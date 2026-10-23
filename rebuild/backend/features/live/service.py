"""Short synchronous stream batches; called in a thread, never on the event loop."""
from dataclasses import dataclass
from threading import Lock

from pydantic import TypeAdapter

from backend.database.models import ReadingHistoryState
from backend.features.readings.schemas import ReadingResponse
from backend.features.readings.service import ReadingsService
from .cursor import StreamCursor
from . import repository

READING = TypeAdapter(ReadingResponse)


@dataclass(frozen=True)
class StreamPolicy:
    poll_seconds: float = 1
    heartbeat_seconds: float = 15
    batch_size: int = 100
    backlog_limit: int = 1000
    per_session: int = 4
    per_process: int = 32
    send_timeout: float = 5


class Connections:
    def __init__(self):
        self.lock = Lock()
        self.sessions = {}
        self.total = 0

    def acquire(self, session_hash, policy):
        with self.lock:
            count = self.sessions.get(session_hash, 0)
            if count >= policy.per_session or self.total >= policy.per_process:
                return False
            self.sessions[session_hash] = count + 1
            self.total += 1
            return True

    def release(self, session_hash):
        with self.lock:
            count = self.sessions[session_hash] - 1
            if count:
                self.sessions[session_hash] = count
            else:
                del self.sessions[session_hash]
            self.total -= 1


class LiveService:
    def __init__(self, accounts, policy):
        self.accounts, self.policy = accounts, policy
        self.readings = ReadingsService(accounts.engine, accounts.settings.token_key, accounts.clock)
        self.cursor = StreamCursor(accounts.settings.token_key)

    def batch(self, token, hatchery_id, tank_id, position):
        operator = self.accounts.authenticate(token, touch=False).require_hatchery(hatchery_id)
        with self.readings.registry.operation(hatchery_id, operator.id) as session:
            self.readings.tank(session, hatchery_id, tank_id)
            watermark = session.get(ReadingHistoryState, hatchery_id).last_position
            if position > watermark:
                return None, position
            changes = repository.changes(session, hatchery_id, tank_id, position, watermark,
                self.policy.backlog_limit + 1)
            if len(changes) > self.policy.backlog_limit:
                return None, position
            batch = changes[:self.policy.batch_size]
            devices, revisions, headers = repository.records(session, batch)
            messages = []
            for change in batch:
                if change.device_event_id:
                    reading = self.readings.device_view(devices[change.device_event_id])
                else:
                    revision = revisions[change.manual_revision_id]
                    reading = self.readings.manual_view(headers[revision.reading_id], revision)
                messages.append(dict(v=1, type="reading.changed",
                    cursor=self.cursor.seal(hatchery_id, tank_id, change.position),
                    reading=READING.validate_python(reading).model_dump(mode="json")))
            # Gaps belong to other tanks. Advance only after every matching change
            # through this watermark has been sent; a heartbeat conveys this progress.
            following = batch[-1].position if len(changes) > len(batch) else watermark
            return messages, following

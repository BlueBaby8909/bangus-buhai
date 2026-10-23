"""Offline stream cursor isolation, limits and transport deadlines."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from backend.features.live.cursor import StreamCursor
from backend.features.live.router import send
from backend.features.live.service import Connections, StreamPolicy
from backend.features.readings.cursor import Cursor
from backend.features.readings.errors import ReadingsError


class CursorTests(unittest.TestCase):
    def test_stable_scoped_signed_token_and_separate_domains(self):
        hatchery, tank = uuid4(), uuid4()
        cursor = StreamCursor(b'synthetic-key')
        token = cursor.seal(hatchery, tank, 23)
        self.assertEqual(token, cursor.seal(hatchery, tank, 23))
        self.assertEqual(cursor.open(token, hatchery, tank), 23)
        for key, h, t in [(b'other-key', hatchery, tank), (b'synthetic-key', uuid4(), tank),
                          (b'synthetic-key', hatchery, uuid4())]:
            with self.assertRaises(ValueError): StreamCursor(key).open(token, h, t)
        with self.assertRaises(ReadingsError): Cursor(b'synthetic-key').open(token, {})
        with self.assertRaises(ValueError):
            cursor.open(Cursor(b'synthetic-key').seal({}, 23, []), hatchery, tank)

    def test_malformed_and_invalid_positions(self):
        cursor, hatchery, tank = StreamCursor(b'synthetic-key'), uuid4(), uuid4()
        for token in [None, '', '!', 'x'*2049, '\ud800', cursor.seal(hatchery, tank, -1),
                      cursor.seal(hatchery, tank, True), cursor.seal(hatchery, tank, 2**63)]:
            with self.subTest(token=repr(token)[:20]), self.assertRaises(ValueError):
                cursor.open(token, hatchery, tank)

    def test_concurrent_default_limits_and_release(self):
        connections, policy = Connections(), StreamPolicy()
        with ThreadPoolExecutor(16) as pool:
            acquired = list(pool.map(lambda _:connections.acquire('same-session', policy), range(32)))
        self.assertEqual(sum(acquired), 4)
        for _ in range(4): connections.release('same-session')
        with ThreadPoolExecutor(16) as pool:
            acquired = list(pool.map(lambda i:connections.acquire(str(i), policy), range(64)))
        self.assertEqual(sum(acquired), 32)
        for i, allowed in enumerate(acquired):
            if allowed: connections.release(str(i))
        self.assertEqual((connections.total, connections.sessions), (0, {}))

    def test_approved_defaults(self):
        policy = StreamPolicy()
        self.assertEqual((policy.poll_seconds, policy.batch_size, policy.heartbeat_seconds,
            policy.backlog_limit, policy.per_session, policy.per_process, policy.send_timeout),
            (1, 100, 15, 1000, 4, 32, 5))


class SendTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_cancels_blocked_send(self):
        cancelled = asyncio.Event()
        async def blocked(_):
            try: await asyncio.Event().wait()
            finally: cancelled.set()
        websocket = AsyncMock()
        websocket.send_json.side_effect = blocked
        with self.assertRaises(TimeoutError): await send(websocket, {'v':1}, .01)
        self.assertTrue(cancelled.is_set())

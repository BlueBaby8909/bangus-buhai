"""T15: real PostgreSQL journal, cookie authorization and ASGI/TCP WebSockets."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
import json
import socket
import threading
from unittest.mock import patch
from urllib.parse import urlencode
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select
from starlette.websockets import WebSocketDisconnect
import uvicorn
from wsproto import WSConnection, ConnectionType
from wsproto.events import Request, AcceptConnection, RejectConnection, TextMessage, CloseConnection, Ping

from backend.core.application import create_app
from backend.core.security import token_hash
from backend.database.models import (AuthSession, Hatchery, ManualReading, ManualReadingRevision,
    Membership, ReadingChange, Tank, UserIdentity)
from backend.features.accounts.service import AccountService
from backend.features.live.cursor import StreamCursor
from backend.features.live.service import Connections, LiveService, StreamPolicy
from backend.features.readings.schemas import CreateMeasurement
from backend.features.readings.service import ReadingsService
from backend.tests.auth_support import FakeAuth
from backend.tests.mqtt_support import DatabaseFixture, eventually


class Wire:
    """Minimal actual TCP client using the same pinned RFC6455 library, no browser/login."""
    def __init__(self, port, target, cookie, origin):
        self.socket = socket.create_connection(('127.0.0.1', port), timeout=5)
        self.socket.settimeout(5)
        self.protocol = WSConnection(ConnectionType.CLIENT)
        self.pending, self.text = [], ''
        self.socket.sendall(self.protocol.send(Request(host=f'127.0.0.1:{port}', target=target,
            extra_headers=[(b'cookie', cookie.encode()), (b'origin', origin.encode())])))
        self.handshake = self.event()

    def event(self):
        while not self.pending:
            data = self.socket.recv(65536)
            if not data:
                return CloseConnection(code=1006)
            self.protocol.receive_data(data)
            self.pending.extend(self.protocol.events())
        return self.pending.pop(0)

    def receive(self):
        while True:
            event = self.event()
            if isinstance(event, TextMessage):
                self.text += event.data
                if event.message_finished:
                    result, self.text = json.loads(self.text), ''
                    return result
            elif isinstance(event, Ping):
                self.socket.sendall(self.protocol.send(event.response()))
            elif isinstance(event, CloseConnection):
                return event

    def close(self):
        self.socket.close()


class LiveTests(DatabaseFixture):
    def setUp(self):
        super().setUp()
        self.fake = FakeAuth()
        self.addCleanup(self.fake.client.close)
        with Session(self.engine) as session, session.begin():
            user = session.get(UserIdentity, self.user)
            user.provider_issuer, user.provider_subject = self.fake.settings.issuer, self.fake.subject
        self.accounts = AccountService(self.fake.settings, self.engine, self.fake.provider, lambda: self.clock)
        self.app = create_app(service=self.accounts)
        self.app.state.live_policy = replace(StreamPolicy(), poll_seconds=.025, heartbeat_seconds=.1)
        self.live = LiveService(self.accounts, self.app.state.live_policy)
        self.readings = ReadingsService(self.engine, self.fake.settings.token_key, lambda: self.clock)
        self.client = self.enterContext(TestClient(self.app, base_url='http://127.0.0.1',
            headers={'Origin': self.fake.settings.origins[0]}))
        login = self.client.post('/api/v1/auth/login', json=dict(email='operator@example.test', password='correct-test-password'))
        self.assertEqual(login.status_code, 200, login.text)
        self.client.headers['X-CSRF-Token'] = login.json()['csrf_token']
        self.token = self.client.cookies.get(self.fake.settings.cookie_name)
        self.base = f'/api/v1/hatcheries/{self.hatchery}/tanks/{self.tank}'

    def history(self, **params):
        response = self.client.get(self.base + '/readings', params=params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def target(self, cursor=None):
        return self.base + '/stream?' + urlencode({'cursor': cursor or self.history()['stream_cursor']})

    def create(self, **changes):
        body = dict(request_id=str(uuid4()), measured_at=self.clock.isoformat(), ph=7.2) | changes
        response = self.client.post(self.base + '/manual-readings', json=body)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def change(self, row, action='correct'):
        body = dict(expected_version=row['version'], reason='Synthetic correction')
        path = self.base + '/manual-readings/' + row['id']
        if action == 'correct':
            body.update(measured_at=row['measured_at'], ph=7.8)
            response = self.client.patch(path, json=body)
        else:
            response = self.client.post(path + '/' + action, json=body)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def changed(self, socket):
        for _ in range(50):
            message = socket.receive_json()
            if message['type'] == 'reading.changed':
                return message
        self.fail('No reading change received')

    def session_row(self, session):
        return session.exec(select(AuthSession).where(AuthSession.token_hash == token_hash(self.token))).one()

    def websocket(self, target, **kwargs):
        return self.client.websocket_connect("ws://127.0.0.1" + target, **kwargs)

    def connect(self, **kwargs):
        return self.websocket(self.target(), **kwargs)

    def test_snapshot_gap_manual_lifecycle_and_canonical_payloads(self):
        snapshot = self.history()
        first = self.create(notes='Preserved provenance')
        second = self.change(first)
        third = self.change(second, 'void')
        fourth = self.change(third, 'restore')
        with self.websocket(self.target(snapshot['stream_cursor'])) as ws:
            self.assertEqual(ws.receive_json()['type'], 'ready')
            messages = [self.changed(ws) for _ in range(4)]
            self.assertEqual([m['reading'] for m in messages], [first, second, third, fourth])
            positions = [self.live.cursor.open(m['cursor'], self.hatchery, self.tank) for m in messages]
            self.assertEqual(positions, [1, 2, 3, 4])

    def test_duplicate_ingestion_and_reconnect_are_at_least_once(self):
        cursor = self.history()['stream_cursor']
        self.process(); self.process()
        with self.websocket(self.target(cursor)) as ws:
            ws.receive_json(); first = self.changed(ws)
        with self.websocket(self.target(cursor)) as ws:
            ws.receive_json(); replay = self.changed(ws)
        self.assertEqual(first, replay)
        with self.websocket(self.target(first['cursor'])) as ws:
            ws.receive_json()
            self.assertEqual(ws.receive_json()['type'], 'heartbeat')

    def test_unknown_capture_time_and_default_ph_preserved(self):
        cursor = self.history()['stream_cursor']
        self.process(self.event(measured_at=None, time_quality='unsynchronized'))
        with self.websocket(self.target(cursor)) as ws:
            ws.receive_json(); reading = self.changed(ws)['reading']
        canonical = self.history(time_basis='received')['items'][0]
        self.assertEqual(reading, canonical)
        self.assertIsNone(reading['measured_at'])

    def test_capture_times_do_not_reorder_commit_delivery(self):
        cursor = self.history()['stream_cursor']
        first = self.event()
        second = self.event(seq=first['seq'] + 1,
            measured_at=(self.clock - timedelta(minutes=20)).isoformat().replace('+00:00', 'Z'))
        self.assertEqual(self.process(first).disposition, 'stored')
        self.assertEqual(self.process(second).disposition, 'stored')
        with self.websocket(self.target(cursor)) as ws:
            ws.receive_json()
            events = [self.changed(ws)['reading']['telemetry'] for _ in range(2)]
        self.assertEqual([e['seq'] for e in events], [first['seq'], second['seq']])

    def uncommitted(self, session):
        header = ManualReading(hatchery_id=self.hatchery, tank_id=self.tank, created_by=self.user,
            request_id=uuid4(), received_at=self.clock)
        session.add(header); session.flush()
        revision = ManualReadingRevision(reading_id=header.id, hatchery_id=self.hatchery,
            tank_id=self.tank, version=1, actor_id=self.user, changed_at=self.clock,
            measured_at=self.clock, ph=7.2)
        session.add(revision); session.flush()

    def test_commit_visible_rollback_invisible_over_socket(self):
        with self.connect() as ws:
            ws.receive_json()
            with Session(self.engine) as session:
                self.uncommitted(session)
                self.assertEqual(ws.receive_json()['type'], 'heartbeat')
                session.rollback()
            self.assertEqual(ws.receive_json()['type'], 'heartbeat')
            with Session(self.engine) as session:
                self.uncommitted(session)
                session.commit()
            self.assertEqual(self.changed(ws)['reading']['version'], 1)

    def test_concurrent_commits_ordered_and_tank_gaps_not_missing(self):
        cursor = self.history()['stream_cursor']
        other = uuid4()
        with Session(self.engine) as session, session.begin():
            session.add(Tank(id=other, hatchery_id=self.hatchery, name='Other tank'))
        def write(tank):
            self.readings.create(self.hatchery, tank, self.user,
                CreateMeasurement(request_id=uuid4(), measured_at=self.clock, ph=7.2))
        with ThreadPoolExecutor(4) as pool:
            list(pool.map(write, [self.tank, other, self.tank, other, self.tank]))
        with Session(self.engine) as session:
            expected = [c.position for c in session.exec(select(ReadingChange).where(
                ReadingChange.tank_id == self.tank).order_by(ReadingChange.position)).all()]
        with self.websocket(self.target(cursor)) as ws:
            ws.receive_json(); messages = [self.changed(ws) for _ in expected]
            self.assertEqual([self.live.cursor.open(m['cursor'], self.hatchery, self.tank) for m in messages], expected)
            heartbeat = ws.receive_json()
            self.assertEqual(self.live.cursor.open(heartbeat['cursor'], self.hatchery, self.tank), 5)

    def test_pagination_cursor_keeps_original_snapshot(self):
        self.create(); self.create()
        first = self.history(limit=1)
        self.create()
        second = self.history(limit=1, cursor=first['next_cursor'])
        self.assertEqual(first['stream_cursor'], second['stream_cursor'])
        with self.websocket(self.target(second['stream_cursor'])) as ws:
            ws.receive_json(); self.assertEqual(self.live.cursor.open(self.changed(ws)['cursor'], self.hatchery, self.tank), 3)

    def test_unauthenticated_missing_origin_and_bad_origins(self):
        target = self.target()
        with TestClient(self.app, base_url='http://127.0.0.1') as client:
            for headers in ({}, {'Origin':self.fake.settings.origins[0]},
                            {'Origin':'https://evil.invalid', 'Cookie':f'bb_session_dev={self.token}'}):
                with self.subTest(headers=list(headers)), self.assertRaises(WebSocketDisconnect):
                    with client.websocket_connect("ws://127.0.0.1" + target, headers=headers): pass
        with self.assertRaises(WebSocketDisconnect):
            with self.websocket(target, headers={'Origin':'null'}): pass

    def test_cursor_tampering_scope_missing_and_ahead(self):
        token = self.history()['stream_cursor']
        invalid = [token[:20] + ('A' if token[20] != 'A' else 'B') + token[21:],
            self.live.cursor.seal(self.hatchery, uuid4(), 0), 'x' * 2049]
        for cursor in invalid:
            with self.subTest(cursor=cursor[:10]), self.assertRaises(WebSocketDisconnect):
                with self.websocket(self.target(cursor)): pass
        with self.assertRaises(WebSocketDisconnect):
            with self.websocket(self.base + '/stream'): pass
        with self.websocket(self.target(self.live.cursor.seal(self.hatchery, self.tank, 1))) as ws:
            ws.receive_json(); self.assertEqual(ws.receive_json()['type'], 'resync_required')

    def test_tenant_and_tank_ownership_checked_even_with_valid_signature(self):
        other_hatchery, other_tank = uuid4(), uuid4()
        with Session(self.engine) as session, session.begin():
            session.add(Hatchery(id=other_hatchery, name='Private')); session.flush()
            session.add(Tank(id=other_tank, hatchery_id=other_hatchery, name='Private'))
        for hatchery, tank in [(other_hatchery, other_tank), (self.hatchery, other_tank)]:
            cursor = self.live.cursor.seal(hatchery, tank, 0)
            url = f'/api/v1/hatcheries/{hatchery}/tanks/{tank}/stream?' + urlencode({'cursor':cursor})
            with self.assertRaises(WebSocketDisconnect):
                with self.websocket(url): pass

    def test_revocation_disable_membership_and_expiry_close_idle_streams(self):
        for cause in ('logout', 'disable', 'membership', 'absolute', 'idle'):
            with self.subTest(cause=cause):
                # Restore synthetic identity; create a fresh independent session each time.
                with Session(self.engine) as session, session.begin():
                    session.get(UserIdentity, self.user).active = True
                    session.get(Membership, (self.hatchery, self.user)).active = True
                self.token, _ = self.accounts.login('operator@example.test', 'correct-test-password', '127.0.0.1')
                self.client.cookies.set(self.fake.settings.cookie_name, self.token)
                with self.connect() as ws:
                    ws.receive_json()
                    if cause == 'logout':
                        self.accounts.logout(self.token)
                    else:
                        with Session(self.engine) as session, session.begin():
                            if cause == 'disable': session.get(UserIdentity, self.user).active = False
                            elif cause == 'membership': session.get(Membership, (self.hatchery, self.user)).active = False
                            else:
                                row = self.session_row(session)
                                if cause == 'absolute':
                                    row.created_at = self.clock - timedelta(hours=8)
                                    row.expires_at = self.clock
                                else: row.last_seen_at = self.clock - timedelta(minutes=30)
                    with self.assertRaises(WebSocketDisconnect) as failure:
                        while True: ws.receive_json()
                    self.assertEqual(failure.exception.code, 1008)

    def test_heartbeats_and_passive_provider_refresh_do_not_touch_inactivity(self):
        with self.connect() as ws:
            ws.receive_json()
            with Session(self.engine) as session, session.begin():
                row = self.session_row(session)
                before = row.last_seen_at
                row.encrypted_tokens = self.accounts.cipher.encrypt(json.dumps(dict(
                    access=self.fake.token(exp=int(self.clock.timestamp()) - 10),
                    refresh='synthetic-refresh')).encode()).decode()
            self.clock += timedelta(minutes=1)
            for _ in range(2): self.assertEqual(ws.receive_json()['type'], 'heartbeat')
            with Session(self.engine) as session:
                self.assertEqual(self.session_row(session).last_seen_at, before)
            self.assertEqual(self.fake.refresh_calls, 1)
            self.clock += timedelta(minutes=29)
            with self.assertRaises(WebSocketDisconnect):
                while True: ws.receive_json()

    def test_production_requires_wss_and_dev_requires_loopback(self):
        target = self.target()
        production = replace(self.fake.settings, development=False, origins=('https://operator.example',))
        accounts = AccountService(production, self.engine, self.fake.provider, lambda:self.clock)
        app = create_app(service=accounts)
        token, _ = accounts.login('operator@example.test', 'correct-test-password', '127.0.0.1')
        headers = {'Origin':production.origins[0], 'Cookie':f'{production.cookie_name}={token}'}
        with TestClient(app, base_url='https://api.example') as client:
            with self.assertRaises(WebSocketDisconnect):
                with client.websocket_connect('ws://api.example'+target,
                    headers=headers | {'X-Forwarded-Proto':'https'}): pass
            with client.websocket_connect('wss://api.example'+target, headers=headers) as ws:
                self.assertEqual(ws.receive_json()['type'], 'ready')
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect('ws://evil.invalid'+target): pass

    def test_push_only_input_closes_and_releases_slot(self):
        with self.connect() as ws:
            ws.receive_json(); ws.send_text('unneeded client input')
            with self.assertRaises(WebSocketDisconnect): ws.receive_json()
        self.assertEqual(self.app.state.live_connections.total, 0)

    def test_database_failure_closes_without_disclosing_details(self):
        with self.connect() as ws:
            ws.receive_json()
            with patch.object(LiveService, 'batch', side_effect=SQLAlchemyError('synthetic-private-details')):
                with self.assertRaises(WebSocketDisconnect) as failure:
                    while True: ws.receive_json()
            self.assertEqual(failure.exception.code, 1013)
            self.assertEqual(failure.exception.reason, 'stream_unavailable')
        self.assertEqual(self.app.state.live_connections.total, 0)

    def serve(self, app=None, port=0):
        listener = socket.socket()
        listener.bind(('127.0.0.1', port)); listener.listen(64)
        server = uvicorn.Server(uvicorn.Config(app or self.app, ws='wsproto', host='127.0.0.1',
            port=listener.getsockname()[1], proxy_headers=False, log_level='error', lifespan='off'))
        thread = threading.Thread(target=server.run, kwargs={'sockets':[listener]}, daemon=True)
        thread.start()
        eventually(lambda:server.started)
        def stop():
            server.should_exit = True; thread.join(10); listener.close()
            self.assertFalse(thread.is_alive())
        self.addCleanup(stop)
        return listener.getsockname()[1], stop

    def wire(self, port, cursor=None, token=None):
        connection = Wire(port, self.target(cursor), f'{self.fake.settings.cookie_name}={token or self.token}', self.fake.settings.origins[0])
        self.addCleanup(connection.close)
        return connection

    def test_real_tcp_reconnect_and_fresh_api_restart(self):
        cursor = self.history()['stream_cursor']
        port, stop = self.serve()
        ws = self.wire(port, cursor); self.assertIsInstance(ws.handshake, AcceptConnection)
        self.assertEqual(ws.receive()['type'], 'ready')
        first = self.create()
        while (message := ws.receive())['type'] != 'reading.changed': pass
        self.assertEqual(message['reading'], first)
        resume = message['cursor']; ws.close(); stop()
        second = self.create()
        fresh = create_app(service=self.accounts)
        fresh.state.live_policy = self.app.state.live_policy
        port, _ = self.serve(fresh, port)
        ws = self.wire(port, resume); self.assertIsInstance(ws.handshake, AcceptConnection)
        self.assertEqual(ws.receive()['type'], 'ready')
        while (message := ws.receive())['type'] != 'reading.changed': pass
        self.assertEqual(message['reading'], second)

    def test_real_tcp_default_per_session_limit_and_recovery(self):
        port, _ = self.serve()
        sockets = [self.wire(port) for _ in range(4)]
        for ws in sockets:
            self.assertIsInstance(ws.handshake, AcceptConnection)
            self.assertEqual(ws.receive()['type'], 'ready')
        denied = self.wire(port)
        self.assertIsInstance(denied.handshake, RejectConnection)
        sockets[0].close()
        eventually(lambda:self.app.state.live_connections.total == 3)
        self.assertIsInstance(self.wire(port).handshake, AcceptConnection)

    def test_real_tcp_process_limit_across_sessions(self):
        port, _ = self.serve()
        for _ in range(8):
            token, _ = self.accounts.login('operator@example.test', 'correct-test-password', f'synthetic-{uuid4()}')
            for _ in range(4):
                ws = self.wire(port, token=token)
                self.assertIsInstance(ws.handshake, AcceptConnection)
                ws.receive()
        token, _ = self.accounts.login('operator@example.test', 'correct-test-password', 'new-synthetic-ip')
        self.assertIsInstance(self.wire(port, token=token).handshake, RejectConnection)
        self.assertEqual(self.app.state.live_connections.total, 32)

    def test_real_tcp_resync_threshold_and_batch_limit(self):
        cursor = self.history()['stream_cursor']
        first = self.create()
        with Session(self.engine) as session, session.begin():
            session.add_all([ManualReadingRevision(reading_id=UUID(first['id']), hatchery_id=self.hatchery,
                tank_id=self.tank, version=version, actor_id=self.user, changed_at=self.clock,
                measured_at=self.clock, ph=7.2, reason='Synthetic backlog') for version in range(2, 1002)])
        messages, following = self.live.batch(self.token, self.hatchery, self.tank, 1)
        self.assertEqual(len(messages), 100)
        self.assertEqual(following, 101)
        port, _ = self.serve()
        ws = self.wire(port, cursor); ws.receive()
        self.assertEqual(ws.receive()['type'], 'resync_required')
        self.assertIsInstance(ws.receive(), CloseConnection)
        # Exactly 1000 pending changes is allowed, and all 10 batches replay in order.
        positions = []
        ws = self.wire(port, self.live.cursor.seal(self.hatchery, self.tank, 1)); ws.receive()
        while len(positions) < 1000:
            message = ws.receive()
            if message['type'] == 'reading.changed':
                positions.append(self.live.cursor.open(message['cursor'], self.hatchery, self.tank))
        self.assertEqual(positions, list(range(2, 1002)))

    def test_real_tcp_send_timeout_releases_slow_connection(self):
        # TCP cannot reliably saturate an OS buffer with a 100-event batch. Inject
        # transport backpressure at ASGI send, while exercising the actual TCP socket.
        from starlette.websockets import WebSocket
        original = WebSocket.send_json
        async def blocked(websocket, message, *args, **kwargs):
            if message.get('type') == 'reading.changed': await asyncio.sleep(2)
            return await original(websocket, message, *args, **kwargs)
        self.app.state.live_policy = replace(self.app.state.live_policy, send_timeout=.05)
        cursor = self.history()['stream_cursor']; self.create()
        with patch.object(WebSocket, 'send_json', blocked):
            port, _ = self.serve()
            ws = self.wire(port, cursor); self.assertEqual(ws.receive()['type'], 'ready')
            close = ws.receive()
            self.assertIsInstance(close, CloseConnection)
            self.assertEqual(close.code, 1013)
            eventually(lambda:self.app.state.live_connections.total == 0)


if __name__ == '__main__':
    import unittest
    unittest.main()

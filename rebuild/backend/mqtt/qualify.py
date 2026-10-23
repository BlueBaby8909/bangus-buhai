"""Explicit broker permission probe, with private logins and non-reading markers only.

Run before starting ingestion. No database access or broker configuration changes.
Markers are intentionally invalid wire documents, non-retained, and never claim to
be accepted readings/ACKs. MQTT passwords and payloads are never printed.
"""
import argparse
from dataclasses import replace
from pathlib import Path
import threading
import time
from uuid import uuid4

import paho.mqtt.client as mqtt

from .config import MqttSettings


def wait(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.02)
    raise RuntimeError('Broker probe response timeout')


class Probe:
    def __init__(self, settings, *, client_id):
        self.connected = threading.Event()
        self.subacks, self.pubacks, self.messages = {}, {}, []
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id,
                                  protocol=mqtt.MQTTv5, reconnect_on_failure=False)
        self.client.connect_timeout = 5
        self.client.tls_set_context(settings.tls())
        self.client.username_pw_set(*settings.credentials())
        self.client.on_connect = self.on_connect
        self.client.on_subscribe = lambda c, u, mid, reasons, p: self.subacks.update({mid: [r.value for r in reasons]})
        self.client.on_publish = lambda c, u, mid, reason, p: self.pubacks.update({mid: reason.value})
        self.client.on_message = lambda c, u, msg: self.messages.append((msg.topic, bytes(msg.payload)))
        try:
            self.client.connect(settings.host, settings.port, keepalive=20)
            self.client.loop_start()
            wait(self.connected.is_set)
        except BaseException:
            self.close()
            raise

    def on_connect(self, client, userdata, flags, reason, properties):
        if not reason.is_failure:
            self.connected.set()

    def subscribe(self, topic):
        code, mid = self.client.subscribe(topic, qos=1)
        if code != 0:
            raise RuntimeError('Probe subscribe unavailable')
        wait(lambda: mid in self.subacks)
        return self.subacks[mid]

    def publish(self, topic, marker):
        info = self.client.publish(topic, marker, qos=1, retain=False)
        if info.rc != 0:
            raise RuntimeError('Probe publish unavailable')
        wait(lambda: info.mid in self.pubacks)
        return self.pubacks[info.mid]

    def close(self):
        self.client.disconnect()
        self.client.loop_stop()


def qualify(settings, device_login, *, commands=False):
    if settings.auth_mode != 'password':
        raise ValueError('Probe requires the selected password authentication mode')
    device_settings = replace(settings, credential_file=str(device_login))
    device_id = device_settings.credentials()[0]
    import re
    if not re.fullmatch(r'BB-[0-9A-F]{12}', device_id):
        raise ValueError('Probe requires a canonical device username')
    own = f'{settings.prefix}/devices/{device_id}'
    foreign_id = 'BB-000000000000' if device_id != 'BB-000000000000' else 'BB-000000000001'
    foreign = f'{settings.prefix}/devices/{foreign_id}'
    backend = device = None
    def check(condition, name):
        if not condition:
            raise RuntimeError('Broker permission check failed: ' + name)
        print('PASS:', name, flush=True)
    marker = ('BB-T13A-PERMISSION-PROBE-' + uuid4().hex).encode()
    try:
        backend = Probe(settings, client_id='bb-probe-backend-' + uuid4().hex[:12])
        device = Probe(device_settings, client_id='bb-probe-spoof-' + uuid4().hex[:12])
        check(True, 'separate logins over verified TLS')
        for suffix in ('telemetry', 'command-results'):
            check(backend.subscribe(f'{settings.prefix}/devices/+/{suffix}') == [1], 'backend subscribe ' + suffix)
        for suffix in ('acks', 'quarantine-receipts'):
            check(device.subscribe(own + '/' + suffix) == [1], 'device subscribe own ' + suffix)
            # Some brokers grant the filter but apply ACLs to each delivered message.
            foreign_result = device.subscribe(foreign + '/' + suffix)
            check(foreign_result == [1] or all(r >= 128 for r in foreign_result), 'foreign subscription response ' + suffix)
            check(backend.publish(foreign + '/' + suffix, b'foreign-' + marker) < 128, 'backend publish foreign ' + suffix)
            check(backend.publish(own + '/' + suffix, marker) < 128, 'backend publish own ' + suffix)
            wait(lambda: (own + '/' + suffix, marker) in device.messages)
        if commands:
            check(device.subscribe(own + '/cmd') == [1], 'device subscribe own commands')
            device.subscribe(foreign + '/cmd')
            check(backend.publish(own + '/cmd', marker) < 128, 'backend publish own commands')
            check(backend.publish(foreign + '/cmd', marker) < 128, 'backend publish foreign commands')
            wait(lambda: (own + '/cmd', marker) in device.messages)
        check(not any(t.startswith(foreign + '/') for t, _ in device.messages), 'device cannot receive foreign responses')
        check(device.publish(own + '/telemetry', marker) < 128, 'device publish own telemetry')
        wait(lambda: (own + '/telemetry', marker) in backend.messages)
        backend_read = backend.subscribe(own + '/acks')
        check(backend_read == [1] or all(r >= 128 for r in backend_read), 'backend ACK subscription response')
        backend.publish(own + '/acks', b'backend-readback-' + marker)
        device.publish(own + '/telemetry', b'ordered-' + marker)
        wait(lambda: (own + '/telemetry', b'ordered-' + marker) in backend.messages)
        check(not any(t.endswith('/acks') for t, _ in backend.messages), 'backend cannot receive ACK traffic')
        # A broker may disconnect a client after rejecting an unauthorized publish.
        # Isolate each negative test so it cannot invalidate later positive markers.
        forbidden = [(device_settings, own + '/acks', 'device cannot publish acks'),
                     (device_settings, own + '/quarantine-receipts', 'device cannot publish receipts'),
                     (device_settings, foreign + '/telemetry', 'device cannot publish foreign telemetry'),
                     (device_settings, own + '/cmd', 'device cannot publish commands'),
                     (settings, own + '/telemetry', 'backend cannot publish telemetry')]
        if not commands:
            forbidden.append((settings, own + '/cmd', 'backend cannot publish commands'))
        for login, topic, name in forbidden:
            denied = Probe(login, client_id='bb-probe-negative-' + uuid4().hex[:12])
            try:
                check(denied.publish(topic, marker) == 135, name)
            finally:
                denied.close()
        print('Broker permission qualification PASS; no database/worker configuration changed', flush=True)
    finally:
        if device: device.close()
        if backend: backend.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device-login', type=Path,
                        default=Path.home() / 'BangusBuhai-Secrets/t13a/mqtt-login/device-login.json')
    parser.add_argument('--commands', action='store_true', help='Qualify T14 command publication and device isolation')
    args = parser.parse_args()
    try:
        qualify(MqttSettings.load(), args.device_login, commands=args.commands)
    except Exception:
        raise SystemExit('Broker qualification unavailable or failed; live worker must remain disabled. No secrets printed.') from None


if __name__ == '__main__':
    main()

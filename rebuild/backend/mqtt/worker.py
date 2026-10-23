"""Bounded MQTT network callbacks plus a separate database processing thread."""
from collections import Counter
from dataclasses import dataclass
import logging
import json
from queue import Empty, Full, Queue
import threading
import time

import paho.mqtt.client as mqtt

from .lease import WorkerLease
from backend.features.commands.service import CommandService

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class Delivery:
    generation: int
    mid: int
    topic: str
    payload: bytes
    qos: int
    retained: bool


@dataclass(frozen=True)
class Completion:
    delivery: Delivery
    outcome: object


class IngestionWorker:
    def __init__(self, engine, settings, service, *, queue_size=64, client=None):
        settings.validate(engine.url.database)
        if settings.mode == 'disabled' or not 1 <= queue_size <= 1024:
            raise ValueError('MQTT worker is disabled or invalid')
        self.settings, self.service = settings, service
        self.commands = CommandService(engine, clock=service.clock)
        self.command_mids = {}
        self.command_pubacks = Queue(maxsize=64)
        self.lease = WorkerLease(engine, settings)
        self.inbox = Queue(maxsize=queue_size)
        self.completions = Queue(maxsize=queue_size)
        self.lock = threading.RLock()
        self.stop_event, self.recover_event, self.ready = threading.Event(), threading.Event(), threading.Event()
        self.generation, self.connected = 0, False
        self.counters = Counter()
        self.client = client or mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
            client_id=settings.client_id, clean_session=False, protocol=mqtt.MQTTv311, manual_ack=True)
        self.client.tls_set_context(settings.tls())
        if settings.auth_mode == 'password':
            self.client.username_pw_set(*settings.credentials())
        self.client.connect_timeout = 5
        self.client.max_queued_messages_set(64)
        self.client.max_inflight_messages_set(20)
        self.client.on_connect, self.client.on_disconnect = self.on_connect, self.on_disconnect
        self.client.on_subscribe, self.client.on_message = self.on_subscribe, self.on_message
        self.client.on_publish = self.on_publish
        self.network_thread = self.processor_thread = None

    def count(self, reason):
        with self.lock:
            self.counters[reason] += 1

    def fence(self):
        with self.lock:
            self.generation += 1
            self.connected = False
            self.ready.clear()
            self.command_mids.clear()

    def on_publish(self, client, userdata, mid, reason, properties):
        attempt = self.command_mids.pop(mid, None)
        if attempt and not reason.is_failure:
            try:
                self.command_pubacks.put_nowait(attempt)
            except Full:
                self.count('command_puback_evidence_lost')

    def dispatch_commands(self):
        if not self.ready.is_set() or not (self.settings.mode == 'test' or self.settings.commands_qualified):
            return
        try:
            self.lease.heartbeat()
        except Exception:
            self.count('lease_lost'); self.stop_event.set(); self.fence(); return
        def publish(wire):
            if not self.ready.is_set() or self.stop_event.is_set() or self.recover_event.is_set():
                return None
            try:
                self.lease.heartbeat()
            except Exception:
                self.count('lease_lost'); self.stop_event.set(); self.fence()
                raise RuntimeError('Command publication fenced') from None
            info = self.client.publish(f"{self.settings.prefix}/devices/{wire['device_id']}/cmd",
                json.dumps(wire, separators=(',', ':')).encode(), qos=1, retain=False)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                self.count('command_publish_failed')
                return None
            return info.mid
        for mid, attempt in self.commands.dispatch(publish):
            self.command_mids[mid] = attempt

    def report(self):
        with self.lock:
            snapshot = dict(self.counters)
        LOG.info('ingestion_counts %s', json.dumps(snapshot, sort_keys=True))

    def on_connect(self, client, userdata, flags, reason, properties):
        if reason.is_failure:
            self.count('connection_denied'); self.recover_event.set(); return
        with self.lock:
            self.generation += 1
            self.connected = True
        result, _ = client.subscribe([(f'{self.settings.prefix}/devices/+/telemetry', 1),
                                     (f'{self.settings.prefix}/devices/+/command-results', 1)])
        if result != mqtt.MQTT_ERR_SUCCESS:
            self.recover_event.set()

    def on_subscribe(self, client, userdata, mid, reasons, properties):
        if len(reasons) != 2 or any(reason.is_failure or reason.value != 1 for reason in reasons):
            self.count('subscription_denied'); self.recover_event.set()
        else:
            self.ready.set()
            LOG.info('ingestion_ready command_dispatch=%s',
                'enabled' if self.settings.mode == 'test' or self.settings.commands_qualified else 'disabled')

    def on_disconnect(self, client, userdata, flags, reason, properties):
        self.fence()

    def on_message(self, client, userdata, message):
        with self.lock:
            generation, connected = self.generation, self.connected
        if not connected:
            return
        if len(message.payload) > 4096 or len(message.topic) > 256:
            self.count('oversize_delivery')
            if message.qos == 1:
                client.ack(message.mid, message.qos)
            return
        try:
            self.inbox.put_nowait(Delivery(generation, message.mid, message.topic,
                bytes(message.payload), message.qos, bool(message.retain)))
        except Full:
            self.count('queue_full'); self.recover_event.set()

    def handle(self, delivery):
        with self.lock:
            if delivery.generation != self.generation or not self.connected or self.stop_event.is_set():
                return
        outcome = self.service.process(delivery.topic, delivery.payload, qos=delivery.qos, retained=delivery.retained)
        # service.process has left its transaction: a failed commit never reaches here.
        try:
            self.completions.put_nowait(Completion(delivery, outcome))
        except Full:
            self.count('completion_queue_full'); self.recover_event.set()

    def flush_completions(self):
        # Only the network owner calls Paho. Publishing from the database thread
        # while callbacks acquire our locks can invert Paho's internal locks.
        while True:
            try:
                completed = self.completions.get_nowait()
            except Empty:
                return
            try:
                self.complete(completed.delivery, completed.outcome)
            finally:
                self.completions.task_done()

    def complete(self, delivery, outcome):
        with self.lock:
            if (delivery.generation != self.generation or not self.connected or
                    self.stop_event.is_set() or self.recover_event.is_set()):
                return
            try:
                self.lease.heartbeat()
            except Exception:
                self.count('lease_lost'); self.stop_event.set(); self.fence(); return
            if outcome.acknowledgement is not None:
                info = self.client.publish(outcome.ack_topic, outcome.acknowledgement, qos=1, retain=False)
                if info.rc != mqtt.MQTT_ERR_SUCCESS:
                    self.count('ack_publish_failed'); self.recover_event.set(); return
            if delivery.qos == 1:
                if self.client.ack(delivery.mid, delivery.qos) != mqtt.MQTT_ERR_SUCCESS:
                    self.recover_event.set()
            self.count(outcome.reason)

    def process_loop(self):
        while not self.stop_event.is_set():
            try:
                attempt = self.command_pubacks.get_nowait()
            except Empty:
                pass
            else:
                try:
                    self.commands.published(attempt)
                except Exception:
                    self.count('command_puback_store_failed')
                finally:
                    self.command_pubacks.task_done()
            try:
                delivery = self.inbox.get(timeout=.2)
            except Empty:
                continue
            try:
                self.handle(delivery)
            except Exception:
                # No SQL, payload or exception repr in logs.
                self.count('processing_unavailable'); self.recover_event.set()
            finally:
                self.inbox.task_done()

    def network_loop(self):
        delay = 1
        reported = time.monotonic()
        try:
            while not self.stop_event.is_set():
                self.recover_event.clear()
                try:
                    self.lease.heartbeat()
                except Exception:
                    self.count('lease_lost'); self.stop_event.set(); break
                try:
                    self.client.connect(self.settings.host, self.settings.port, keepalive=30)
                    heartbeat = time.monotonic()
                    while not self.stop_event.is_set() and not self.recover_event.is_set():
                        self.flush_completions()
                        if self.stop_event.is_set() or self.recover_event.is_set():
                            break
                        if self.client.loop(timeout=.2) != mqtt.MQTT_ERR_SUCCESS:
                            break
                        if self.ready.is_set():
                            delay = 1
                        if time.monotonic() - heartbeat >= 1:
                            # A lease failure must stop, never silently acquire a new lease.
                            try:
                                self.lease.heartbeat()
                            except Exception:
                                self.count('lease_lost'); self.stop_event.set(); break
                            heartbeat = time.monotonic()
                            self.dispatch_commands()
                            if heartbeat - reported >= 60:
                                self.report(); reported = heartbeat
                except Exception:
                    self.count('connection_unavailable')
                finally:
                    self.fence(); self.client.disconnect()
                self.stop_event.wait(delay)
                delay = min(delay * 2, 300)
        finally:
            self.fence()
            self.report()

    def start(self):
        self.lease.acquire()
        try:
            self.processor_thread = threading.Thread(target=self.process_loop, name='bb-mqtt-store', daemon=True)
            self.network_thread = threading.Thread(target=self.network_loop, name='bb-mqtt-network', daemon=True)
            self.processor_thread.start(); self.network_thread.start()
        except BaseException:
            self.stop(); raise

    def stop(self):
        self.stop_event.set(); self.fence()
        for thread in (self.network_thread, self.processor_thread):
            if thread is not None:
                thread.join(timeout=15)
                if thread.is_alive():
                    raise RuntimeError('Ingestion shutdown is still pending')
        self.lease.close()

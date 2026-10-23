"""python -m backend.mqtt; disabled by default, independently of the API."""
import logging
import signal

from backend.database.config import make_engine
from .config import MqttSettings
from .service import IngestionService
from .worker import IngestionWorker


def main(*, service_factory=None):
    engine = worker = None
    try:
        settings = MqttSettings.load()
        if settings.mode == 'disabled':
            print('MQTT ingestion disabled; no connections opened')
            return 0
        engine = make_engine(test=settings.mode == 'test')
        service = (service_factory or IngestionService)(engine, settings.prefix)
        worker = IngestionWorker(engine, settings, service)
        def stop(signum, frame):
            worker.stop_event.set()
        for signum in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signum, stop)
        worker.start()
        while not worker.stop_event.wait(1):
            pass
        return 1 if worker.counters.get('lease_lost') else 0
    except Exception:
        logging.getLogger(__name__).error('ingestion_unavailable')
        return 1
    finally:
        if worker is not None:
            worker.stop()
        if engine is not None:
            engine.dispose()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    raise SystemExit(main())

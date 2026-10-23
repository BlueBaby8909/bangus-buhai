"""Session-level PostgreSQL singleton lease; loss fences the worker."""
import hashlib
import threading
import sqlalchemy as sa


class WorkerBusy(RuntimeError):
    pass


class WorkerLease:
    def __init__(self, engine, settings):
        # Intentionally database/prefix-wide: host aliases and alternate client
        # IDs cannot bypass singleton protection for the same ingestion namespace.
        identity = f'bb-ingestion-v1:{settings.prefix}'
        self.key = int.from_bytes(hashlib.sha256(identity.encode()).digest()[:8], 'big', signed=True)
        self.engine, self.connection = engine, None
        self.lock = threading.RLock()

    def acquire(self):
        self.connection = self.engine.connect().execution_options(isolation_level='AUTOCOMMIT')
        try:
            if not self.connection.scalar(sa.text('SELECT pg_try_advisory_lock(:key)'), {'key': self.key}):
                raise WorkerBusy('An ingestion worker already holds this subscription')
        except BaseException:
            self.connection.close(); self.connection = None
            raise

    def heartbeat(self):
        with self.lock:
            if self.connection is None or self.connection.invalidated:
                raise RuntimeError('Ingestion lease lost')
            self.connection.scalar(sa.text('SELECT 1'))

    def close(self):
        if self.connection is not None:
            try:
                if not self.connection.invalidated:
                    self.connection.execute(sa.text('SELECT pg_advisory_unlock(:key)'), {'key': self.key})
            except Exception:
                self.connection.invalidate()
            finally:
                self.connection.close(); self.connection = None

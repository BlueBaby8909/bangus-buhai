"""Explicit local T13A lost-ACK exercise. Preserves normal live qualification gates."""
from dataclasses import replace
import logging

from .__main__ import main
from .service import IngestionService


class DropFirstStoredAck(IngestionService):
    def __init__(self, engine, prefix):
        url = engine.url
        if url.host not in ('127.0.0.1', 'localhost') or url.port != 55432 or url.database != 'bangus_buhai_rebuild':
            raise ValueError('Lost-ACK exercise requires the isolated local development database')
        super().__init__(engine, prefix)
        self.dropped = False

    def process(self, *args, **kwargs):
        outcome = super().process(*args, **kwargs)
        if outcome.disposition == 'stored' and not self.dropped:
            self.dropped = True
            logging.getLogger(__name__).info('verification_first_stored_ack_withheld_after_commit')
            return replace(outcome, acknowledgement=None, ack_topic=None)
        return outcome


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    raise SystemExit(main(service_factory=DropFirstStoredAck))

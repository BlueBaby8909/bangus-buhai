import json
import unittest

from contracts import ContractError, QuarantineReceipt, ValidationContext, validate_message


class QuarantineWireTests(unittest.TestCase):
    def setUp(self):
        self.context = ValidationContext('BB-AABBCC112233')
        self.topic = 'bangusbuhai-rebuild/devices/BB-AABBCC112233/quarantine-receipts'
        self.document = dict(schema_version=1, device_id=self.context.device_id,
            boot_id='11111111-1111-4111-8111-111111111111', seq=7, event_kind='telemetry',
            quarantine_id='22222222-2222-4222-8222-222222222222', reason='binding_unavailable',
            payload_sha256='a'*64)

    def test_distinct_receipt_cannot_parse_as_success_ack(self):
        self.assertIsInstance(validate_message(self.topic, json.dumps(self.document).encode(), self.context), QuarantineReceipt)
        with self.assertRaises(ContractError):
            validate_message(self.topic.replace('quarantine-receipts', 'acks'), json.dumps(self.document).encode(), self.context)

    def test_strict_identity_types_digest_kind_and_unknown_fields(self):
        for changes in ({'seq': True}, {'seq': 7.0}, {'schema_version': True},
                        {'payload_sha256': 'A'*64}, {'payload_sha256': 'a'*63},
                        {'event_kind': 'command_result'}, {'reason': 'Bad reason'},
                        {'device_id': 'BB-000000000000'}, {'result': 'stored'}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                validate_message(self.topic, json.dumps(self.document | changes).encode(), self.context)

    def test_duplicates_and_oversize_rejected(self):
        for raw in (b'{"schema_version":1,"schema_version":1}', b'{' + b' '*4096 + b'}'):
            with self.assertRaises(ContractError): validate_message(self.topic, raw, self.context)

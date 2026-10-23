import unittest
from pathlib import Path
import json
from pydantic import ValidationError
from contracts import RelayCommand, CommandResult, validate_command_result, ContractError


class T14ContractTests(unittest.TestCase):
    def test_auto_and_set_semantics_and_result(self):
        fixtures = Path(__file__).resolve().parents[1] / 'fixtures/valid'
        wire = json.loads((fixtures/'command-relay-on.json').read_text())
        command = RelayCommand.model_validate(wire)
        for value in (None, 'true', 1):
            with self.assertRaises(ValidationError): RelayCommand.model_validate(wire | {'desired_on':value})
        auto = RelayCommand.model_validate({k:v for k,v in wire.items() if k!='desired_on'} | {'type':'relay.auto'})
        with self.assertRaises(ValidationError): RelayCommand.model_validate(wire | {'type':'relay.auto'})
        result = CommandResult.model_validate(json.loads((fixtures/'result-applied.json').read_text()))
        result = result.model_copy(update={'command_id':auto.command_id,'binding_id':auto.binding_id,
            'device_id':auto.device_id,'observed_on':False})
        validate_command_result(result, auto)
        with self.assertRaises(ContractError): validate_command_result(result, command)

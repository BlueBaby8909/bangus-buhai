"""Disposable browser-test API. Never import from application code or run against live data."""
import json
import tempfile
from pathlib import Path
from datetime import timedelta
from dataclasses import replace
from uuid import uuid4
from fastapi import Request
from sqlmodel import Session
import uvicorn
from backend.tests.mqtt_support import DatabaseFixture
from backend.tests.auth_support import FakeAuth
from backend.tests.registry_support import SimulatedDevice
from backend.database.models import UserIdentity, Hatchery, Membership, Tank, Device, Binding
from backend.core.application import create_app
from backend.features.accounts.service import AccountService
from backend.features.commands.service import CommandService
from backend.features.registry.service import RegistryService
from backend.features.registry.owner import prepare


def main():
    fixture=DatabaseFixture();fixture.setUpClass();fixture.setUp()
    fake=FakeAuth();fake.settings=replace(fake.settings,origins=('http://127.0.0.1:5189',))
    accounts=AccountService(fake.settings,fixture.engine,fake.provider,lambda:fixture.clock)
    other=uuid4();second=uuid4()
    with Session(fixture.engine) as s,s.begin():
        user=s.get(UserIdentity,fixture.user);user.provider_issuer=fake.settings.issuer;user.provider_subject=fake.subject
        s.get(Tank,fixture.tank).name='Nursery A'
        s.add(Hatchery(id=other,name='Second hatchery'));s.flush();s.add(Membership(hatchery_id=other,user_id=fixture.user))
        s.add(Tank(hatchery_id=other,name='Second hatchery tank'))
        s.add(Device(id=second,hatchery_id=fixture.hatchery,external_id='BB-000000000022',display_name='Second sensor'));s.flush()
        s.add(Binding(device_id=second,tank_id=fixture.tank,hatchery_id=fixture.hatchery,started_at=fixture.clock-timedelta(hours=1)))
    fixture.process(fixture.event(measured_at=fixture.clock.isoformat().replace('+00:00','Z')))
    agent=SimulatedDevice('BB-000000000033')
    temp=tempfile.TemporaryDirectory(prefix='bb-browser-synthetic-')
    output=Path(temp.name)/'claim.json'
    prepare(fixture.engine,agent.external_id,agent.pem,output,clock=lambda:fixture.clock)
    code=json.loads(output.read_text())['claim_code']
    app=create_app(service=accounts)
    commands=CommandService(fixture.engine,fake.settings.token_key,lambda:fixture.clock)
    registry=RegistryService(fixture.engine,fake.settings.token_key,lambda:fixture.clock)

    @app.get('/health')
    def health():return {'status':'ok','synthetic':True}

    @app.get('/__test/context')
    def context():return dict(hatchery=str(fixture.hatchery),other=str(other),tank=str(fixture.tank),device=fixture.agent.external_id,claim_device=agent.external_id,claim_code=code)

    @app.post('/__test/reading')
    async def reading(request:Request):
        fixture.clock+=timedelta(seconds=1)
        options=await request.json() if await request.body() else {}
        payload=fixture.event(seq=int(fixture.clock.timestamp())%4000000000,measured_at=fixture.clock.isoformat().replace('+00:00','Z'))
        payload['readings']['temperature']['value']=options.get('temperature',29.4)
        return dict(disposition=fixture.process(payload).disposition)

    @app.post('/__test/advance')
    async def advance(request:Request):
        fixture.clock+=timedelta(seconds=(await request.json()).get('seconds',1801));return {'ok':True}

    @app.post('/__test/apply')
    def apply():
        submitted=commands.dispatch(lambda wire:1)
        for intent,attempt in submitted:commands.published(attempt)
        latest=commands.latest(fixture.hatchery,fixture.agent.external_id,fixture.user)
        if latest:
            wire=latest['command'];payload=dict(schema_version=1,device_id=fixture.agent.external_id,binding_id=str(fixture.binding),boot_id=str(uuid4()),seq=200,capture_uptime_ms=5000,time_quality='synchronized',created_at=fixture.clock.isoformat().replace('+00:00','Z'),command_id=str(wire['command_id']),result='applied',reason='applied',observed_on=wire.get('desired_on',False))
            fixture.process(payload,topic=fixture.topic.replace('/telemetry','/command-results'))
        return {'ok':True}

    @app.post('/__test/prove')
    def prove():
        challenge=registry.challenge(agent.external_id,'sync',None,None,'synthetic-browser-device')
        result=registry.proof(challenge['challenge_id'],agent.signature(challenge),'synthetic-browser-device')
        config=result['configuration']
        challenge=registry.challenge(agent.external_id,'confirm',config['document']['revision'],config['digest'],'synthetic-browser-device')
        registry.proof(challenge['challenge_id'],agent.signature(challenge),'synthetic-browser-device')
        return {'ok':True}
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8019,ws='wsproto',proxy_headers=False,log_level='warning'))
    @app.post('/__test/shutdown')
    def shutdown():server.should_exit=True;return {'ok':True}
    try:server.run()
    finally:
        fake.client.close();fixture.doCleanups();fixture.tearDownClass();temp.cleanup()


if __name__=='__main__':main()

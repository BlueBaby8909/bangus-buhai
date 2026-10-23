"""Owner-run authenticated unloaded-relay exercise. No credentials are saved."""
import argparse
import getpass
import json
import time
from uuid import UUID, uuid4
import httpx
from backend.core.config import AuthSettings


def exercise(client, path):
    """One authenticated session; sequential ON/OFF/AUTO and API retry checks."""
    for label, body in (
        ('ON', {'type':'relay.set','desired_on':True}),
        ('OFF', {'type':'relay.set','desired_on':False}),
        ('AUTO', {'type':'relay.auto'}),
    ):
        key=str(uuid4())
        print(f'{label}: sending...',flush=True)
        response=client.post(path,json=body,headers={'Idempotency-Key':key})
        if response.status_code!=202:
            print(f'{label}: HTTP {response.status_code}; exercise stopped.',flush=True)
            raise RuntimeError('Command admission unavailable')
        command=response.json()['command_id']
        print('Command:',command,flush=True)
        deadline=time.monotonic()+70
        while True:
            response=client.get(path+'/'+command)
            if response.status_code!=200: raise RuntimeError('Command status unavailable')
            row=response.json()
            if row['status'] in ('applied','rejected','failed','timed_out'):
                break
            if time.monotonic()>=deadline:
                print(f'{label}: no final result; outcome unknown. Exercise stopped.',flush=True)
                raise RuntimeError('No final command result')
            time.sleep(.5)
        print(f"{label}: {row['status']} (command {command})",flush=True)
        if row['status']!='applied':
            print('Exercise stopped; timeout does not prove ON or OFF.',flush=True)
            raise RuntimeError('Command was not applied')
        repeated=client.post(path,json=body,headers={'Idempotency-Key':key})
        if repeated.status_code!=202 or repeated.json()['command_id']!=command:
            raise RuntimeError('Idempotent retry failed')
        print(f'{label}: duplicate request kept the same command. Watch relay/LCD.',flush=True)
        if label!='AUTO': time.sleep(3)
    print('API cycle passed. Report whether the relay went ON then OFF and LCD returned to AUTO.',flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('on', 'off', 'auto', 'status', 'exercise'))
    parser.add_argument('--hatchery', type=UUID, required=True)
    parser.add_argument('--device', default='BB-14C19FC68C60')
    parser.add_argument('--idempotency-key', type=UUID)
    parser.add_argument('--command', type=UUID)
    args = parser.parse_args()
    import re
    if not re.fullmatch(r'BB-[0-9A-F]{12}',args.device) or (args.action=='status' and args.command is None):
        parser.error('Use a canonical device ID and --command for status')
    settings = AuthSettings.load()
    email = input('Operator email: ').strip()
    password = getpass.getpass('Password (hidden): ')
    path=f'/api/v1/hatcheries/{args.hatchery}/devices/{args.device}/commands'
    logged_in=False
    with httpx.Client(base_url='http://127.0.0.1:8001', timeout=15, trust_env=False,
                      headers={'Origin':settings.origins[0]}) as client:
        try:
            response=client.post('/api/v1/auth/login',json={'email':email,'password':password})
            password=None
            if response.status_code!=200: raise RuntimeError(f'Login unavailable (HTTP {response.status_code})')
            logged_in=True; client.headers['X-CSRF-Token']=response.json()['csrf_token']
            if args.action=='exercise':
                exercise(client,path)
                return
            command=args.command
            if args.action!='status':
                key=args.idempotency_key or uuid4()
                body={'type':'relay.auto'} if args.action=='auto' else {'type':'relay.set','desired_on':args.action=='on'}
                print('Unloaded relay:',args.device,'action:',args.action,'idempotency key:',key,flush=True)
                response=client.post(path,json=body,headers={'Idempotency-Key':str(key)})
                if response.status_code!=202:
                    raise RuntimeError(f'Command unavailable (HTTP {response.status_code}, code {response.json().get("error",{}).get("code","unknown")})')
                command=response.json()['command_id']
                print('Persisted command:',command,'(acceptance does not prove actuation)',flush=True)
            deadline=time.monotonic()+70; last=None
            while True:
                response=client.get(path+'/'+str(command))
                if response.status_code!=200: raise RuntimeError(f'Status unavailable (HTTP {response.status_code})')
                row=response.json()
                snapshot={'command_id':row['command_id'],'status':row['status'],'timed_out_at':row['timed_out_at'],
                    'attempts':len(row['attempts']),'results':row['results']}
                if snapshot!=last: print(json.dumps(snapshot),flush=True); last=snapshot
                if args.action=='status' or row['status'] in ('applied','rejected','failed','timed_out') or time.monotonic()>=deadline:
                    break
                time.sleep(1)
            if row['status']=='timed_out': print('Outcome unknown; timeout does not mean ON or OFF. Query this command again for late evidence.')
        finally:
            if logged_in:
                try:
                    if client.post('/api/v1/auth/logout').status_code!=204: print('Logout unavailable; normal session expiry applies.')
                except httpx.HTTPError: print('Logout unavailable; normal session expiry applies.')


if __name__=='__main__':
    try: main()
    except (RuntimeError,ValueError,OSError,httpx.HTTPError):
        raise SystemExit('Live command exercise unavailable; check local API, account access and recorded command status. No secrets printed.') from None

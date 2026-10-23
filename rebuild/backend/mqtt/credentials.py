"""Explicit preparation of separate private MQTT logins; never contact the broker."""
import argparse
import json
from pathlib import Path
import re
import secrets


def prepare(directory, device_id):
    if not re.fullmatch(r'BB-[0-9A-F]{12}', device_id):
        raise ValueError('Invalid canonical device ID')
    directory = Path(directory).resolve()
    repository = Path(__file__).resolve().parents[3]
    if directory.is_relative_to(repository):
        raise ValueError('MQTT login material must be outside the repository')
    # Dedicated directory is created exclusively; existing credentials are never replaced.
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    device = dict(username=device_id, password=secrets.token_urlsafe(32))
    backend = dict(username='BB-REBUILD-INGESTOR', password=secrets.token_urlsafe(32))
    for name, content in [('device-login.json', json.dumps(device, indent=2) + '\n'),
                          ('backend-login.json', json.dumps(backend, indent=2) + '\n'),
                          ('device_mqtt_login.h', '#pragma once\n#define BB_MQTT_USERNAME ' +
                           json.dumps(device['username']) + '\n#define BB_MQTT_PASSWORD ' +
                           json.dumps(device['password']) + '\n')]:
        with (directory / name).open('x', encoding='utf-8', newline='\n') as target:
            target.write(content)
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', required=True)
    parser.add_argument('--directory', type=Path,
                        default=Path.home() / 'BangusBuhai-Secrets/t13a/mqtt-login')
    args = parser.parse_args()
    try:
        directory = prepare(args.directory, args.device)
    except (ValueError, OSError):
        raise SystemExit('Private MQTT preparation unavailable; nothing was overwritten. No secrets printed.') from None
    print('Separate device/backend logins prepared in:', directory)
    print('No broker setting changed. Read login JSON files locally; never paste their contents in chat.')


if __name__ == '__main__':
    main()

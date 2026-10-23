"""Opt-in device-only LAN HTTPS. No account/data initialization or cloud actions."""
import argparse
from datetime import datetime, timedelta, timezone
import ipaddress
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

DEFAULT_DIRECTORY = Path.home() / 'BangusBuhai-Secrets' / 't13a'


def prepare(directory, address):
    address = ipaddress.ip_address(address)
    if not address.is_private or address.is_loopback or address.is_unspecified or address.is_multicast:
        raise ValueError('Use the PC private Wi-Fi address')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)  # Refuse all replacement, including partial material.
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Bangus Buhai T13A local CA')])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=30))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
          .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), False)
          .sign(ca_key, hashes.SHA256()))
    cert = (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, str(address))]))
            .issuer_name(ca.subject).public_key(server_key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=7))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(address)]), False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), False)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()), False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), False)
            .sign(ca_key, hashes.SHA256()))
    files = {'backend-ca.pem': ca.public_bytes(serialization.Encoding.PEM),
             'server-cert.pem': cert.public_bytes(serialization.Encoding.PEM),
             'server-key.pem': server_key.private_bytes(serialization.Encoding.PEM,
                 serialization.PrivateFormat.PKCS8, serialization.NoEncryption()),
             'device_setup_material.h': ('#pragma once\n#define BB_DEVICE_SETUP_URL "https://'
                 + str(address) + ':8443"\n').encode('ascii')}
    # CA signing key is deliberately not retained; replacement requires explicit new material.
    for name, content in files.items():
        with (directory / name).open('xb') as stream:
            stream.write(content)
    return directory


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('action', choices=('prepare', 'serve', 'broker-identity'))
    cli.add_argument('--host', type=ipaddress.IPv4Address)
    cli.add_argument('--directory', type=Path, default=DEFAULT_DIRECTORY)
    args = cli.parse_args()
    if args.action != 'broker-identity' and args.host is None:
        cli.error('--host is required for local HTTPS')
    if args.action == 'prepare':
        prepare(args.directory, str(args.host))
        print('Created private local HTTPS material; existing material was not replaced.')
    elif args.action == 'broker-identity':
        broker_identity(args.directory)
        print('Created separate backend public certificate and private key; upload only mqtt-backend-cert.pem.')
    else:
        import uvicorn
        from backend.core.application import create_app
        app = create_app(device_only=True, device_hosts=(str(args.host),))
        uvicorn.run(app, host=str(args.host), port=8443, proxy_headers=False,
                    ssl_certfile=str(args.directory / 'server-cert.pem'),
                    ssl_keyfile=str(args.directory / 'server-key.pem'), access_log=False)


def broker_identity(directory):
    directory = Path(directory)
    cert_path, key_path = directory / 'mqtt-backend-cert.pem', directory / 'mqtt-backend-key.pem'
    if not directory.is_dir() or cert_path.exists() or key_path.exists():
        raise ValueError('Private directory must exist; backend material must not exist')
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'BB-REBUILD-INGESTOR')])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=90))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), False)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), False)
            .sign(key, hashes.SHA256()))
    created = []
    try:
        for path, content in ((key_path, key.private_bytes(serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8, serialization.NoEncryption())),
                (cert_path, cert.public_bytes(serialization.Encoding.PEM))):
            with path.open('xb') as stream:
                created.append(path)
                stream.write(content)
    except BaseException:
        for path in created: path.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    main()

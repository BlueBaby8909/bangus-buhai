"""Synthetic device keys are generated in memory and never use local device secrets."""
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from backend.features.registry.security import decode, encode


class SimulatedDevice:
    def __init__(self, external_id="BB-000000000011", *, expired=False, client_auth=True, ca=False, key=None):
        self.external_id = external_id
        self.key = key or rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, external_id)])
        clock = datetime.now(timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(self.key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(clock - timedelta(days=2))
            .not_valid_after(clock + timedelta(days=-1 if expired else 30))
            .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True))
        if client_auth:
            cert = cert.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        self.pem = cert.sign(self.key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode()

    def signature(self, challenge):
        return encode(self.key.sign(decode(challenge["signing_input"]),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256()))

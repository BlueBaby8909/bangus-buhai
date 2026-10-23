"""Pinned public credentials and domain-separated setup signatures. No private keys."""
import base64
import hashlib
import json
import re
from datetime import datetime

from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from .errors import RegistryError

DEVICE_PATTERN = r"^BB-[0-9A-F]{12}$"
PREFIX = b"BB-SETUP-V1\n"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def code_hash(code):
    return hashlib.sha256(code.encode("ascii")).hexdigest()


def encode(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Invalid base64url")
    result = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if encode(result) != value:
        raise ValueError("Noncanonical base64url")
    return result


def signing_input(payload):
    return PREFIX + canonical(payload)


def certificate(pem: str, external_id: str, clock: datetime):
    try:
        if not re.fullmatch(DEVICE_PATTERN, external_id) or len(pem.encode()) > 16384:
            raise ValueError()
        stripped = pem.strip()
        if (not stripped.startswith("-----BEGIN CERTIFICATE-----") or
                not stripped.endswith("-----END CERTIFICATE-----") or stripped.count("-----BEGIN ") != 1):
            raise ValueError()
        cert = x509.load_pem_x509_certificate(pem.encode("ascii"))
        key = cert.public_key()
        names = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if len(names) != 1 or names[0].value != external_id:
            raise ValueError()
        if not isinstance(key, rsa.RSAPublicKey) or key.key_size not in (2048, 3072, 4096):
            raise ValueError()
        if not cert.not_valid_before_utc <= clock < cert.not_valid_after_utc:
            raise ValueError()
        if ExtendedKeyUsageOID.CLIENT_AUTH not in cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value:
            raise ValueError()
        if cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise ValueError()
        return cert
    except (ValueError, TypeError, UnicodeError, x509.ExtensionNotFound, x509.DuplicateExtension,
            x509.InvalidVersion, UnsupportedAlgorithm):
        raise RegistryError(401, "invalid_device_credential") from None


def verify(pem, external_id, clock, payload, signature):
    cert = certificate(pem, external_id, clock)
    try:
        cert.public_key().verify(decode(signature), signing_input(payload),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
    except (ValueError, TypeError, InvalidSignature):
        raise RegistryError(401, "invalid_device_proof") from None

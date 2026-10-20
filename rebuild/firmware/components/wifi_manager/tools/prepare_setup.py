"""Create/reuse private, per-device Security 2 material outside the checkout."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import secrets
import sys


def load_srp(firmware):
    tool = firmware / "managed_components/espressif__network_provisioning/tool/esp_prov"
    sys.path.insert(0, str(tool))
    spec = importlib.util.spec_from_file_location("bb_srp", tool / "security/srp6a.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(firmware, destination, device_id):
    if not re.fullmatch(r"BB-[0-9A-F]{12}", device_id):
        raise ValueError("Device ID must be BB- followed by 12 uppercase hex digits")
    firmware = firmware.resolve()
    destination = destination.resolve()
    # Keep generated credentials outside the entire repository, not just firmware.
    checkout = firmware.parents[1]
    if destination.is_relative_to(checkout):
        raise ValueError("Choose a secrets directory outside the repository")
    destination.mkdir(parents=True, exist_ok=True)
    credentials = destination / "wifi-setup.json"
    if credentials.exists():
        data = json.loads(credentials.read_text(encoding="utf-8"))
        if data["device_id"] != device_id:
            raise ValueError("Existing setup material belongs to another device")
        if data["username"] != device_id or data["name"] != "PROV_" + device_id[-6:]:
            raise ValueError("Existing setup identity is invalid")
        if len(data["password"]) < 24 or not re.fullmatch(r"[0-9a-f]{32}", data["salt"]):
            raise ValueError("Existing setup material is invalid; preserve and inspect it")
        if not re.fullmatch(r"[0-9a-f]{768}", data["verifier"]):
            raise ValueError("Existing verifier has an unexpected length")
    else:
        srp = load_srp(firmware)
        # The vendor helper serializes intermediate hashes as integers. Avoid a
        # leading-zero digest/salt so standard fixed-width mobile clients agree.
        while True:
            password = secrets.token_urlsafe(24)
            if hashlib.sha512(f"{device_id}:{password}".encode()).digest()[0] != 0:
                break
        while True:
            salt, verifier = srp.generate_salt_and_verifier(device_id, password, 16)
            if len(salt) == 16:
                break
        verifier = verifier.rjust(384, b"\0")
        data = dict(device_id=device_id, username=device_id, password=password,
                    name="PROV_" + device_id[-6:], salt=salt.hex(), verifier=verifier.hex())
        with credentials.open("x", encoding="utf-8") as output:
            json.dump(data, output, indent=2)
            output.write("\n")

    srp = load_srp(firmware)
    modulus, generator = srp.get_ng(srp.NG_3072)
    inner = hashlib.sha512(f'{data["username"]}:{data["password"]}'.encode()).digest()
    exponent = int.from_bytes(hashlib.sha512(bytes.fromhex(data["salt"]) + inner).digest(), "big")
    if pow(generator, exponent, modulus) != int(data["verifier"], 16):
        raise ValueError("Setup password/salt/verifier mismatch; existing files preserved")

    def array(name, value):
        return f"static const unsigned char {name}[] = {{" + ",".join(
            f"0x{byte:02x}" for byte in value) + "};\n"

    header = "#pragma once\n"
    header += array("bb_setup_mac", bytes.fromhex(device_id[3:]))
    header += array("bb_setup_salt", bytes.fromhex(data["salt"]))
    header += array("bb_setup_verifier", bytes.fromhex(data["verifier"]))
    header += f'#define BB_SETUP_NAME {json.dumps(data["name"])}\n'
    (destination / "wifi_setup_material.h").write_text(header, encoding="utf-8")
    qr = dict(ver="v1", name=data["name"], username=data["username"],
              pop=data["password"], transport="ble", network="wifi")
    (destination / "wifi-setup-qr.json").write_text(json.dumps(qr), encoding="utf-8")
    return credentials


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--directory", type=Path,
                        default=Path.home() / "BangusBuhai-Secrets/t07")
    args = parser.parse_args()
    firmware = Path(__file__).resolve().parents[3]
    path = prepare(firmware, args.directory, args.device_id)
    print(f"Setup material ready. Phone credentials: {path}")
    print("No setup password was printed. Keep these files private and outside Git.")


if __name__ == "__main__":
    main()

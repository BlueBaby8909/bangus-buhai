"""Minimal local setup, always anchored to rebuild/database; never resets data."""

import secrets
import subprocess
import sys
from pathlib import Path

from .config import LOCAL_ENV


def main():
    action = sys.argv[1] if len(sys.argv) == 2 else ""
    if action not in {"up", "stop", "status"}:
        raise SystemExit("Usage: python -m backend.database.local up|stop|status")
    if not LOCAL_ENV.exists():
        if action != "up":
            raise SystemExit("Run 'up' to configure the isolated local database first")
        password = secrets.token_hex(24)
        prefix = f"postgresql+psycopg://bb_rebuild:{password}@127.0.0.1:55432/"
        try:
            with LOCAL_ENV.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(
                    f"BB_POSTGRES_PASSWORD={password}\n"
                    f"BB_DATABASE_URL={prefix}bangus_buhai_rebuild\n"
                    f"BB_TEST_DATABASE_URL={prefix}bangus_buhai_rebuild_test\n"
                )
        except FileExistsError:
            pass  # Another setup process won; never overwrite its configuration.
    arguments = {"up": ["up", "-d", "--wait", "--wait-timeout", "90"],
                 "stop": ["stop"], "status": ["ps"]}[action]
    compose = Path(__file__).resolve().parents[2] / "database" / "compose.yaml"
    raise SystemExit(subprocess.call([
        "docker", "compose", "--project-name", "bangusbuhai-t09",
        "--env-file", str(LOCAL_ENV), "-f", str(compose), *arguments,
    ]))


if __name__ == "__main__":
    main()

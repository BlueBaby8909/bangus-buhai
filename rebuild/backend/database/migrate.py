"""Run from rebuild using: python -m backend.database.migrate."""

from pathlib import Path

from alembic import command
from alembic.config import Config


def configuration() -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
    return config


if __name__ == "__main__":
    command.upgrade(configuration(), "head")

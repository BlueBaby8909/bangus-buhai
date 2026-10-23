from alembic import context
from sqlmodel import SQLModel

from backend.database import models  # noqa: F401: registers migration metadata
from backend.database.config import make_engine


def migrate(connection):
    context.configure(connection=connection, target_metadata=SQLModel.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


connection = context.config.attributes.get("connection")
if connection is not None:
    migrate(connection)
else:
    engine = make_engine()
    try:
        with engine.connect() as connection:
            migrate(connection)
    finally:
        engine.dispose()

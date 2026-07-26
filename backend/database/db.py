import os
from sqlmodel import create_engine, Session, SQLModel

from config import settings

base_dir = os.path.dirname(os.path.abspath(__file__))
default_db_url = f"sqlite:///{os.path.join(base_dir, 'bangusbuhai.db')}"

db_url = settings.database_url or default_db_url

# check_same_thread=False is only needed/valid for sqlite; skip it for other engines
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(db_url, connect_args=connect_args)


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    """Create all tables registered on SQLModel.metadata. Called once at app startup."""
    SQLModel.metadata.create_all(engine)

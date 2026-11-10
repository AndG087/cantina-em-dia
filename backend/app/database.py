from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


# A sessão usa UTC; as datas voltam com fuso pelo tipo UTCDateTime (models.py).
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={'connect_timeout': 3, 'charset': 'utf8mb4', 'init_command': "SET time_zone = '+00:00'"},
    hide_parameters=True,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session():
    with SessionLocal() as session:
        yield session

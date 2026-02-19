from contextlib import contextmanager
from typing import Iterator

from sqlmodel import SQLModel, Session, create_engine

from app.core.config import settings

engine = create_engine(settings.database_url, echo=False)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_db_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session

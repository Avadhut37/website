from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session

from .database import engine


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@contextmanager
def session_scope() -> Iterator[Session]:
    with Session(engine) as session:
        yield session

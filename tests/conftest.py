"""Общие фикстуры для тестов: изолированная тестовая база."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base


@pytest.fixture()
def engine():
    """Создаёт движок с пустой тестовой базой на каждый тест."""
    return create_engine("sqlite://", echo=False)


@pytest.fixture()
def session(engine):
    """Создаёт схему и отдаёт сессию; после теста база умирает сама."""
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    yield session
    session.close()


@pytest.fixture()
def auth_service_session(engine):
    """Подменяет SessionLocal в auth_service на тестовую базу.

    Нужен, потому что функции auth_service открывают сессии сами.
    """
    import services.auth_service as auth_service

    auth_service.SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    return auth_service

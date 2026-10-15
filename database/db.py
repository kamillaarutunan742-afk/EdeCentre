"""Модуль подключения к базе данных.

Создаёт движок SQLAlchemy, фабрику сессий и функцию
инициализации схемы базы данных.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL

# Движок — центральный объект SQLAlchemy, через него идёт вся работа с БД
engine = create_engine(DATABASE_URL, echo=False)

# Фабрика сессий: каждая сессия — одна рабочая транзакция с БД
SessionLocal = sessionmaker(bind=engine)


def get_session():
    """Создаёт и возвращает новую сессию работы с базой данных.

    Returns:
        Session: объект сессии SQLAlchemy для выполнения запросов.
    """
    return SessionLocal()


def init_db() -> None:
    """Создаёт все таблицы в базе данных по описанным моделям."""
    import database.models  # noqa: F401 — импорт регистрирует модели

    from database.models import Base

    Base.metadata.create_all(engine)

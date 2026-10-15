from __future__ import annotations
"""Базовый репозиторий: универсальные CRUD-операции для любой модели.

Реализует принцип DRY: общая логика доступа к данным написана один раз,
конкретные репозитории наследуют её и при необходимости добавляют
специфичные запросы.
"""

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Универсальный репозиторий с CRUD-операциями.

    Attributes:
        model: класс ORM-модели, с которой работает репозиторий.
    """

    def __init__(self, model: type[ModelType], session: Session) -> None:
        """Инициализирует репозиторий.

        Args:
            model: класс ORM-модели (например, Student).
            session: сессия SQLAlchemy для работы с БД.
        """
        self.model = model
        self.session = session

    def create(self, **fields) -> ModelType:
        """Создаёт новую запись.

        Args:
            **fields: значения полей модели.

        Returns:
            ModelType: созданный объект с присвоенным первичным ключом.
        """
        obj = self.model(**fields)
        self.session.add(obj)
        self.session.commit()
        return obj

    def get_by_id(self, obj_id: int) -> ModelType | None:
        """Возвращает запись по первичному ключу.

        Args:
            obj_id: значение первичного ключа.

        Returns:
            Объект модели или None, если запись не найдена.
        """
        return self.session.get(self.model, obj_id)

    def get_all(self) -> list[ModelType]:
        """Возвращает все записи таблицы.

        Returns:
            Список объектов модели.
        """
        return list(self.session.scalars(select(self.model)))

    def update(self, obj: ModelType, **fields) -> ModelType:
        """Обновляет поля существующей записи.

        Args:
            obj: объект модели для обновления.
            **fields: новые значения полей.

        Returns:
            ModelType: обновлённый объект.
        """
        for name, value in fields.items():
            setattr(obj, name, value)
        self.session.commit()
        return obj

    def delete(self, obj: ModelType) -> None:
        """Удаляет запись из базы данных.

        Args:
            obj: объект модели для удаления.
        """
        self.session.delete(obj)
        self.session.commit()

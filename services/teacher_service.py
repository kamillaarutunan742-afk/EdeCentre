from __future__ import annotations
"""Сервис преподавателей: CRUD."""

from sqlalchemy.orm import Session

from database.models import Teacher
from repositories.base_repository import BaseRepository


class TeacherService:
    """Бизнес-логика работы с преподавателями."""

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.repo = BaseRepository(Teacher, session)

    def create_teacher(self, full_name: str, **fields) -> Teacher:
        """Создаёт преподавателя с валидацией имени.

        Args:
            full_name: полное имя.
            **fields: остальные поля модели.

        Returns:
            Созданный объект Teacher.

        Raises:
            ValueError: если имя пустое.
        """
        if not full_name.strip():
            raise ValueError("ФИО преподавателя не может быть пустым")
        return self.repo.create(full_name=full_name.strip(), **fields)

    def get_teacher(self, teacher_id: int) -> Teacher | None:
        """Возвращает преподавателя по идентификатору."""
        return self.repo.get_by_id(teacher_id)

    def get_all_teachers(self) -> list[Teacher]:
        """Возвращает всех преподавателей."""
        return self.repo.get_all()

    def update_teacher(self, teacher: Teacher, **fields) -> Teacher:
        """Обновляет данные преподавателя."""
        return self.repo.update(teacher, **fields)

    def delete_teacher(self, teacher: Teacher) -> None:
        """Удаляет преподавателя (группы остаются без него)."""
        self.repo.delete(teacher)

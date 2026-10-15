from __future__ import annotations
"""Сервис групп: создание групп и работа с составом."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Group, GroupStudent, Student
from repositories.base_repository import BaseRepository

DIRECTIONS = ("Английский", "Немецкий", "Французский", "Испанский")
LEVELS = ("beginner", "elementary", "intermediate", "advanced")


class GroupService:
    """Бизнес-логика групп и зачисления учеников."""

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.repo = BaseRepository(Group, session)

    def get_all(self) -> list[Group]:
        """Возвращает все группы."""
        return self.repo.get_all()

    def get_by_id(self, group_id: int) -> Group | None:
        """Возвращает группу по идентификатору.

        Args:
            group_id: идентификатор группы.

        Returns:
            Объект Group или None.
        """
        return self.session.get(Group, group_id)

    def _extra_fields(self) -> list[str]:
        """Собирает необязательные числовые колонки модели группы.

        Returns:
            Список названий колонок, которые есть в модели.
        """
        columns = Group.__table__.columns.keys()
        return [
            name
            for name in (
                "lessons_per_week",
                "capacity",
                "max_students",
                "age_range",
                "age_group",
                "teacher_id",
            )
            if name in columns
        ]

    def create_group(
        self,
        name: str,
        direction: str,
        age_range: str,
        level: str,
        number: int = 12,
        teacher_id: int | None = None,
    ) -> Group:
        """Создаёт группу с валидацией и адаптацией под модель.

        Args:
            name: название группы.
            direction: направление (язык).
            age_range: возрастная категория («7-10», «18+»).
            level: код уровня.
            number: число (занятий в неделю или размер группы — как в модели).
            teacher_id: идентификатор преподавателя (опционально).

        Returns:
            Созданный объект Group.

        Raises:
            ValueError: при некорректных данных или дубле названия.
        """
        if not name.strip():
            raise ValueError("Название группы не может быть пустым")
        if direction not in DIRECTIONS:
            raise ValueError("Выберите направление из списка")
        if level not in LEVELS:
            raise ValueError("Выберите уровень из списка")
        existing = self.session.scalar(select(Group).where(Group.name == name.strip()))
        if existing is not None:
            raise ValueError("Группа с таким названием уже существует")
        try:
            number = int(number)
        except (TypeError, ValueError):
            raise ValueError("Число занятий или размер группы должно быть числом")
        if number <= 0:
            raise ValueError("Число должно быть больше нуля")

        columns = Group.__table__.columns.keys()
        kwargs: dict = {
            "name": name.strip(),
            "direction": direction,
            "level": level,
        }
        for field in ("age_range", "age_group"):
            if field in columns and age_range.strip():
                kwargs[field] = age_range.strip()
                break
        for field in ("lessons_per_week", "capacity", "max_students"):
            if field in columns:
                kwargs[field] = number
                break
        if teacher_id is not None and "teacher_id" in columns:
            kwargs["teacher_id"] = teacher_id
        return self.repo.create(**kwargs)

    def add_student(self, group: Group, student_id: int) -> GroupStudent:
        """Зачисляет ученика в группу.

        Args:
            group: объект группы.
            student_id: идентификатор ученика.

        Returns:
            Созданная связь GroupStudent.

        Raises:
            ValueError: если ученик не найден или уже в группе.
        """
        student = self.session.get(Student, student_id)
        if student is None:
            raise ValueError("Ученик не найден")
        existing = self.session.scalar(
            select(GroupStudent).where(
                GroupStudent.group_id == group.group_id,
                GroupStudent.student_id == student_id,
            )
        )
        if existing is not None:
            raise ValueError("Ученик уже зачислен в эту группу")
        link = GroupStudent(group_id=group.group_id, student_id=student_id)
        self.session.add(link)
        self.session.commit()
        self.session.refresh(link)
        return link

    def remove_student(self, group: Group, student_id: int) -> None:
        """Исключает ученика из группы.

        Args:
            group: объект группы.
            student_id: идентификатор ученика.
        """
        link = self.session.scalar(
            select(GroupStudent).where(
                GroupStudent.group_id == group.group_id,
                GroupStudent.student_id == student_id,
            )
        )
        if link is not None:
            self.session.delete(link)
            self.session.commit()

    def get_students(self, group: Group) -> list:
        """Возвращает учеников группы объектами Student.

        Args:
            group: объект группы.

        Returns:
            Список объектов Student.
        """
        result = []
        for item in group.students:
            if hasattr(item, "full_name"):
                result.append(item)
                continue
            student = self.session.get(Student, item.student_id)
            if student is not None:
                result.append(student)
        return result

    def get_table_rows(self) -> list[tuple]:
        """Собирает строки для таблицы групп.

        Returns:
            Кортежи (id, название, направление, возраст, уровень,
            преподаватель, число учеников).
        """
        rows = []
        for group in self.get_all():
            teacher = getattr(group, "teacher", None)
            teacher_name = teacher.full_name if teacher is not None else "—"
            level = getattr(group, "level", "") or ""
            level_text = {
                "beginner": "Начинающий",
                "elementary": "Элементарный",
                "intermediate": "Средний",
                "advanced": "Продвинутый",
            }.get(level, level or "—")
            age = (
                getattr(group, "age_range", None)
                or getattr(group, "age_group", None)
                or "—"
            )
            rows.append(
                (
                    group.group_id,
                    group.name,
                    getattr(group, "direction", "") or "—",
                    age,
                    level_text,
                    teacher_name,
                    len(self.get_students(group)),
                )
            )
        return rows

    def delete(self, group: Group) -> None:
        """Удаляет группу.

        Args:
            group: объект группы.
        """
        self.session.delete(group)
        self.session.commit()

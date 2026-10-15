from __future__ import annotations
"""Сервис учеников: CRUD, поиск и данные для таблицы экрана."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import (
    Attendance,
    Group,
    GroupStudent,
    Payment,
    Student,
    Subscription,
)
from repositories.base_repository import BaseRepository


class StudentService:
    """Бизнес-логика работы с учениками."""

    VALID_STATUSES = ("active", "frozen", "archived")

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.repo = BaseRepository(Student, session)

    def create_student(self, full_name: str, **fields) -> Student:
        """Создаёт ученика с валидацией имени.

        Args:
            full_name: полное имя (обязательно).
            **fields: остальные поля модели Student.

        Returns:
            Созданный объект Student.

        Raises:
            ValueError: если имя пустое или статус некорректен.
        """
        if not full_name.strip():
            raise ValueError("ФИО ученика не может быть пустым")
        status = fields.get("status", "active")
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Недопустимый статус: {status}")
        fields.setdefault("enroll_date", date.today())
        return self.repo.create(full_name=full_name.strip(), **fields)

    def get_student(self, student_id: int) -> Student | None:
        """Возвращает ученика по идентификатору."""
        return self.repo.get_by_id(student_id)

    def get_all_students(self) -> list[Student]:
        """Возвращает всех учеников."""
        return self.repo.get_all()

    def search_students(self, query: str) -> list[Student]:
        """Ищет учеников по подстроке в ФИО.

        Args:
            query: поисковая строка.

        Returns:
            Список подходящих объектов Student.
        """
        query = (query or "").strip()
        if not query:
            return self.get_all_students()
        return list(
            self.session.scalars(
                select(Student).where(Student.full_name.ilike(f"%{query}%"))
            )
        )

    def update_student(self, student: Student, **fields) -> Student:
        """Обновляет данные ученика.

        Args:
            student: объект Student.
            **fields: новые значения полей.

        Returns:
            Обновлённый объект.

        Raises:
            ValueError: если имя пустое или статус некорректен.
        """
        if "full_name" in fields and not fields["full_name"].strip():
            raise ValueError("ФИО ученика не может быть пустым")
        if "status" in fields and fields["status"] not in self.VALID_STATUSES:
            raise ValueError(f"Недопустимый статус: {fields['status']}")
        return self.repo.update(student, **fields)

    def delete_student(self, student: Student) -> None:
        """Удаляет ученика вместе со всеми связанными данными.

        Порядок удаления важен: сначала записи, ссылающиеся на
        абонементы (посещаемость), затем платежи и абонементы,
        затем связь с группами и сам ученик.

        Args:
            student: объект ученика.
        """
        student_id = student.student_id
        self.session.query(Attendance).filter(
            Attendance.student_id == student_id
        ).delete()
        self.session.query(Payment).filter(Payment.student_id == student_id).delete()
        self.session.query(Subscription).filter(
            Subscription.student_id == student_id
        ).delete()
        self.session.query(GroupStudent).filter(
            GroupStudent.student_id == student_id
        ).delete()
        self.repo.delete(student)

    def get_table_rows(self) -> list[tuple]:
        """Собирает данные для таблицы учеников: группа, абонемент, долг.

        Returns:
            Список кортежей (id, ФИО, телефон, группа, абонемент, долг).
        """
        links = self.session.scalars(select(GroupStudent)).all()
        groups_by_student: dict[int, list[str]] = {}
        for link in links:
            group = self.session.get(Group, link.group_id)
            if group:
                groups_by_student.setdefault(link.student_id, []).append(group.name)

        subs_by_student: dict[int, str] = {}
        price_by_student: dict[int, float] = {}
        for sub in self.session.scalars(
            select(Subscription).where(Subscription.status == "active")
        ):
            if sub.subscription_type:
                subs_by_student[sub.student_id] = sub.subscription_type.name
                price_by_student[sub.student_id] = (
                    price_by_student.get(sub.student_id, 0)
                    + sub.subscription_type.price
                )

        paid: dict[int, float] = dict(
            self.session.execute(
                select(
                    Payment.student_id,
                    func.coalesce(func.sum(Payment.amount), 0.0),
                ).group_by(Payment.student_id)
            ).all()
        )

        rows = []
        for student in self.get_all_students():
            sid = student.student_id
            debt = max(price_by_student.get(sid, 0) - paid.get(sid, 0), 0)
            rows.append(
                (
                    sid,
                    student.full_name,
                    student.phone or "—",
                    ", ".join(groups_by_student.get(sid, [])) or "—",
                    subs_by_student.get(sid, "—"),
                    debt,
                )
            )
        return rows

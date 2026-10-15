from __future__ import annotations
"""Сервис посещаемости: отметки занятий, списание абонементов, правка статусов."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    Attendance,
    Group,
    GroupStudent,
    Student,
    Subscription,
    SubscriptionType,
)
from repositories.base_repository import BaseRepository


class AttendanceService:
    """Бизнес-логика посещаемости."""

    STATUS_LABELS = {
        "present": "Присутствовал",
        "absent": "Отсутствовал",
        "sick": "Болел",
    }

    VALID_STATUSES = frozenset(STATUS_LABELS)

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.repo = BaseRepository(Attendance, session)

    def get_all_attendance(self) -> list[Attendance]:
        """Возвращает все отметки.

        Returns:
            Список объектов Attendance.
        """
        return self.repo.get_all()

    def _resolve_students(self, group: Group) -> list[Student]:
        """Превращает связи группы в объекты Student.

        Args:
            group: объект группы.

        Returns:
            Список учеников группы.
        """
        students: list[Student] = []
        for item in group.students:
            if hasattr(item, "full_name"):
                students.append(item)
                continue
            student = self.session.get(Student, item.student_id)
            if student is not None:
                students.append(student)
        return students

    def _active_subscription(self, student_id: int) -> Subscription | None:
        """Возвращает активный абонемент ученика.

        Args:
            student_id: идентификатор ученика.

        Returns:
            Объект Subscription или None.
        """
        return self.session.scalars(
            select(Subscription).where(
                Subscription.student_id == student_id,
                Subscription.status == "active",
            )
        ).first()

    def _spend_lesson(self, subscription: Subscription) -> None:
        """Списывает одно занятие с абонемента.

        Args:
            subscription: объект абонемента.

        Raises:
            ValueError: если занятий не осталось.
        """
        if subscription.remaining_lessons <= 0:
            raise ValueError("Занятия абонемента исчерпаны")
        subscription.remaining_lessons -= 1
        if subscription.remaining_lessons == 0:
            subscription.status = "exhausted"

    def _refund_lesson(self, subscription: Subscription) -> None:
        """Возвращает занятие на абонемент.

        Args:
            subscription: объект абонемента.
        """
        if subscription.remaining_lessons < subscription.total_lessons:
            subscription.remaining_lessons += 1
        if subscription.status != "active":
            subscription.status = "active"

    def mark_lesson(self, group: Group, lesson_date, statuses: dict[int, str]) -> None:
        """Отмечает посещаемость группы на дату.

        Повторная отметка не создаёт дубликатов и не списывает занятие
        второй раз: при изменении статуса абонемент корректируется.

        Args:
            group: объект группы.
            lesson_date: дата занятия.
            statuses: словарь {student_id: статус}.

        Raises:
            ValueError: если у группы нет учеников.
        """
        students = self._resolve_students(group)
        if not students:
            raise ValueError("В этой группе нет учеников")

        for student in students:
            status = statuses.get(student.student_id, "absent")
            record = self.session.scalar(
                select(Attendance).where(
                    Attendance.student_id == student.student_id,
                    Attendance.lesson_date == lesson_date,
                )
            )
            subscription = self._active_subscription(student.student_id)

            if record is None:
                # новая отметка: списываем занятие только присутствовавшим
                spent = False
                if status == "present" and subscription is not None:
                    try:
                        self._spend_lesson(subscription)
                        spent = True
                    except ValueError:
                        spent = False
                self.repo.create(
                    student_id=student.student_id,
                    group_id=group.group_id,
                    lesson_date=lesson_date,
                    status=status,
                    subscription_id=(
                        subscription.subscription_id if spent else None
                    ),
                )
                continue

            # отметка за этот день уже есть — дубля не создаём
            old_status = record.status
            if old_status == status:
                continue

            linked = (
                self.session.get(Subscription, record.subscription_id)
                if record.subscription_id
                else subscription
            )
            if old_status == "present" and status != "present":
                # присутствие сняли — возвращаем занятие
                if linked is not None:
                    self._refund_lesson(linked)
                record.subscription_id = None
            elif old_status != "present" and status == "present":
                # присутствие поставили задним числом — списываем занятие
                if linked is not None:
                    try:
                        self._spend_lesson(linked)
                        record.subscription_id = linked.subscription_id
                    except ValueError:
                        record.subscription_id = None

            record.status = status
            if record.group_id is None:
                record.group_id = group.group_id

        self.session.commit()

    def set_status(self, attendance_id: int, status: str) -> None:
        """Меняет статус существующей отметки с корректировкой абонемента.

        Args:
            attendance_id: идентификатор отметки.
            status: present / absent / sick.

        Raises:
            ValueError: если статус неизвестен или отметка не найдена.
        """
        if status not in self.VALID_STATUSES:
            raise ValueError("Недопустимый статус")
        record = self.session.get(Attendance, attendance_id)
        if record is None:
            raise ValueError("Отметка не найдена")

        old_status = record.status
        if old_status == status:
            return

        subscription = (
            self.session.get(Subscription, record.subscription_id)
            if record.subscription_id
            else self._active_subscription(record.student_id)
        )

        if old_status == "present" and status != "present":
            # сняли присутствие — занятие возвращается на абонемент
            if subscription is not None:
                self._refund_lesson(subscription)
            record.subscription_id = None
        elif old_status != "present" and status == "present":
            # поставили присутствие — списываем занятие
            if subscription is not None:
                try:
                    self._spend_lesson(subscription)
                    record.subscription_id = subscription.subscription_id
                except ValueError:
                    record.subscription_id = None

        record.status = status
        self.session.commit()

    def get_table_rows(self, group_id: int | None = None) -> list[tuple]:
        """Собирает строки для таблицы посещаемости.

        Args:
            group_id: фильтр по группе (None — все группы).

        Returns:
            Кортежи (id, дата, группа, ученик, статус, абонемент, списано).
        """
        student_ids = None
        if group_id is not None:
            student_ids = {
                link.student_id
                for link in self.session.scalars(
                    select(GroupStudent).where(GroupStudent.group_id == group_id)
                )
            }
        rows = []
        records = sorted(
            self.repo.get_all(), key=lambda r: r.lesson_date, reverse=True
        )
        for record in records:
            if student_ids is not None and record.student_id not in student_ids:
                continue
            student = self.session.get(Student, record.student_id)
            if student is None:
                continue
            group_name = "—"
            if getattr(record, "group_id", None):
                group = self.session.get(Group, record.group_id)
                if group is not None:
                    group_name = group.name
            if group_name == "—":
                for link in self.session.scalars(
                    select(GroupStudent).where(
                        GroupStudent.student_id == student.student_id
                    )
                ):
                    group = self.session.get(Group, link.group_id)
                    if group is not None:
                        group_name = group.name
                        break

            sub_name = "—"
            latest_sub = self.session.scalars(
                select(Subscription)
                .where(Subscription.student_id == student.student_id)
                .order_by(Subscription.subscription_id.desc())
            ).first()
            if latest_sub is not None:
                sub_type = latest_sub.subscription_type
                if sub_type is None and getattr(latest_sub, "type_id", None):
                    sub_type = self.session.get(
                        SubscriptionType, latest_sub.type_id
                    )
                if sub_type is not None:
                    sub_name = sub_type.name

            spent = "-1" if record.status == "present" else "—"
            rows.append(
                (
                    record.attendance_id,
                    str(record.lesson_date),
                    group_name,
                    student.full_name,
                    self.STATUS_LABELS.get(record.status, record.status),
                    sub_name,
                    spent,
                )
            )
        return rows

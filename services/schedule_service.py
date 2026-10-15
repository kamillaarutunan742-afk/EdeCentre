"""Сервис расписания: занятия с обязательной датой и контролем конфликтов."""

from datetime import date, datetime

from sqlalchemy import select

from database.db import SessionLocal
from database.models import Group, Schedule, Teacher

DAYS = (
    "Понедельник", "Вторник", "Среда", "Четверг",
    "Пятница", "Суббота", "Воскресенье",
)

WEEKDAY_TO_NAME = {
    0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг",
    4: "Пятница", 5: "Суббота", 6: "Воскресенье",
}


def _to_minutes(time_text: str) -> int:
    """Переводит строку 'ЧЧ:ММ' в минуты от полуночи.

    Args:
        time_text: время в формате ЧЧ:ММ.

    Returns:
        Количество минут.
    """
    parts = time_text.strip().split(":")
    return int(parts[0]) * 60 + int(parts[1])


class ScheduleService:
    """Управление расписанием занятий."""

    def __init__(self, session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session

    def get_all(self) -> list[Schedule]:
        """Возвращает все занятия, отсортированные по дате и времени."""
        return list(
            self.session.scalars(
                select(Schedule).order_by(Schedule.lesson_date, Schedule.start_time)
            )
        )

    def get_lessons_by_date(self, lesson_date: date) -> list[Schedule]:
        """Возвращает занятия на конкретную дату.

        Args:
            lesson_date: дата занятия.

        Returns:
            Список занятий.
        """
        return list(
            self.session.scalars(
                select(Schedule)
                .where(Schedule.lesson_date == lesson_date)
                .order_by(Schedule.start_time)
            )
        )

    def get_table_rows(self) -> list[tuple]:
        """Формирует строки для таблицы расписания.

        Returns:
            Список кортежей (id, дата, время, группа, преподаватель, кабинет).
        """
        rows = []
        for lesson in self.get_all():
            group = lesson.group
            teacher = group.teacher if group is not None else None
            date_text = (
                lesson.lesson_date.strftime("%d.%m.%Y")
                if lesson.lesson_date
                else lesson.day_of_week
            )
            rows.append(
                (
                    lesson.schedule_id,
                    date_text,
                    f"{lesson.start_time}–{lesson.end_time}" if lesson.end_time
                    else lesson.start_time,
                    group.name if group is not None else "",
                    teacher.full_name if teacher is not None else "",
                    lesson.room or "",
                )
            )
        return rows

    def create_lesson(
        self,
        group_id: int,
        lesson_date: date,
        start: str,
        end: str = "",
        room: str = "",
    ) -> Schedule:
        """Создаёт занятие с обязательной датой и проверкой конфликтов.

        Args:
            group_id: идентификатор группы.
            lesson_date: дата занятия (обязательна).
            start: время начала ЧЧ:ММ.
            end: время окончания ЧЧ:ММ.
            room: кабинет.

    Returns:
            Созданное занятие.

        Raises:
            ValueError: если данные неполны или занятие пересекается
                с другим занятием той же группы.
        """
        if lesson_date is None:
            raise ValueError("Дата занятия обязательна")
        start = start.strip()
        if not start:
            raise ValueError("Укажите время начала")
        try:
            start_minutes = _to_minutes(start)
            end_minutes = _to_minutes(end) if end.strip() else start_minutes + 60
        except (ValueError, IndexError):
            raise ValueError("Время в формате ЧЧ:ММ")
        if end_minutes <= start_minutes:
            raise ValueError("Окончание должно быть позже начала")

        conflicts = [
            lesson
            for lesson in self.get_lessons_by_date(lesson_date)
            if lesson.group_id == group_id
            and _to_minutes(lesson.start_time) < end_minutes
            and (_to_minutes(lesson.end_time or lesson.start_time) > start_minutes)
        ]
        if conflicts:
            raise ValueError(
                "Конфликт: у группы уже есть занятие "
                f"{conflicts[0].start_time} в этот день"
            )

        lesson = Schedule(
            group_id=group_id,
            lesson_date=lesson_date,
            day_of_week=WEEKDAY_TO_NAME[lesson_date.weekday()],
            start_time=start,
            end_time=end.strip(),
            room=room.strip(),
        )
        self.session.add(lesson)
        self.session.commit()
        return lesson

    def delete(self, lesson: Schedule) -> None:
        """Удаляет занятие.

        Args:
            lesson: объект занятия.
        """
        self.session.delete(lesson)
        self.session.commit()

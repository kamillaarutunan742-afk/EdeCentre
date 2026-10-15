"""Сервис отчётов: агрегированные показатели для дашборда."""

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import (
    Attendance,
    Group,
    GroupStudent,
    Notification,
    Payment,
    Schedule,
    Student,
    Subscription,
    Teacher,
)
from services.attendance_service import AttendanceService
from services.payment_service import PaymentService


class ReportService:
    """Агрегированные показатели приложения."""

    DAY_ORDER = (
        "Понедельник",
        "Вторник",
        "Среда",
        "Четверг",
        "Пятница",
        "Суббота",
        "Воскресенье",
    )

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.payments = PaymentService(session)

    def _count(self, model) -> int:
        """Считает записи таблицы.

        Args:
            model: ORM-модель.

        Returns:
            Количество записей.
        """
        return self.session.scalar(select(func.count()).select_from(model)) or 0

    def get_dashboard_stats(self) -> dict:
        """Собирает показатели для дашборда.

        Returns:
            Словарь со счётчиками и выручкой за текущий месяц.
        """
        month_start = date.today().replace(day=1)
        return {
            "Учеников": self._count(Student),
            "Групп": self._count(Group),
            "Преподавателей": self._count(Teacher),
            "Активных абонементов": self.session.scalar(
                select(func.count(Subscription.subscription_id)).where(
                    Subscription.status == "active"
                )
            )
            or 0,
            "Выручка за месяц, ₽": self.payments.get_revenue(month_start, date.today()),
        }

    def get_group_sizes(self) -> list[tuple[str, int]]:
        """Возвращает пары «название группы — число учеников».

        Returns:
            Список кортежей (название, количество).
        """
        return [
            (group.name, len(group.students))
            for group in self.session.scalars(select(Group))
        ]

    def get_week_attendance(self) -> int:
        """Считает посещения за последние 7 дней.

        Returns:
            Количество отметок «присутствовал».
        """
        start = date.today() - timedelta(days=7)
        return (
            self.session.scalar(
                select(func.count(Attendance.attendance_id)).where(
                    Attendance.lesson_date >= start,
                    Attendance.status == "present",
                )
            )
            or 0
        )

    def count_unread_notifications(self) -> int:
        """Считает уведомления за последние 7 дней как «новые».

        Returns:
            Количество свежих уведомлений.
        """
        start = date.today() - timedelta(days=7)
        return (
            self.session.scalar(
                select(func.count(Notification.notification_id)).where(
                    Notification.created_at >= start
                )
            )
            or 0
        )

    def get_upcoming_lessons(self) -> list[tuple[str, str, str]]:
        """Возвращает занятия по дням недели для дашборда.

        Returns:
            Список кортежей (день недели, время, название группы),
            отсортированный по дням и времени.
        """
        lessons = []
        for item in self.session.scalars(select(Schedule)):
            group = self.session.get(Group, item.group_id)
            name = group.name if group else "—"
            lessons.append((item.day_of_week, str(item.start_time), name))
        lessons.sort(key=lambda row: (self.DAY_ORDER.index(row[0]), row[1]))
        return lessons

    def get_attention_items(self) -> list[tuple[str, str]]:
        """Собирает предупреждения: мало занятий и задолженности.

        Returns:
            Список кортежей (тип, текст); тип — «warn» или «danger».
        """
        items: list[tuple[str, str]] = []
        subs = list(
            self.session.scalars(
                select(Subscription).where(Subscription.status == "active")
            )
        )
        for sub in subs:
            if sub.remaining_lessons <= 2:
                name = sub.student.full_name if sub.student else "—"
                items.append(
                    (
                        "warn",
                        f"Абонемент {name} — осталось {sub.remaining_lessons} зан.",
                    )
                )

        paid: dict[int, float] = dict(
            self.session.execute(
                select(
                    Payment.student_id,
                    func.coalesce(func.sum(Payment.amount), 0.0),
                ).group_by(Payment.student_id)
            ).all()
        )

        debts: dict[int, float] = {}
        for sub in subs:
            price = sub.subscription_type.price if sub.subscription_type else 0
            debts[sub.student_id] = debts.get(sub.student_id, 0) + price

        for student_id, total in debts.items():
            owed = total - paid.get(student_id, 0)
            if owed > 0:
                student = self.session.get(Student, student_id)
                if student:
                    items.append(
                        ("danger", f"{student.full_name} — долг {owed:.0f} руб.")
                    )
        return items

    def build_report(self, kind: str, start: date, end: date):
        """Формирует отчёт выбранного типа за период.

        Args:
            kind: название типа отчёта.
            start: начало периода.
            end: конец периода.

        Returns:
            Кортеж (заголовки, строки).
        """
        labels = AttendanceService(self.session).STATUS_LABELS
        if kind.startswith("Посещаемость"):
            headers = ("Дата", "Группа", "Ученик", "Статус", "Списано")
            rows = []
            for record in self.session.scalars(
                select(Attendance).where(
                    Attendance.lesson_date >= start,
                    Attendance.lesson_date <= end,
                )
            ):
                student = self.session.get(Student, record.student_id)
                if student is None:
                    continue
                group_name = "—"
                for link in self.session.scalars(
                    select(GroupStudent).where(
                        GroupStudent.student_id == student.student_id
                    )
                ):
                    group = self.session.get(Group, link.group_id)
                    if group is not None:
                        group_name = group.name
                        break
                rows.append(
                    (
                        str(record.lesson_date),
                        group_name,
                        student.full_name,
                        labels.get(record.status, record.status),
                        "-1" if record.status == "present" else "—",
                    )
                )
            rows.sort(key=lambda r: r[0])
            return headers, rows

        headers = ("Дата", "Ученик", "Абонемент", "Сумма", "Способ")
        rows = []
        for (
            _,
            date_text,
            student,
            sub_name,
            amount,
            method,
        ) in self.payments.get_table_rows():
            try:
                payment_date = datetime.strptime(date_text, "%Y-%m-%d").date()
            except ValueError:
                continue
            if start <= payment_date <= end:
                rows.append(
                    (date_text, student, sub_name, f"{amount:.0f} руб.", method)
                )
        return headers, rows

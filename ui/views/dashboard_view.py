"""Экран «Дашборд»: сводка и ближайшие занятия с датами."""

import tkinter as tk
from datetime import date

from sqlalchemy import func, select

from database.models import Group, Payment, Schedule, Student, Subscription
from ui.theme import make_header


class DashboardView:
    """Сводка по школе и расписание ближайших занятий."""

    def __init__(self, parent, session, user=None):
        self.session = session
        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)
        make_header(self.frame)

        stats = tk.Frame(self.frame, bg="#f5f6fa")
        stats.pack(fill=tk.X, padx=20, pady=(14, 0))
        month_start = date.today().replace(day=1)
        income = self.session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.payment_date >= month_start)
        )
        cards = (
            ("Учеников", self.session.scalar(
                select(func.count(Student.student_id))) or 0),
            ("Групп", self.session.scalar(
                select(func.count(Group.group_id))) or 0),
            ("Активных абонементов", self.session.scalar(
                select(func.count(Subscription.subscription_id)).where(
                    Subscription.status == "active")) or 0),
            (f"Оплаты с {month_start.strftime('%d.%m.%Y')}", f"{income:.0f} руб."),
        )
        for title, value in cards:
            card = tk.Frame(stats, bg="white", padx=18, pady=14)
            card.pack(side=tk.LEFT, padx=(0, 12), fill=tk.X, expand=True)
            tk.Label(card, text=value, bg="white", fg="#1a1f33",
                     font=("Segoe UI", 18, "bold")).pack(anchor="w")
            tk.Label(card, text=title, bg="white", fg="#6b7590",
                     font=("Segoe UI", 9)).pack(anchor="w")

        list_card = tk.Frame(self.frame, bg="white", padx=20, pady=16)
        list_card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(14, 16))
        tk.Label(list_card, text="Ближайшие занятия", bg="white", fg="#1a1f33",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))

        self.table = tk.Text(list_card, bg="white", relief=tk.FLAT,
                             font=("Courier New", 10), height=12)
        self.table.pack(fill=tk.BOTH, expand=True)

        upcoming = list(self.session.scalars(
            select(Schedule)
            .where(Schedule.lesson_date >= date.today())
            .order_by(Schedule.lesson_date, Schedule.start_time)
            .limit(15)
        ))
        lines = ["Дата         Время   Группа                Преподаватель",
                 "-" * 70]
        for lesson in upcoming:
            group = lesson.group
            teacher = (group.teacher.full_name
                       if group is not None and group.teacher is not None else "—")
            lines.append(
                f"{lesson.lesson_date.strftime('%d.%m.%Y')}   "
                f"{lesson.start_time}–{lesson.end_time or '?:??'}  "
                f"{(group.name if group else '—'):<22}{teacher}"
            )
        if len(lines) == 2:
            lines.append("Занятий не запланировано")
        self.table.insert("1.0", "\n".join(lines))
        self.table.config(state=tk.DISABLED)

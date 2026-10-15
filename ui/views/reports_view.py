"""Экран «Отчёты»: выгрузка в Excel."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from sqlalchemy import select

from database.models import (
    Group, Payment, Student, Subscription,
)
from services.attendance_service import AttendanceService
from services.export_service import export_excel
from ui.theme import make_header

REPORTS = ("Ученики", "Группы", "Посещаемость", "Абонементы", "Платежи")


class ReportsView:
    """Выбор отчёта и экспорт в файл Excel."""

    def __init__(self, parent, session, user=None):
        """Инициализирует экран.

        Args:
            parent: родительский виджет.
            session: сессия SQLAlchemy.
            user: вошедший пользователь (у ученика экспорт скрыт).
        """
        self.session = session
        self.is_student = user is not None and getattr(user, "role", "") == "student"

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)
        make_header(self.frame)

        card = tk.Frame(self.frame, bg="white", padx=20, pady=16)
        card.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        tk.Label(card, text="Отчёт", bg="white", fg="#5a6478").pack(anchor="w")
        self.report_combo = ttk.Combobox(card, state="readonly", width=30,
                                         values=list(REPORTS))
        self.report_combo.current(0)
        self.report_combo.pack(anchor="w", pady=(2, 12), ipady=3)

        ttk.Button(card, text="⬇ Скачать Excel (.xlsx)",
                   style="Secondary.TButton",
                   command=self._export).pack(anchor="w")

        self.preview = tk.Text(card, bg="#f8f9fb", relief=tk.FLAT, height=14)
        self.preview.pack(fill=tk.BOTH, expand=True, pady=(14, 0))
        self.report_combo.bind("<<ComboboxSelected>>", lambda e: self._preview())
        self._preview()

    def _data(self):
        """Формирует (заголовок, шапку, строки) выбранного отчёта.

        Returns:
            Кортеж (название отчёта, заголовки колонок, строки данных).
        """
        kind = self.report_combo.get()
        if kind == "Ученики":
            rows = []
            for student in self.session.scalars(select(Student)):
                groups = ", ".join(g.name for g in student.groups) or "—"
                rows.append((student.student_id, student.full_name,
                             student.phone, student.direction,
                             student.parent_name, groups))
            return kind, ("№", "ФИО", "Телефон", "Направление",
                          "Родитель", "Группы"), rows
        if kind == "Группы":
            rows = [
                (g.group_id, g.name, g.direction, g.level, g.age_range,
                 g.teacher.full_name if g.teacher is not None else "—")
                for g in self.session.scalars(select(Group))
            ]
            return kind, ("№", "Название", "Направление", "Уровень",
                          "Возраст", "Преподаватель"), rows
        if kind == "Посещаемость":
            service = AttendanceService(self.session)
            return kind, ("№", "Дата", "Группа", "Ученик", "Статус",
                          "Абонемент", "Списано"), service.get_table_rows()
        if kind == "Абонементы":
            rows = []
            for sub in self.session.scalars(select(Subscription)):
                rows.append((
                    sub.subscription_id,
                    sub.student.full_name if sub.student is not None else "—",
                    sub.subscription_type.name if sub.subscription_type else "—",
                    sub.total_lessons, sub.remaining_lessons,
                    sub.status,
                    sub.start_date.strftime("%d.%m.%Y")
                    if sub.start_date else "—",
                ))
            return kind, ("№", "Ученик", "Тип", "Занятий", "Осталось",
                          "Статус", "Начало"), rows
        rows = []
        for payment in self.session.scalars(
            select(Payment).order_by(Payment.payment_date.desc())
        ):
            student = self.session.get(Student, payment.student_id)
            rows.append((
                payment.payment_id,
                payment.payment_date.strftime("%d.%m.%Y"),
                student.full_name if student is not None else "—",
                f"{payment.amount:.2f}", payment.method,
            ))
        return "Платежи", ("№", "Дата", "Ученик", "Сумма", "Способ"), rows

    def _preview(self):
        """Обновляет текстовый предпросмотр выбранного отчёта."""
        title, headers, rows = self._data()
        self.preview.config(state=tk.NORMAL)
        self.preview.delete("1.0", tk.END)
        lines = [f"{title}: {len(rows)} записей", "  |  ".join(headers)]
        for row in rows[:20]:
            lines.append("  |  ".join(str(cell) for cell in row))
        if len(rows) > 20:
            lines.append(f"... и ещё {len(rows) - 20} записей")
        self.preview.insert("1.0", "\n".join(lines))
        self.preview.config(state=tk.DISABLED)

    def _export(self):
        """Сохраняет выбранный отчёт в файл Excel.

        Excel выбран вместо PDF: кириллица пишется без внешних шрифтов,
        файл открывается на любом компьютере.
        """
        if self.is_student:
            messagebox.showinfo("Отчёты", "Экспорт доступен сотрудникам",
                                parent=self.frame)
            return
        title, headers, rows = self._data()
        if not rows:
            messagebox.showinfo("Отчёты", "Нет данных для отчёта",
                                parent=self.frame)
            return
        path = filedialog.asksaveasfilename(
            parent=self.frame,
            defaultextension=".xlsx",
            initialfile=f"отчет_{title.lower()}.xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not path:
            return
        try:
            export_excel(path, title, headers, rows)
        except Exception as error:
            messagebox.showerror("Отчёты", str(error), parent=self.frame)
            return
        messagebox.showinfo("Отчёты", f"Файл сохранён:\n{path}",
                            parent=self.frame)

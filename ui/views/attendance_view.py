"""Экран «Посещаемость»: таблица отметок и отметка занятия."""

import tkinter as tk
from tkinter import messagebox, ttk

from sqlalchemy import select

from tkcalendar import DateEntry

from database.models import Group
from services.attendance_service import AttendanceService
from services.group_service import GroupService
from ui.dialogs.choice_dialog import ChoiceDialog
from ui.theme import make_header

STATUS_OPTIONS = (
    ("present", "Присутствовал"),
    ("absent", "Отсутствовал"),
    ("sick", "Болел"),
)


class AttendanceView:
    """Таблица посещаемости и окно отметки группы."""

    def __init__(self, parent: tk.Widget, session, user=None) -> None:
        """Инициализирует экран.

        Args:
            parent: родительский виджет.
            session: сессия SQLAlchemy.
            user: вошедший пользователь (у ученика кнопки скрыты).
        """
        self.session = session
        self.service = AttendanceService(session)
        self.group_service = GroupService(session)
        self.is_student = user is not None and getattr(user, "role", "") == "student"

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)
        if not self.is_student:
            make_header(
                self.frame, "Посещаемость", "✅ Отметить посещаемость", self._on_mark
            )
        else:
            make_header(self.frame, "Посещаемость")

        card = tk.Frame(self.frame, bg="white", padx=20, pady=16)
        card.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        self.table = ttk.Treeview(
            card,
            show="headings",
            selectmode="browse",
            columns=("id", "date", "group", "student", "status", "sub", "spent"),
        )
        for column, text, width in (
            ("id", "№", 50),
            ("date", "Дата", 110),
            ("group", "Группа", 140),
            ("student", "Ученик", 190),
            ("status", "Статус", 130),
            ("sub", "Абонемент", 120),
            ("spent", "Списано", 80),
        ):
            self.table.heading(column, text=text)
            self.table.column(column, width=width, anchor=tk.W)
        self.table.tag_configure("present", foreground="#047857")
        self.table.tag_configure("absent", foreground="#b91c1c")
        self.table.tag_configure("sick", foreground="#b45309")
        scrollbar = ttk.Scrollbar(card, orient=tk.VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if not self.is_student:
            self.table.bind("<Double-1>", self._on_edit_status)

        self.refresh()

    def refresh(self) -> None:
        """Перезагружает таблицу отметок."""
        self.table.delete(*self.table.get_children())
        tag_map = {
            "Присутствовал": "present",
            "Отсутствовал": "absent",
            "Болел": "sick",
        }
        for row in self.service.get_table_rows():
            record_id, date_text, group, student, status, sub, spent = row
            self.table.insert(
                "",
                tk.END,
                tags=(tag_map.get(status, "absent"),),
                values=(record_id, date_text, group, student, status, sub, spent),
            )

    def _on_mark(self) -> None:
        """Открывает окно отметки: группа, дата, статусы учеников."""
        options = [
            (group.group_id, group.name)
            for group in self.session.scalars(select(Group))
        ]
        if not options:
            messagebox.showinfo(
                "Посещаемость", "Сначала создайте группу", parent=self.frame
            )
            return
        chooser = ChoiceDialog(
            self.frame, "Отметка посещаемости", options, "Выберите группу:"
        )
        self.frame.wait_window(chooser.top)
        if chooser.result is None:
            return
        group = self.session.get(Group, chooser.result)
        students = self.group_service.get_students(group) if group is not None else []
        if group is None or not students:
            messagebox.showinfo(
                "Посещаемость", "В этой группе нет учеников", parent=self.frame
            )
            return

        top = tk.Toplevel(self.frame)
        top.title(f"Отметка: {group.name}")
        top.transient(self.frame.winfo_toplevel())
        top.grab_set()

        head = tk.Frame(top, bg="white", padx=20, pady=12)
        head.pack(fill=tk.X)
        tk.Label(head, text="Дата занятия", bg="white", fg="#5a6478").pack(
            side=tk.LEFT
        )
        date_entry = DateEntry(head, date_format="dd.mm.yyyy", width=12)
        date_entry.pack(side=tk.LEFT, padx=8)

        body = tk.Frame(top, bg="white", padx=20, pady=6)
        body.pack(fill=tk.BOTH, expand=True)
        combos: dict[int, ttk.Combobox] = {}
        for student in students:
            row_frame = tk.Frame(body, bg="white")
            row_frame.pack(fill=tk.X, pady=4)
            tk.Label(
                row_frame,
                text=student.full_name,
                bg="white",
                fg="#1a1f33",
                font=("Segoe UI", 10),
            ).pack(side=tk.LEFT)
            combo = ttk.Combobox(
                row_frame,
                state="readonly",
                width=16,
                values=[label for _, label in STATUS_OPTIONS],
            )
            combo.current(0)
            combo.pack(side=tk.RIGHT)
            combos[student.student_id] = combo

        def on_save() -> None:
            """Сохраняет отметки и списывает занятия присутствовавшим."""
            lesson_date = date_entry.get_date()
            statuses = {
                student_id: STATUS_OPTIONS[combo.current()][0]
                for student_id, combo in combos.items()
            }
            try:
                self.service.mark_lesson(group, lesson_date, statuses)
            except Exception as error:
                messagebox.showerror("Посещаемость", str(error), parent=top)
                return
            top.destroy()
            self.refresh()
            messagebox.showinfo("Посещаемость", "Отметки сохранены", parent=self.frame)

        tk.Button(
            head,
            text="Сохранить",
            command=on_save,
            cursor="hand2",
            bg="#1a1f33",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            bd=0,
            activebackground="#2e3554",
            activeforeground="white",
        ).pack(side=tk.RIGHT)

        top.wait_visibility()
        top.focus_set()

    def _on_edit_status(self, event) -> None:
        """Меняет статус отметки по двойному клику по строке."""
        item = self.table.identify_row(event.y)
        if not item:
            return
        attendance_id = int(self.table.item(item, "values")[0])
        current = self.table.item(item, "values")[4]
        codes = {label: code for code, label in STATUS_OPTIONS}
        edit = tk.Toplevel(self.frame)
        edit.title("Изменение статуса")
        edit.configure(bg="white")
        edit.transient(self.frame.winfo_toplevel())
        edit.grab_set()
        tk.Label(edit, text="Статус посещения", bg="white", fg="#5a6478").pack(
            padx=20, pady=(14, 2)
        )
        combo = ttk.Combobox(
            edit,
            state="readonly",
            width=20,
            values=[label for _, label in STATUS_OPTIONS],
        )
        combo.set(current)
        combo.pack(padx=20, pady=(2, 10), ipady=3)

        def on_save() -> None:
            """Сохраняет новый статус с пересчётом абонемента."""
            try:
                self.service.set_status(attendance_id, codes[combo.get()])
            except Exception as error:
                messagebox.showerror("Посещаемость", str(error), parent=edit)
                return
            edit.destroy()
            self.refresh()

        tk.Button(
            edit,
            text="Сохранить",
            command=on_save,
            cursor="hand2",
            bg="#1a1f33",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            bd=0,
            activebackground="#2e3554",
            activeforeground="white",
        ).pack(padx=20, pady=(0, 14), ipady=5)

"""Экран «Расписание»: занятия с календарём и обязательной датой."""

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import date

from tkcalendar import DateEntry

from database.models import Group
from services.schedule_service import ScheduleService
from ui.theme import make_header


class LessonDialog(tk.Toplevel):
    """Диалог создания и редактирования занятия с календарём."""

    def __init__(self, master, title, groups, initial=None, on_save=None) -> None:
        """Создаёт диалог.

        Args:
            master: родительский виджет.
            title: заголовок окна.
            groups: список кортежей (group_id, название).
            initial: значения по умолчанию.
            on_save: колбэк, принимающий словарь значений.
        """
        super().__init__(master)
        initial = initial or {}
        self.title(title)
        self.configure(bg="white")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        self.result = None
        self.on_save = on_save

        form = tk.Frame(self, bg="white", padx=24, pady=16)
        form.pack()

        tk.Label(form, text="Дата занятия (обязательно)", bg="white",
                 fg="#5a6478").pack(anchor="w")
        self.date_entry = DateEntry(
            form, date_format="dd.mm.yyyy", width=14, bg="#f5f6fa"
        )
        if initial.get("lesson_date"):
            self.date_entry.set_date(initial["lesson_date"])
        self.date_entry.pack(fill=tk.X, pady=(2, 10), ipady=4)

        tk.Label(form, text="Группа", bg="white", fg="#5a6478").pack(anchor="w")
        self.group_combo = ttk.Combobox(
            form, state="readonly", width=26, values=[name for _, name in groups]
        )
        if initial.get("group_id") is not None:
            for index, (gid, _) in enumerate(groups):
                if gid == initial["group_id"]:
                    self.group_combo.current(index)
                    break
        elif groups:
            self.group_combo.current(0)
        self.group_combo.pack(fill=tk.X, pady=(2, 10), ipady=3)

        self.entries: dict[str, tk.Entry] = {}
        for key, label, value in (
            ("start", "Начало (ЧЧ:ММ)", initial.get("start", "")),
            ("end", "Окончание (ЧЧ:ММ)", initial.get("end", "")),
            ("room", "Кабинет", initial.get("room", "")),
        ):
            tk.Label(form, text=label, bg="white", fg="#5a6478").pack(anchor="w")
            entry = tk.Entry(form, width=28, relief=tk.FLAT, bg="#f5f6fa")
            entry.insert(0, value)
            entry.pack(fill=tk.X, pady=(2, 10), ipady=4)
            self.entries[key] = entry

        tk.Button(
            form,
            text="Сохранить",
            command=self._save,
            cursor="hand2",
            bg="#1a1f33",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            bd=0,
            activebackground="#2e3554",
            activeforeground="white",
        ).pack(fill=tk.X, ipady=6)

    def _save(self) -> None:
        """Собирает значения и вызывает колбэк сохранения."""
        index = self.group_combo.current()
        data = {
            "lesson_date": self.date_entry.get_date(),
            "group_id": self.master_group_id[index] if False else None,
        }
        # group_id берём из переданного списка групп
        data["group_id"] = self._groups[index][0] if hasattr(self, "_groups") else None
        for key, entry in self.entries.items():
            data[key] = entry.get().strip()
        try:
            self.on_save(data)
            self.result = data
            self.destroy()
        except Exception as error:
            messagebox.showerror("Расписание", str(error), parent=self)


class ScheduleView:
    """Список занятий с добавлением, редактированием и удалением."""

    def __init__(self, parent: tk.Widget, session, user=None) -> None:
        """Инициализирует экран.

        Args:
            parent: родительский виджет.
            session: сессия SQLAlchemy.
            user: вошедший пользователь (у ученика кнопки скрыты).
        """
        self.session = session
        self.service = ScheduleService(session)
        self.is_student = user is not None and getattr(user, "role", "") == "student"

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)
        if not self.is_student:
            make_header(self.frame, "Расписание", "+ Добавить занятие", self._on_add)
        else:
            make_header(self.frame, "Расписание")

        card = tk.Frame(self.frame, bg="white", padx=20, pady=16)
        card.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        self.table = ttk.Treeview(
            card,
            show="headings",
            selectmode="browse",
            columns=("id", "date", "time", "group", "teacher", "room"),
        )
        for column, text, width in (
            ("id", "№", 50),
            ("date", "Дата", 110),
            ("time", "Время", 110),
            ("group", "Группа", 170),
            ("teacher", "Преподаватель", 200),
            ("room", "Кабинет", 90),
        ):
            self.table.heading(column, text=text)
            self.table.column(column, width=width, anchor=tk.W)
        scrollbar = ttk.Scrollbar(card, orient=tk.VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if not self.is_student:
            buttons = tk.Frame(card, bg="white")
            buttons.pack(fill=tk.X, pady=(10, 0))
            ttk.Button(
                buttons,
                text="✏ Редактировать",
                style="Secondary.TButton",
                command=self._on_edit,
            ).pack(side=tk.LEFT)
            ttk.Button(
                buttons,
                text="🗑 Удалить",
                style="Secondary.TButton",
                command=self._on_delete,
            ).pack(side=tk.LEFT, padx=8)

        self.refresh()

    def refresh(self) -> None:
        """Перезагружает таблицу расписания."""
        self.table.delete(*self.table.get_children())
        for row in self.service.get_table_rows():
            self.table.insert("", tk.END, values=row)

    def _selected_lesson(self):
        """Возвращает выбранное занятие или None с подсказкой."""
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo(
                "Расписание", "Выберите занятие в таблице", parent=self.frame
            )
            return None
        lesson_id = int(self.table.item(selection[0], "values")[0])
        for lesson in self.service.get_all():
            if getattr(lesson, "schedule_id", None) == lesson_id:
                return lesson
        return None

    def _group_options(self) -> list[tuple]:
        """Собирает варианты групп.

        Returns:
            Список кортежей (group_id, название).
        """
        from sqlalchemy import select
        return [
            (group.group_id, group.name)
            for group in self.session.scalars(select(Group))
        ]

    def _save_from_dialog(self, data: dict, lesson=None) -> None:
        """Сохраняет занятие из диалога.

        Args:
            data: значения полей диалога.
            lesson: редактируемое занятие или None для нового.
        """
        try:
            if lesson is not None:
                self.service.delete(lesson)
            self.service.create_lesson(
                data["group_id"],
                data["lesson_date"],
                data["start"],
                end=data["end"],
                room=data["room"],
            )
        except ValueError as error:
            messagebox.showwarning(
                "Проверка данных", str(error), parent=self.frame
            )
        except Exception as error:
            messagebox.showerror("Расписание", str(error), parent=self.frame)
        self.refresh()

    def _on_add(self) -> None:
        """Открывает форму добавления занятия."""
        options = self._group_options()
        if not options:
            messagebox.showinfo(
                "Расписание", "Сначала создайте группу", parent=self.frame
            )
            return
        dialog = LessonDialog(self.frame, "Новое занятие", options,
                              on_save=lambda data: self._save_from_dialog(data))
        dialog._groups = options
        self.frame.wait_window(dialog)

    def _on_edit(self) -> None:
        """Редактирует выбранное занятие."""
        lesson = self._selected_lesson()
        if lesson is None:
            return
        options = self._group_options()
        initial = {
            "lesson_date": lesson.lesson_date or date.today(),
            "group_id": lesson.group_id,
            "start": str(lesson.start_time),
            "end": str(getattr(lesson, "end_time", "") or ""),
            "room": getattr(lesson, "room", "") or "",
        }
        dialog = LessonDialog(
            self.frame, "Редактирование занятия", options, initial,
            on_save=lambda data: self._save_from_dialog(data, lesson),
        )
        dialog._groups = options
        self.frame.wait_window(dialog)

    def _on_delete(self) -> None:
        """Удаляет выбранное занятие с подтверждением."""
        lesson = self._selected_lesson()
        if lesson is None:
            return
        if not messagebox.askyesno(
            "Удаление", "Удалить это занятие из расписания?", parent=self.frame
        ):
            return
        self.service.delete(lesson)
        self.refresh()

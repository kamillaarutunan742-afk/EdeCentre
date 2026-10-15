"""Экран «Преподаватели»: таблица и CRUD."""

import tkinter as tk
from tkinter import messagebox, ttk

from services.teacher_service import TeacherService
from ui.dialogs.form_dialog import FormDialog


class TeachersView:
    """Экран управления преподавателями."""

    COLUMNS = ("id", "full_name", "phone", "subjects")
    HEADERS = ("ID", "ФИО", "Телефон", "Языки")

    def __init__(self, parent: tk.Widget, session) -> None:
        """Инициализирует экран.

        Args:
            parent: родительский виджет.
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.service = TeacherService(session)

        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)

        bar = ttk.Frame(self.frame, padding=(0, 0, 0, 10))
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="Обновить", command=self.refresh).pack(side=tk.LEFT)

        wrapper = ttk.Frame(self.frame)
        wrapper.pack(fill=tk.BOTH, expand=True)
        self.table = ttk.Treeview(
            wrapper, columns=self.COLUMNS, show="headings", selectmode="browse"
        )
        for column, header in zip(self.COLUMNS, self.HEADERS):
            self.table.heading(column, text=header)
            self.table.column(column, width=50 if column == "id" else 180)
        scrollbar = ttk.Scrollbar(wrapper, orient=tk.VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        buttons = ttk.Frame(self.frame, padding=(0, 10, 0, 0))
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Добавить", command=self._on_add).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(buttons, text="Редактировать", command=self._on_edit).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(buttons, text="Удалить", command=self._on_delete).pack(side=tk.LEFT)
        self.refresh()

    @staticmethod
    def _form_fields() -> list:
        """Возвращает спецификацию полей формы преподавателя.

        Returns:
            Список описаний полей для FormDialog.
        """
        return [
            ("full_name", "ФИО", "entry", None),
            ("phone", "Телефон", "entry", None),
            ("subjects", "Преподаваемые языки", "entry", None),
        ]

    def refresh(self) -> None:
        """Перезагружает таблицу преподавателей."""
        self.table.delete(*self.table.get_children())
        for teacher in self.service.get_all_teachers():
            self.table.insert(
                "",
                tk.END,
                iid=str(teacher.teacher_id),
                values=(
                    teacher.teacher_id,
                    teacher.full_name,
                    teacher.phone or "",
                    teacher.subjects or "",
                ),
            )

    def _get_selected_teacher(self):
        """Возвращает выбранного преподавателя или None с сообщением."""
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo(
                "Преподаватели",
                "Выберите преподавателя в таблице",
                parent=self.frame,
            )
            return None
        return self.service.get_teacher(int(selected[0]))

    def _on_add(self) -> None:
        """Открывает форму добавления и сохраняет преподавателя."""
        dialog = FormDialog(self.frame, "Добавить преподавателя", self._form_fields())
        if dialog.result is None:
            return
        try:
            self.service.create_teacher(**dialog.result)
        except ValueError as error:
            self.session.rollback()
            messagebox.showerror("Преподаватели", str(error), parent=self.frame)
            return
        self.refresh()

    def _on_edit(self) -> None:
        """Открывает форму редактирования выбранного преподавателя."""
        teacher = self._get_selected_teacher()
        if teacher is None:
            return
        dialog = FormDialog(
            self.frame,
            "Редактировать преподавателя",
            self._form_fields(),
            initial={
                "full_name": teacher.full_name,
                "phone": teacher.phone or "",
                "subjects": teacher.subjects or "",
            },
        )
        if dialog.result is None:
            return
        try:
            self.service.update_teacher(teacher, **dialog.result)
        except ValueError as error:
            self.session.rollback()
            messagebox.showerror("Преподаватели", str(error), parent=self.frame)
            return
        self.refresh()

    def _on_delete(self) -> None:
        """Удаляет преподавателя после подтверждения."""
        teacher = self._get_selected_teacher()
        if teacher is None:
            return
        if not messagebox.askyesno(
            "Удаление",
            f"Удалить преподавателя «{teacher.full_name}»?",
            parent=self.frame,
        ):
            return
        try:
            self.service.delete_teacher(teacher)
        except Exception:
            self.session.rollback()
            messagebox.showerror(
                "Преподаватели",
                "Не удалось удалить преподавателя",
                parent=self.frame,
            )
            return
        self.refresh()

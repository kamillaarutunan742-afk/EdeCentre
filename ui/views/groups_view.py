"""Экран «Группы»: список, добавление, полное редактирование и удаление."""

import tkinter as tk
from tkinter import messagebox, ttk

from sqlalchemy import select

from database.models import Group, Teacher
from ui.theme import make_header


class GroupDialog(tk.Toplevel):
    """Диалог группы со всеми полями."""

    def __init__(self, master, title, teachers, initial=None, on_save=None):
        super().__init__(master)
        initial = initial or {}
        self.title(title)
        self.configure(bg="white")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        self.on_save = on_save
        self.teachers = teachers

        form = tk.Frame(self, bg="white", padx=24, pady=16)
        form.pack()
        self.entries = {}
        for key, label, value in (
            ("name", "Название *", initial.get("name", "")),
            ("direction", "Направление", initial.get("direction", "")),
            ("level", "Уровень", initial.get("level", "")),
            ("age_range", "Возраст", initial.get("age_range", "")),
        ):
            tk.Label(form, text=label, bg="white", fg="#5a6478").pack(anchor="w")
            entry = tk.Entry(form, width=28, relief=tk.FLAT, bg="#f5f6fa")
            entry.insert(0, value)
            entry.pack(fill=tk.X, pady=(2, 10), ipady=4)
            self.entries[key] = entry

        tk.Label(form, text="Преподаватель", bg="white", fg="#5a6478").pack(anchor="w")
        labels = ["— без преподавателя —"] + [t.full_name for t in teachers]
        self.teacher_combo = ttk.Combobox(form, state="readonly", width=26,
                                          values=labels)
        current = initial.get("teacher_id")
        if current is not None:
            for index, teacher in enumerate(teachers):
                if teacher.teacher_id == current:
                    self.teacher_combo.current(index + 1)
                    break
        else:
            self.teacher_combo.current(0)
        self.teacher_combo.pack(fill=tk.X, pady=(2, 12), ipady=3)

        tk.Button(
            form, text="Сохранить", command=self._save, cursor="hand2",
            bg="#1a1f33", fg="white", font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, bd=0,
            activebackground="#2e3554", activeforeground="white",
        ).pack(fill=tk.X, ipady=6)

    def _save(self):
        index = self.teacher_combo.current()
        data = {key: entry.get().strip() for key, entry in self.entries.items()}
        data["teacher_id"] = self.teachers[index - 1].teacher_id if index > 0 else None
        try:
            self.on_save(data)
            self.destroy()
        except Exception as error:
            messagebox.showerror("Группы", str(error), parent=self)


class GroupsView:
    """Таблица групп с полным редактированием и удалением."""

    def __init__(self, parent, session, user=None):
        self.session = session
        self.is_student = user is not None and getattr(user, "role", "") == "student"

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)
        if not self.is_student:
            make_header(self.frame, button_text="+ Добавить группу",
                        command=self._on_add)
        else:
            make_header(self.frame)

        card = tk.Frame(self.frame, bg="white", padx=20, pady=16)
        card.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        self.table = ttk.Treeview(
            card, show="headings", selectmode="browse",
            columns=("id", "name", "direction", "level", "age", "teacher"),
        )
        for column, text, width in (
            ("id", "№", 45),
            ("name", "Название", 170),
            ("direction", "Направление", 130),
            ("level", "Уровень", 100),
            ("age", "Возраст", 100),
            ("teacher", "Преподаватель", 200),
        ):
            self.table.heading(column, text=text)
            self.table.column(column, width=width, anchor=tk.W)
        scrollbar = ttk.Scrollbar(card, orient=tk.VERTICAL,
                                  command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if not self.is_student:
            buttons = tk.Frame(card, bg="white")
            buttons.pack(fill=tk.X, pady=(10, 0))
            ttk.Button(buttons, text="✏ Редактировать", style="Secondary.TButton",
                       command=self._on_edit).pack(side=tk.LEFT)
            ttk.Button(buttons, text="🗑 Удалить", style="Secondary.TButton",
                       command=self._on_delete).pack(side=tk.LEFT, padx=8)

        self.refresh()

    def refresh(self):
        self.table.delete(*self.table.get_children())
        for group in self.session.scalars(select(Group)):
            teacher = group.teacher.full_name if group.teacher is not None else "—"
            self.table.insert("", tk.END, iid=str(group.group_id), values=(
                group.group_id, group.name, group.direction, group.level,
                group.age_range, teacher,
            ))

    def _selected(self):
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo("Группы", "Выберите группу в таблице",
                                parent=self.frame)
            return None
        return int(selection[0])

    def _teachers(self):
        return list(self.session.scalars(select(Teacher)))

    def _save_group(self, data, group=None):
        if not data["name"]:
            raise ValueError("Название обязательно")
        try:
            if group is None:
                group = Group(name=data["name"])
                self.session.add(group)
            group.name = data["name"]
            group.direction = data["direction"]
            group.level = data["level"]
            group.age_range = data["age_range"]
            group.teacher_id = data["teacher_id"]
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise ValueError("Группа с таким названием уже есть")
        self.refresh()

    def _on_add(self):
        dialog = GroupDialog(self.frame, "Новая группа", self._teachers(),
                             on_save=lambda d: self._save_group(d))
        self.frame.wait_window(dialog)

    def _on_edit(self):
        group_id = self._selected()
        if group_id is None:
            return
        group = self.session.get(Group, group_id)
        dialog = GroupDialog(
            self.frame, "Редактирование группы", self._teachers(),
            initial={
                "name": group.name, "direction": group.direction,
                "level": group.level, "age_range": group.age_range,
                "teacher_id": group.teacher_id,
            },
            on_save=lambda d: self._save_group(d, group),
        )
        self.frame.wait_window(dialog)

    def _on_delete(self):
        group_id = self._selected()
        if group_id is None:
            return
        if not messagebox.askyesno(
            "Удаление",
            "Удалить группу вместе с занятиями расписания? Ученики останутся.",
            parent=self.frame,
        ):
            return
        self.session.delete(self.session.get(Group, group_id))
        self.session.commit()
        self.refresh()

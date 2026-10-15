"""Экран «Ученики»: список, добавление, полное редактирование и удаление."""

import tkinter as tk
from tkinter import messagebox, ttk

from sqlalchemy import select

from tkcalendar import DateEntry

from database.models import (
    Attendance, Group, GroupStudent, Payment, Student, Subscription,
)
from ui.theme import make_header


class StudentDialog(tk.Toplevel):
    """Диалог создания и редактирования ученика."""

    def __init__(self, master, title, groups, initial=None, on_save=None):
        super().__init__(master)
        initial = initial or {}
        self.title(title)
        self.configure(bg="white")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)

        form = tk.Frame(self, bg="white", padx=24, pady=16)
        form.pack()

        tk.Label(form, text="ФИО *", bg="white", fg="#5a6478").pack(anchor="w")
        self.name = tk.Entry(form, width=28, relief=tk.FLAT, bg="#f5f6fa")
        self.name.insert(0, initial.get("full_name", ""))
        self.name.pack(fill=tk.X, pady=(2, 10), ipady=4)

        tk.Label(form, text="Телефон", bg="white", fg="#5a6478").pack(anchor="w")
        self.phone = tk.Entry(form, width=28, relief=tk.FLAT, bg="#f5f6fa")
        self.phone.insert(0, initial.get("phone", ""))
        self.phone.pack(fill=tk.X, pady=(2, 10), ipady=4)

        tk.Label(form, text="Направление", bg="white", fg="#5a6478").pack(anchor="w")
        self.direction = tk.Entry(form, width=28, relief=tk.FLAT, bg="#f5f6fa")
        self.direction.insert(0, initial.get("direction", ""))
        self.direction.pack(fill=tk.X, pady=(2, 10), ipady=4)

        tk.Label(form, text="Уровень", bg="white", fg="#5a6478").pack(anchor="w")
        self.level = tk.Entry(form, width=28, relief=tk.FLAT, bg="#f5f6fa")
        self.level.insert(0, initial.get("level", ""))
        self.level.pack(fill=tk.X, pady=(2, 10), ipady=4)

        tk.Label(form, text="Родитель", bg="white", fg="#5a6478").pack(anchor="w")
        self.parent_name = tk.Entry(form, width=28, relief=tk.FLAT, bg="#f5f6fa")
        self.parent_name.insert(0, initial.get("parent_name", ""))
        self.parent_name.pack(fill=tk.X, pady=(2, 10), ipady=4)

        tk.Label(form, text="Дата зачисления", bg="white", fg="#5a6478").pack(anchor="w")
        self.enroll = DateEntry(form, date_format="dd.mm.yyyy", width=14,
                               bg="#f5f6fa")
        if initial.get("enroll_date"):
            self.enroll.set_date(initial["enroll_date"])
        self.enroll.pack(fill=tk.X, pady=(2, 10), ipady=4)

        tk.Label(form, text="Группа", bg="white", fg="#5a6478").pack(anchor="w")
        labels = ["— без группы —"] + [name for _, name in groups]
        self.group_combo = ttk.Combobox(form, state="readonly", width=26,
                                        values=labels)
        current_id = initial.get("group_id")
        if current_id is not None:
            for index, (gid, _) in enumerate(groups):
                if gid == current_id:
                    self.group_combo.current(index + 1)
                    break
        else:
            self.group_combo.current(0)
        self.group_combo.pack(fill=tk.X, pady=(2, 12), ipady=3)

        self.on_save = on_save
        self.groups = groups
        tk.Button(
            form, text="Сохранить", command=self._save, cursor="hand2",
            bg="#1a1f33", fg="white", font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, bd=0,
            activebackground="#2e3554", activeforeground="white",
        ).pack(fill=tk.X, ipady=6)

    def _save(self):
        index = self.group_combo.current()
        data = {
            "full_name": self.name.get(),
            "phone": self.phone.get().strip(),
            "direction": self.direction.get().strip(),
            "level": self.level.get().strip(),
            "parent_name": self.parent_name.get().strip(),
            "enroll_date": self.enroll.get_date(),
            "group_id": self.groups[index - 1][0] if index > 0 else None,
        }
        try:
            self.on_save(data)
            self.destroy()
        except Exception as error:
            messagebox.showerror("Ученики", str(error), parent=self)


class StudentsView:
    """Таблица учеников с полным редактированием и удалением."""

    def __init__(self, parent, session, user=None):
        self.session = session
        self.is_student = user is not None and getattr(user, "role", "") == "student"

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)
        if not self.is_student:
            make_header(self.frame, button_text="+ Добавить ученика",
                        command=self._on_add)
        else:
            make_header(self.frame)

        card = tk.Frame(self.frame, bg="white", padx=20, pady=16)
        card.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        self.table = ttk.Treeview(
            card, show="headings", selectmode="browse",
            columns=("id", "fio", "phone", "direction", "level",
                     "parent", "groups"),
        )
        for column, text, width in (
            ("id", "№", 45),
            ("fio", "ФИО", 190),
            ("phone", "Телефон", 120),
            ("direction", "Направление", 120),
            ("level", "Уровень", 90),
            ("parent", "Родитель", 160),
            ("groups", "Группы", 180),
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
        for student in self.session.scalars(select(Student)):
            names = [g.name for g in student.groups]
            self.table.insert("", tk.END, iid=str(student.student_id), values=(
                student.student_id, student.full_name, student.phone,
                student.direction, student.level, student.parent_name,
                ", ".join(names),
            ))

    def _selected(self):
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo("Ученики", "Выберите ученика в таблице",
                                parent=self.frame)
            return None
        return int(selection[0])

    def _group_options(self):
        return [(g.group_id, g.name)
                for g in self.session.scalars(select(Group))]

    def _save_student(self, data, student=None):
        if not data["full_name"].strip():
            raise ValueError("ФИО обязательно")
        if student is None:
            student = Student(full_name=data["full_name"])
            self.session.add(student)
            self.session.flush()
        student.full_name = data["full_name"].strip()
        student.phone = data["phone"]
        student.direction = data["direction"]
        student.level = data["level"]
        student.parent_name = data["parent_name"]
        student.enroll_date = data["enroll_date"]
        for link in self.session.scalars(
            select(GroupStudent).where(
                GroupStudent.student_id == student.student_id)
        ):
            self.session.delete(link)
        if data["group_id"] is not None:
            self.session.add(GroupStudent(group_id=data["group_id"],
                                          student_id=student.student_id))
        self.session.commit()
        self.refresh()

    def _on_add(self):
        groups = self._group_options()
        dialog = StudentDialog(self.frame, "Новый ученик", groups,
                               on_save=lambda d: self._save_student(d))
        self.frame.wait_window(dialog)

    def _on_edit(self):
        student_id = self._selected()
        if student_id is None:
            return
        student = self.session.get(Student, student_id)
        groups = self._group_options()
        current_group = student.groups[0].group_id if student.groups else None
        dialog = StudentDialog(
            self.frame, "Редактирование ученика", groups,
            initial={
                "full_name": student.full_name, "phone": student.phone,
                "direction": student.direction, "level": student.level,
                "parent_name": student.parent_name,
                "enroll_date": student.enroll_date, "group_id": current_group,
            },
            on_save=lambda d: self._save_student(d, student),
        )
        self.frame.wait_window(dialog)

    def _on_delete(self):
        student_id = self._selected()
        if student_id is None:
            return
        if not messagebox.askyesno(
            "Удаление",
            "Удалить ученика вместе с его абонементами, отметками "
            "посещаемости и платежами?",
            parent=self.frame,
        ):
            return
        for model in (GroupStudent, Attendance, Subscription, Payment):
            for row in self.session.scalars(
                select(model).where(model.student_id == student_id)
            ):
                self.session.delete(row)
        self.session.delete(self.session.get(Student, student_id))
        self.session.commit()
        self.refresh()

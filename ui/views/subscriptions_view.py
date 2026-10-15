"""Экран «Абонементы»: продажа с автооплатой, полное редактирование, удаление."""

import tkinter as tk
from tkinter import messagebox, ttk

from sqlalchemy import select

from tkcalendar import DateEntry

from database.models import (
    Notification, Payment, Student, Subscription, SubscriptionType,
)
from ui.theme import make_header

SUB_STATUSES = ("active", "exhausted", "cancelled")
SUB_LABELS = {
    "active": "Активен",
    "exhausted": "Исчерпан",
    "cancelled": "Отменён",
}


class SubscriptionDialog(tk.Toplevel):
    """Диалог продажи/редактирования абонемента."""

    def __init__(self, master, title, students, types_, initial=None,
                 on_save=None, with_student=True):
        super().__init__(master)
        initial = initial or {}
        self.title(title)
        self.configure(bg="white")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        self.on_save = on_save
        self.students = students
        self.types = types_

        form = tk.Frame(self, bg="white", padx=24, pady=16)
        form.pack()

        self.student_combo = None
        if with_student:
            tk.Label(form, text="Ученик", bg="white", fg="#5a6478").pack(anchor="w")
            self.student_combo = ttk.Combobox(
                form, state="readonly", width=26,
                values=[s.full_name for s in students],
            )
            if initial.get("student_id") is not None:
                for index, student in enumerate(students):
                    if student.student_id == initial["student_id"]:
                        self.student_combo.current(index)
                        break
            elif students:
                self.student_combo.current(0)
            self.student_combo.pack(fill=tk.X, pady=(2, 10), ipady=3)

        tk.Label(form, text="Тип абонемента", bg="white", fg="#5a6478").pack(anchor="w")
        self.type_combo = ttk.Combobox(
            form, state="readonly", width=26,
            values=[f"{t.name} ({t.lessons_count} зан., {t.price:.0f} руб.)"
                    for t in types_],
        )
        if initial.get("type_id") is not None:
            for index, item in enumerate(types_):
                if item.type_id == initial["type_id"]:
                    self.type_combo.current(index)
                    break
        elif types_:
            self.type_combo.current(0)
        self.type_combo.pack(fill=tk.X, pady=(2, 10), ipady=3)

        tk.Label(form, text="Дата начала", bg="white", fg="#5a6478").pack(anchor="w")
        self.start = DateEntry(form, date_format="dd.mm.yyyy", width=14,
                              bg="#f5f6fa")
        if initial.get("start_date"):
            self.start.set_date(initial["start_date"])
        self.start.pack(fill=tk.X, pady=(2, 10), ipady=4)

        tk.Label(form, text="Осталось занятий", bg="white", fg="#5a6478").pack(anchor="w")
        self.remaining = tk.Spinbox(form, from_=0, to=500, width=8)
        self.remaining.delete(0, tk.END)
        self.remaining.insert(0, str(initial.get("remaining_lessons", 0)))
        self.remaining.pack(fill=tk.X, pady=(2, 10), ipady=4)

        tk.Label(form, text="Статус", bg="white", fg="#5a6478").pack(anchor="w")
        self.status_combo = ttk.Combobox(
            form, state="readonly", width=26,
            values=[SUB_LABELS[s] for s in SUB_STATUSES],
        )
        self.status_combo.current(
            SUB_STATUSES.index(initial.get("status", "active"))
            if initial.get("status") in SUB_STATUSES else 0
        )
        self.status_combo.pack(fill=tk.X, pady=(2, 12), ipady=3)

        tk.Button(
            form, text="Сохранить", command=self._save, cursor="hand2",
            bg="#1a1f33", fg="white", font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, bd=0,
            activebackground="#2e3554", activeforeground="white",
        ).pack(fill=tk.X, ipady=6)

    def _save(self):
        """Собирает значения и вызывает колбэк сохранения."""
        type_index = self.type_combo.current()
        if type_index < 0:
            raise ValueError("Выберите тип абонемента")
        data = {
            "student_id": (
                self.students[self.student_combo.current()].student_id
                if self.student_combo is not None and self.students else None
            ),
            "type_id": self.types[type_index].type_id,
            "start_date": self.start.get_date(),
            "remaining_lessons": int(self.remaining.get() or 0),
            "status": SUB_STATUSES[self.status_combo.current()],
        }
        try:
            self.on_save(data)
            self.destroy()
        except Exception as error:
            messagebox.showerror("Абонементы", str(error), parent=self)


class SubscriptionsView:
    """Таблица абонементов с продажей, редактированием и удалением."""

    def __init__(self, parent, session, user=None):
        """Инициализирует экран.

        Args:
            parent: родительский виджет.
            session: сессия SQLAlchemy.
            user: вошедший пользователь (у ученика кнопки скрыты).
        """
        self.session = session
        self.is_student = user is not None and getattr(user, "role", "") == "student"

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)
        if not self.is_student:
            make_header(self.frame, button_text="+ Продать абонемент",
                        command=self._on_add)
        else:
            make_header(self.frame)

        card = tk.Frame(self.frame, bg="white", padx=20, pady=16)
        card.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        self.table = ttk.Treeview(
            card, show="headings", selectmode="browse",
            columns=("id", "student", "type", "total", "remaining",
                     "start", "status"),
        )
        for column, text, width in (
            ("id", "№", 45),
            ("student", "Ученик", 190),
            ("type", "Тип", 160),
            ("total", "Занятий", 80),
            ("remaining", "Осталось", 85),
            ("start", "Начало", 100),
            ("status", "Статус", 100),
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
        """Перезагружает таблицу абонементов."""
        self.table.delete(*self.table.get_children())
        for sub in self.session.scalars(select(Subscription)):
            self.table.insert("", tk.END, iid=str(sub.subscription_id), values=(
                sub.subscription_id,
                sub.student.full_name if sub.student is not None else "—",
                sub.subscription_type.name if sub.subscription_type else "—",
                sub.total_lessons, sub.remaining_lessons,
                sub.start_date.strftime("%d.%m.%Y") if sub.start_date else "—",
                SUB_LABELS.get(sub.status, sub.status),
            ))

    def _selected(self):
        """Возвращает идентификатор выбранного абонемента или None."""
        selection = self.table.selection()
        if not selection:
            messagebox.showinfo("Абонементы", "Выберите абонемент в таблице",
                                parent=self.frame)
            return None
        return int(selection[0])

    def _students(self):
        """Возвращает список всех учеников."""
        return list(self.session.scalars(select(Student)))

    def _types(self):
        """Возвращает список всех типов абонементов."""
        return list(self.session.scalars(select(SubscriptionType)))

    def _on_add(self):
        """Открывает диалог продажи абонемента."""
        students, types_ = self._students(), self._types()
        if not students:
            messagebox.showinfo("Абонементы", "Сначала добавьте ученика",
                                parent=self.frame)
            return
        if not types_:
            messagebox.showinfo("Абонементы",
                                "Сначала создайте тип абонемента",
                                parent=self.frame)
            return
        dialog = SubscriptionDialog(
            self.frame, "Продажа абонемента", students, types_,
            on_save=self._create,
        )
        self.frame.wait_window(dialog)

    def _create(self, data):
        """Создаёт абонемент, фиксирует оплату и уведомление.

        Args:
            data: значения из диалога продажи.
        """
        sub_type = self.session.get(SubscriptionType, data["type_id"])
        subscription = Subscription(
            student_id=data["student_id"],
            type_id=data["type_id"],
            start_date=data["start_date"],
            total_lessons=sub_type.lessons_count,
            remaining_lessons=sub_type.lessons_count,
            status="active",
        )
        self.session.add(subscription)
        self.session.flush()
        # оплата фиксируется сразу при продаже
        self.session.add(Payment(
            student_id=data["student_id"],
            amount=sub_type.price,
            payment_date=data["start_date"],
            method="Абонемент",
        ))
        self.session.add(Notification(
            message=(f"Ученик {self.session.get(Student, data['student_id']).full_name}"
                     f" оплатил абонемент «{sub_type.name}» "
                     f"({sub_type.lessons_count} занятий)"),
            type="info",
        ))
        self.session.commit()
        self.refresh()

    def _save(self, data, subscription):
        """Сохраняет изменения существующего абонемента.

        Args:
            data: значения из диалога редактирования.
            subscription: редактируемый абонемент.
        """
        sub_type = self.session.get(SubscriptionType, data["type_id"])
        subscription.type_id = data["type_id"]
        subscription.start_date = data["start_date"]
        subscription.total_lessons = sub_type.lessons_count
        subscription.remaining_lessons = data["remaining_lessons"]
        subscription.status = data["status"]
        self.session.commit()
        self.refresh()

    def _on_edit(self):
        """Открывает диалог редактирования выбранного абонемента."""
        subscription_id = self._selected()
        if subscription_id is None:
            return
        subscription = self.session.get(Subscription, subscription_id)
        dialog = SubscriptionDialog(
            self.frame, "Редактирование абонемента", self._students(),
            self._types(),
            initial={
                "student_id": subscription.student_id,
                "type_id": subscription.type_id,
                "start_date": subscription.start_date,
                "remaining_lessons": subscription.remaining_lessons,
                "status": subscription.status,
            },
            on_save=lambda d: self._save(d, subscription),
            with_student=False,
        )
        self.frame.wait_window(dialog)

    def _on_delete(self):
        """Удаляет выбранный абонемент с подтверждением."""
        subscription_id = self._selected()
        if subscription_id is None:
            return
        if not messagebox.askyesno("Удаление", "Удалить абонемент?",
                                   parent=self.frame):
            return
        self.session.delete(self.session.get(Subscription, subscription_id))
        self.session.commit()
        self.refresh()

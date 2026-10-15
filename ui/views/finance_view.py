"""Экран «Финансы»: оплаты, долги, оплата задолженности."""

from datetime import date

import tkinter as tk
from tkinter import messagebox, ttk
from sqlalchemy import func, select

from database.models import Notification, Payment, Student, Subscription
from services.payment_service import PaymentService
from ui.dialogs.choice_dialog import ChoiceDialog
from ui.dialogs.form_dialog import FormDialog
from ui.theme import make_header

METHOD_OPTIONS = (("Наличный", "Наличный"), ("Безналичный", "Безналичный"))


class FinanceView:
    """Оплаты и задолженности с возможностью погасить долг."""

    def __init__(self, parent: tk.Widget, session) -> None:
        """Инициализирует экран.

        Args:
            parent: родительский виджет.
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.service = PaymentService(session)

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)
        make_header(self.frame, "Финансы", "+ Новая оплата", self._on_add_payment)

        stats = tk.Frame(self.frame, bg="#f5f6fa")
        stats.pack(fill=tk.X, pady=(14, 0))
        month_start = date.today().replace(day=1)
        revenue = self.service.get_revenue(month_start, date.today())
        total_paid = (
            self.session.scalar(select(func.coalesce(func.sum(Payment.amount), 0.0)))
            or 0.0
        )
        debt_total = sum(owed for _, _, owed in self._debts())
        for title, value in (
            ("Выручка за месяц", f"{revenue:.0f} ₽"),
            ("Поступления всего", f"{total_paid:.0f} ₽"),
            ("Задолженность", f"{debt_total:.0f} ₽"),
        ):
            card = tk.Frame(stats, bg="white", padx=16, pady=12)
            card.pack(side=tk.LEFT, padx=(0, 12), fill=tk.X, expand=True)
            tk.Label(
                card, text=title, bg="white", fg="#6b7590", font=("Segoe UI", 9)
            ).pack(anchor="w")
            tk.Label(
                card,
                text=value,
                bg="white",
                fg="#1a1f33",
                font=("Segoe UI", 15, "bold"),
            ).pack(anchor="w")

        actions = tk.Frame(self.frame, bg="#f5f6fa")
        actions.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(
            actions,
            text="Оплатить задолженность",
            style="Primary.TButton",
            command=self._on_pay_debt,
        ).pack(side=tk.LEFT)

        card = tk.Frame(self.frame, bg="white", padx=20, pady=16)
        card.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        self.table = ttk.Treeview(
            card,
            show="headings",
            selectmode="browse",
            columns=("id", "date", "student", "sub", "amount", "method"),
        )
        for column, text, width in (
            ("id", "№", 50),
            ("date", "Дата", 110),
            ("student", "Ученик", 200),
            ("sub", "Абонемент", 130),
            ("amount", "Сумма", 100),
            ("method", "Способ", 120),
        ):
            self.table.heading(column, text=text)
            self.table.column(column, width=width, anchor=tk.W)
        self.table.tag_configure("cash", foreground="#b45309")
        self.table.tag_configure("cashless", foreground="#047857")
        scrollbar = ttk.Scrollbar(card, orient=tk.VERTICAL, command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.refresh()

    def refresh(self) -> None:
        """Перезагружает таблицу оплат."""
        self.table.delete(*self.table.get_children())
        for row in self.service.get_table_rows():
            payment_id, date_text, student, sub_name, amount, method = row
            tag = "cash" if method == "Наличный" else "cashless"
            self.table.insert(
                "",
                tk.END,
                tags=(tag,),
                values=(
                    payment_id,
                    date_text,
                    student,
                    sub_name,
                    f"{amount:.0f} ₽",
                    method,
                ),
            )

    def _debts(self) -> list[tuple[int, str, float]]:
        """Считает задолженности по активным абонементам.

        Returns:
            Список кортежей (student_id, ФИО, сумма долга).
        """
        subs = list(
            self.session.scalars(
                select(Subscription).where(Subscription.status == "active")
            )
        )
        paid = dict(
            self.session.execute(
                select(
                    Payment.student_id,
                    func.coalesce(func.sum(Payment.amount), 0.0),
                ).group_by(Payment.student_id)
            ).all()
        )
        billed: dict[int, float] = {}
        for sub in subs:
            price = sub.subscription_type.price if sub.subscription_type else 0
            billed[sub.student_id] = billed.get(sub.student_id, 0) + price
        debts = []
        for student_id, total in billed.items():
            owed = total - paid.get(student_id, 0.0)
            if owed > 0:
                student = self.session.get(Student, student_id)
                if student is not None:
                    debts.append((student_id, student.full_name, owed))
        return debts

    def _student_options(self) -> list[tuple]:
        """Собирает варианты учеников для списка.

        Returns:
            Список кортежей (student_id, ФИО).
        """
        return [
            (student.student_id, student.full_name)
            for student in self.session.scalars(select(Student))
        ]

    def _create_payment(self, student_id: int, amount_text: str, method: str) -> None:
        """Сохраняет оплату и создаёт уведомление.

        Args:
            student_id: идентификатор ученика.
            amount_text: сумма строкой.
            method: способ оплаты.
        """
        try:
            amount = float(str(amount_text).replace(",", "."))
        except (TypeError, ValueError):
            messagebox.showerror(
                "Финансы", "Сумма должна быть числом", parent=self.frame
            )
            return
        if amount <= 0:
            messagebox.showerror(
                "Финансы", "Сумма должна быть больше нуля", parent=self.frame
            )
            return
        student = self.session.get(Student, student_id)
        self.session.add(
            Payment(
                student_id=student_id,
                amount=amount,
                payment_date=date.today(),
                method=method,
            )
        )
        self.session.add(
            Notification(
                message=f"Поступила оплата {amount:.0f} руб. от {student.full_name}",
                type="payment",
                created_at=date.today(),
            )
        )
        self.session.commit()
        self.refresh()

    def _on_add_payment(self) -> None:
        """Открывает форму новой оплаты."""
        options = self._student_options()
        if not options:
            messagebox.showinfo(
                "Финансы", "Сначала добавьте учеников", parent=self.frame
            )
            return
        fields = [
            ("student_id", "Ученик", "combo", options),
            ("amount", "Сумма", "entry", ()),
            ("method", "Способ", "combo", METHOD_OPTIONS),
        ]
        dialog = FormDialog(self.frame, "Новая оплата", fields)
        self.frame.wait_window(dialog.top)
        if not dialog.result:
            return
        data = dialog.result
        if data.get("student_id") is None:
            return
        self._create_payment(data["student_id"], data["amount"], data["method"])

    def _on_pay_debt(self) -> None:
        """Гасит задолженность выбранного ученика."""
        debts = self._debts()
        if not debts:
            messagebox.showinfo(
                "Финансы", "Задолженностей нет — все долги погашены", parent=self.frame
            )
            return
        options = [
            (student_id, f"{name} — долг {owed:.0f} руб.")
            for student_id, name, owed in debts
        ]
        dialog = ChoiceDialog(
            self.frame, "Оплата задолженности", options, "Выберите ученика:"
        )
        self.frame.wait_window(dialog.top)
        if dialog.result is None:
            return
        student_id, name, owed = next(
            item for item in debts if item[0] == dialog.result
        )
        fields = [
            ("amount", f"Сумма (долг {owed:.0f} руб.)", "entry", ()),
            ("method", "Способ", "combo", METHOD_OPTIONS),
        ]
        pay_dialog = FormDialog(
            self.frame,
            f"Оплата долга — {name}",
            fields,
            {"amount": f"{owed:.0f}"},
        )
        self.frame.wait_window(pay_dialog.top)
        if not pay_dialog.result:
            return
        data = pay_dialog.result
        self._create_payment(student_id, data["amount"], data["method"])

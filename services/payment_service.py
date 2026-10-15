from __future__ import annotations
"""Сервис финансов: оплаты, выручка, таблица платежей."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import Payment, Student, Subscription, SubscriptionType
from repositories.base_repository import BaseRepository


class PaymentService:
    """Бизнес-логика оплат."""

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.repo = BaseRepository(Payment, session)

    def get_all_payments(self) -> list[Payment]:
        """Возвращает все оплаты, свежие сверху.

        Returns:
            Список объектов Payment.
        """
        return sorted(self.repo.get_all(), key=lambda p: p.payment_date, reverse=True)

    def get_revenue(self, start: date, end: date) -> float:
        """Считает выручку за период.

        Args:
            start: дата начала.
            end: дата конца.

        Returns:
            Сумма оплат за период.
        """
        return (
            self.session.scalar(
                select(func.coalesce(func.sum(Payment.amount), 0.0)).where(
                    Payment.payment_date >= start,
                    Payment.payment_date <= end,
                )
            )
            or 0.0
        )

    def _latest_subscription(self, student_id: int) -> Subscription | None:
        """Возвращает последний абонемент ученика.

        Args:
            student_id: идентификатор ученика.

        Returns:
            Объект Subscription или None.
        """
        return self.session.scalars(
            select(Subscription)
            .where(Subscription.student_id == student_id)
            .order_by(Subscription.subscription_id.desc())
        ).first()

    def _subscription_name(self, subscription: Subscription | None) -> str:
        """Возвращает название типа абонемента без опоры на связь.

        Args:
            subscription: объект Subscription или None.

        Returns:
            Название типа или «—».
        """
        if subscription is None:
            return "—"
        sub_type = subscription.subscription_type
        if sub_type is None and getattr(subscription, "type_id", None):
            sub_type = self.session.get(SubscriptionType, subscription.type_id)
        return sub_type.name if sub_type is not None else "—"

    def get_table_rows(self) -> list[tuple]:
        """Собирает строки для таблицы оплат.

        Returns:
            Кортежи (id, дата, ученик, абонемент, сумма, способ).
        """
        rows = []
        for payment in self.get_all_payments():
            student = self.session.get(Student, payment.student_id)
            name = student.full_name if student is not None else "—"
            latest = self._latest_subscription(payment.student_id)
            method = getattr(payment, "method", "") or "—"
            rows.append(
                (
                    payment.payment_id,
                    str(payment.payment_date),
                    name,
                    self._subscription_name(latest),
                    float(payment.amount),
                    method,
                )
            )
        return rows

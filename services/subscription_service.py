"""Сервис абонементов: типы, продажа, списание занятий."""

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Notification, Student, Subscription, SubscriptionType
from repositories.base_repository import BaseRepository


class SubscriptionService:
    """Бизнес-логика абонементов."""

    STATUS_LABELS = {
        "active": "Активен",
        "expired": "Закончился",
        "cancelled": "Отменён",
    }

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.repo = BaseRepository(Subscription, session)
        self.type_repo = BaseRepository(SubscriptionType, session)

    def create_type(self, name: str, lessons_count, price) -> SubscriptionType:
        """Создаёт тип абонемента с валидацией.

        Args:
            name: название типа.
            lessons_count: количество занятий.
            price: цена.

        Returns:
            Созданный объект SubscriptionType.

        Raises:
            ValueError: при некорректных данных.
        """
        if not name.strip():
            raise ValueError("Название не может быть пустым")
        try:
            lessons_count = int(lessons_count)
            price = float(str(price).replace(",", "."))
        except (TypeError, ValueError):
            raise ValueError("Занятия — целое число, цена — число")
        if lessons_count <= 0:
            raise ValueError("Количество занятий должно быть больше нуля")
        if price < 0:
            raise ValueError("Цена не может быть отрицательной")
        return self.type_repo.create(
            name=name.strip(), lessons_count=lessons_count, price=price
        )

    def get_all_types(self) -> list[SubscriptionType]:
        """Возвращает все типы абонементов."""
        return self.type_repo.get_all()

    def sell_subscription(self, student_id: int, type_id: int) -> Subscription:
        """Продаёт абонемент ученику и создаёт уведомление.

        Args:
            student_id: идентификатор ученика.
            type_id: идентификатор типа абонемента.

        Returns:
            Созданный объект Subscription.

        Raises:
            ValueError: если ученик или тип не найдены.
        """
        student = self.session.get(Student, student_id)
        if student is None:
            raise ValueError("Ученик не найден")
        sub_type = self.session.get(SubscriptionType, type_id)
        if sub_type is None:
            raise ValueError("Тип абонемента не найден")
        start = date.today()
        subscription = self.repo.create(
            student_id=student_id,
            type_id=type_id,
            start_date=start,
            end_date=start + timedelta(days=90),
            total_lessons=sub_type.lessons_count,
            remaining_lessons=sub_type.lessons_count,
            status="active",
        )
        self._notify(f"Ученику {student.full_name} продан абонемент «{sub_type.name}»")
        return subscription

    def spend_lesson(self, subscription: Subscription) -> Subscription:
        """Списывает одно занятие; при нуле закрывает абонемент.

        Args:
            subscription: объект Subscription.

        Returns:
            Обновлённый объект Subscription.

        Raises:
            ValueError: если абонемент не активен или занятия кончились.
        """
        if subscription.status != "active":
            raise ValueError("Абонемент не активен")
        if subscription.remaining_lessons <= 0:
            subscription.status = "expired"
            self.session.commit()
            raise ValueError("Занятия по этому абонементу закончились")
        subscription.remaining_lessons -= 1
        if subscription.remaining_lessons == 0:
            subscription.status = "expired"
            name = subscription.student.full_name if subscription.student else "—"
            self._notify(f"Абонемент ученика {name} закончился")
        self.session.commit()
        return subscription

    def get_student_subscriptions(self, student_id: int) -> list[Subscription]:
        """Возвращает абонементы ученика.

        Args:
            student_id: идентификатор ученика.

        Returns:
            Список объектов Subscription.
        """
        return list(
            self.session.scalars(
                select(Subscription).where(Subscription.student_id == student_id)
            )
        )

    def get_all_subscriptions(self) -> list[Subscription]:
        """Возвращает все абонементы."""
        return self.repo.get_all()

    def get_table_rows(self) -> list[tuple]:
        """Собирает строки для таблицы абонементов.

        Returns:
            Кортежи (id, ученик, тип, осталось, всего, цена, статус).
        """
        rows = []
        for sub in self.repo.get_all():
            sub_type = sub.subscription_type
            total = getattr(sub, "total_lessons", None) or (
                sub_type.lessons_count if sub_type else 0
            )
            price = sub_type.price if sub_type else 0
            name = sub.student.full_name if sub.student else "—"
            type_name = sub_type.name if sub_type else "—"
            rows.append(
                (
                    sub.subscription_id,
                    name,
                    type_name,
                    sub.remaining_lessons,
                    total,
                    price,
                    sub.status,
                )
            )
        return rows

    def _notify(self, message: str) -> None:
        """Создаёт уведомление.

        Args:
            message: текст уведомления.
        """
        self.session.add(
            Notification(
                message=message, type="subscription", created_at=datetime.now()
            )
        )

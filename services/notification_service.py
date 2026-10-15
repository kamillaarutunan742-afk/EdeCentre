"""Сервис уведомлений: чтение, отметки, удаление."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import Notification


class NotificationService:
    """Работа с уведомлениями."""

    TYPE_LABELS = {
        "subscription": "Окончание абонемента",
        "payment": "Долг по оплате",
        "expiry": "Истечение срока",
        "info": "Информация",
    }

    def __init__(self, session: Session) -> None:
        """Инициализирует сервис.

        Args:
            session: сессия SQLAlchemy.
        """
        self.session = session

    def get_all(self) -> list[Notification]:
        """Возвращает уведомления: новые сверху."""
        return list(
            self.session.scalars(
                select(Notification).order_by(Notification.created_at.desc())
            )
        )

    def unread_count(self) -> int:
        """Считает непрочитанные уведомления."""
        return (
            self.session.scalar(
                select(func.count(Notification.notification_id)).where(
                    Notification.is_read == False  # noqa: E712
                )
            )
            or 0
        )

    def mark_read(self, notification: Notification) -> None:
        """Отмечает одно уведомление прочитанным."""
        notification.is_read = True
        self.session.commit()

    def mark_all_read(self) -> None:
        """Отмечает все уведомления прочитанными."""
        for item in self.session.scalars(
            select(Notification).where(Notification.is_read == False)  # noqa: E712
        ):
            item.is_read = True
        self.session.commit()

    def delete(self, notification: Notification) -> None:
        """Удаляет уведомление."""
        self.session.delete(notification)
        self.session.commit()

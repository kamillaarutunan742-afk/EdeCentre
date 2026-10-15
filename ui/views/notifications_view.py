"""Экран «Уведомления» в стиле прототипа EduCenter."""

from datetime import datetime

import tkinter as tk
from tkinter import messagebox

from services.notification_service import NotificationService
from ui.theme import make_header

TYPE_COLORS = {
    "subscription": "#3b82f6",
    "payment": "#3b82f6",
    "expiry": "#8a93a5",
    "info": "#8a93a5",
}


def time_ago(value: datetime) -> str:
    """Возвращает человеческую давность события.

    Args:
        value: момент создания уведомления.

    Returns:
        Строка вида «2 мин назад», «Вчера», «3 дня назад».
    """
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    seconds = (datetime.now() - value).total_seconds()
    if seconds < 3600:
        return f"{max(int(seconds // 60), 1)} мин назад"
    if seconds < 86400:
        hours = int(seconds // 3600)
        return (
            f"{hours} час{'а' if 2 <= hours <= 4 else ''} назад"
            if hours > 1
            else "1 час назад"
        )
    days = int(seconds // 86400)
    if days == 1:
        return "Вчера"
    return f"{days} дня назад" if 2 <= days <= 4 else f"{days} дней назад"


class NotificationsView:
    """Список уведомлений: клик — отметить прочитанным."""

    def __init__(self, parent: tk.Widget, session) -> None:
        """Инициализирует экран.

        Args:
            parent: родительский виджет.
            session: сессия SQLAlchemy.
        """
        self.session = session
        self.service = NotificationService(session)

        self.frame = tk.Frame(parent, bg="#f5f6fa")
        self.frame.pack(fill=tk.BOTH, expand=True)

        make_header(
            self.frame,
            "Уведомления",
            "Отметить все прочитанными",
            self._on_mark_all,
        )

        self.list_frame = tk.Frame(self.frame, bg="white", padx=16, pady=12)
        self.list_frame.pack(fill=tk.BOTH, expand=True, pady=(14, 0))
        self.refresh()

    def refresh(self) -> None:
        """Перезагружает список уведомлений."""
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        items = self.service.get_all()
        if not items:
            tk.Label(
                self.list_frame,
                text="Уведомлений нет 🔕",
                bg="white",
                fg="#6b7590",
            ).pack(anchor="w", pady=8)
            return
        for item in items:
            self._row(item)

    def _row(self, item) -> None:
        """Рисует строку одного уведомления.

        Args:
            item: объект Notification.
        """
        dot_color = TYPE_COLORS.get(item.type, "#8a93a5")
        if item.is_read:
            dot_color = "#d7dbe2"
        row = tk.Frame(
            self.list_frame,
            bg="white",
            pady=10,
            highlightthickness=1,
            highlightbackground="#eceef2",
        )
        row.pack(fill=tk.X, pady=2)

        tk.Canvas(row, width=10, height=10, bg="white", highlightthickness=0).pack(
            side=tk.LEFT, padx=(4, 8)
        )
        row.winfo_children()[-1].create_oval(1, 1, 9, 9, fill=dot_color, outline="")

        type_text = NotificationService.TYPE_LABELS.get(item.type, "Информация")
        fg = "#8a93a5" if item.is_read else "#1a1f33"
        tk.Label(
            row,
            text=type_text,
            bg="white",
            fg=fg,
            font=("Segoe UI", 9),
            width=18,
            anchor="w",
        ).pack(side=tk.LEFT)
        tk.Label(
            row,
            text=item.message,
            bg="white",
            fg=fg,
            font=("Segoe UI", 9, "bold" if not item.is_read else "normal"),
            anchor="w",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            row,
            text=time_ago(item.created_at),
            bg="white",
            fg="#8a93a5",
            font=("Segoe UI", 8),
        ).pack(side=tk.RIGHT, padx=6)

        row.bind("<Button-1>", lambda event, n=item: self._toggle_read(n))
        for child in row.winfo_children():
            child.bind("<Button-1>", lambda event, n=item: self._toggle_read(n))

    def _toggle_read(self, item) -> None:
        """Переключает статус «прочитано» у уведомления.

        Args:
            item: объект Notification.
        """
        item.is_read = not item.is_read
        self.session.commit()
        self.refresh()

    def _on_mark_all(self) -> None:
        """Отмечает все уведомления прочитанными."""
        self.service.mark_all_read()
        self.refresh()
        messagebox.showinfo(
            "Уведомления",
            "Все уведомления отмечены прочитанными",
            parent=self.frame,
        )

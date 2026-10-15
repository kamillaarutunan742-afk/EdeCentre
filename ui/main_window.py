"""Главное окно приложения: тёмное меню, шапка с обновлением, роли."""

import inspect

import tkinter as tk
from tkinter import messagebox, ttk

from database.models import User
from ui.theme import (
    BG_CONTENT,
    BG_SIDEBAR,
    FONT_BASE,
    SIDEBAR_ACTIVE,
    TEXT_MUTED,
    apply_theme,
)
from ui.views.dashboard_view import DashboardView
from ui.views.students_view import StudentsView
from ui.views.teachers_view import TeachersView
from ui.views.groups_view import GroupsView
from ui.views.schedule_view import ScheduleView
from ui.views.attendance_view import AttendanceView
from ui.views.subscriptions_view import SubscriptionsView
from ui.views.finance_view import FinanceView
from ui.views.notifications_view import NotificationsView
from ui.views.reports_view import ReportsView
from services.notification_service import NotificationService
from ui.dialogs.password_dialog import ChangePasswordDialog

MENU = (
    ("Дашборд", "⌂"),
    ("Ученики", "☺"),
    ("Группы", "▦"),
    ("Абонементы", "▣"),
    ("Посещаемость", "✔"),
    ("Расписание", "▤"),
    ("Финансы", "₽"),
    ("Отчёты", "◫"),
    ("Уведомления", "✉"),
)

SECTIONS = {
    "Дашборд": DashboardView,
    "Ученики": StudentsView,
    "Группы": GroupsView,
    "Абонементы": SubscriptionsView,
    "Посещаемость": AttendanceView,
    "Расписание": ScheduleView,
    "Финансы": FinanceView,
    "Отчёты": ReportsView,
    "Уведомления": NotificationsView,
}

ROLE_SECTIONS = {
    "student": ("Дашборд", "Расписание", "Уведомления"),
}


class MainWindow:
    """Главное окно с навигацией по разделам."""

    def __init__(self, session, user: User, on_logout=None) -> None:
        """Инициализирует главное окно.

        Args:
            session: сессия SQLAlchemy.
            user: вошедший пользователь.
            on_logout: обратный вызов выхода (опционально).
        """
        self.session = session
        self.user = user
        self.on_logout = on_logout
        self.current_section = "Дашборд"
        self.menu_buttons: dict[str, tk.Button] = {}
        self.role_sections = ROLE_SECTIONS.get(getattr(user, "role", ""), None)
        self.notif_service = NotificationService(session)

        self.root = tk.Tk()
        apply_theme(self.root)
        self.root.title("EduCenter — языковая школа")
        self.root.geometry("1150x680")
        self.root.minsize(960, 600)
        self._build_layout()

    def _build_layout(self) -> None:
        """Создаёт меню, шапку и область содержимого."""
        sidebar = tk.Frame(self.root, width=210, bg=BG_SIDEBAR)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar,
            text="EduCenter",
            bg=BG_SIDEBAR,
            fg="white",
            font=("Segoe UI", 14, "bold"),
            pady=16,
        ).pack(fill=tk.X, padx=10)

        for name, icon in MENU:
            if self.role_sections is not None and name not in self.role_sections:
                continue
            button = tk.Button(
                sidebar,
                text=f" {icon}  {name}",
                anchor="w",
                relief=tk.FLAT,
                bg=BG_SIDEBAR,
                fg="#c7cfdd",
                font=FONT_BASE,
                padx=14,
                pady=9,
                bd=0,
                cursor="hand2",
                activebackground=SIDEBAR_ACTIVE,
                activeforeground="white",
                command=lambda n=name: self._show_section(n),
            )
            button.pack(fill=tk.X, padx=8, pady=1)
            self.menu_buttons[name] = button

        tk.Button(
            sidebar,
            text="  Сменить пароль",
            anchor="w",
            relief=tk.FLAT,
            bg=BG_SIDEBAR,
            fg=TEXT_MUTED,
            font=FONT_BASE,
            padx=14,
            pady=6,
            bd=0,
            cursor="hand2",
            activebackground=BG_SIDEBAR,
            activeforeground="white",
            command=self._on_change_password,
        ).pack(side=tk.BOTTOM, fill=tk.X, padx=8)
        tk.Button(
            sidebar,
            text=" ←  Выйти",
            anchor="w",
            relief=tk.FLAT,
            bg=BG_SIDEBAR,
            fg=TEXT_MUTED,
            font=FONT_BASE,
            padx=14,
            pady=8,
            bd=0,
            cursor="hand2",
            activebackground=BG_SIDEBAR,
            activeforeground="white",
            command=self._on_logout,
        ).pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 10))

        header = tk.Frame(self.root, bg="white", height=58)
        header.pack(side=tk.TOP, fill=tk.X)
        header.pack_propagate(False)
        tk.Frame(header, bg="#eceef2", height=1).pack(side=tk.BOTTOM, fill=tk.X)
        self.header_label = tk.Label(
            header,
            text="Дашборд",
            bg="white",
            fg="#1a1f33",
            font=("Segoe UI", 14, "bold"),
        )
        self.header_label.pack(side=tk.LEFT, padx=22)
        ttk.Button(
            header,
            text="⟳ Обновить",
            style="Secondary.TButton",
            command=self._refresh_section,
        ).pack(side=tk.RIGHT, padx=16, pady=12)
        self.notif_badge = tk.Label(
            header,
            text="",
            bg="white",
            fg="#dc2626",
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        self.notif_badge.pack(side=tk.RIGHT, padx=8)
        self.notif_badge.bind("<Button-1>", lambda e: self._show_section("Уведомления"))
        tk.Label(
            header,
            text=f"{self.user.full_name} ({self.user.role})",
            bg="white",
            fg="#6b7590",
            font=("Segoe UI", 9),
        ).pack(side=tk.RIGHT, padx=8)

        self.content = tk.Frame(self.root, bg=BG_CONTENT)
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.refresh_badge()
        self._show_section("Дашборд")

    def refresh_badge(self) -> None:
        """Обновляет счётчик непрочитанных уведомлений в шапке.

        Если непрочитанных нет — значок скрывается.
        """
        count = self.notif_service.unread_count()
        if count:
            self.notif_badge.config(
                text=f"🔔 новых уведомлений: {count}", state=tk.NORMAL
            )
        else:
            self.notif_badge.config(text="", state=tk.DISABLED)

    def _refresh_section(self) -> None:
        """Перерисовывает текущий раздел (обновляет данные из БД)."""
        self._show_section(self.current_section)

    def _show_section(self, name: str) -> None:
        """Отображает выбранный раздел и подсвечивает пункт меню.

        Args:
            name: название раздела из меню.
        """
        self.current_section = name
        for item, button in self.menu_buttons.items():
            if item == name:
                button.config(bg=SIDEBAR_ACTIVE, fg="white")
            else:
                button.config(bg=BG_SIDEBAR, fg="#c7cfdd")

        self.header_label.config(text=name)

        # при открытии «Уведомлений» помечаем всё прочитанным
        if name == "Уведомления":
            self.notif_service.mark_all_read()

        for widget in self.content.winfo_children():
            widget.destroy()
        view_class = SECTIONS.get(name)
        if view_class is not None:
            if "user" in inspect.signature(view_class.__init__).parameters:
                view_class(self.content, self.session, user=self.user)
            else:
                view_class(self.content, self.session)

        self.refresh_badge()

    def _on_change_password(self) -> None:
        """Открывает диалог смены пароля."""
        dialog = ChangePasswordDialog(self.root, self.user.login)
        self.root.wait_window(dialog.top)
        if dialog.result:
            messagebox.showinfo(
                "Профиль",
                "Пароль обновлён, используйте его при следующем входе",
                parent=self.root,
            )

    def _on_logout(self) -> None:
        """Выполняет выход из учётной записи."""
        if self.on_logout is not None:
            self.root.destroy()
            self.on_logout()
        else:
            self.root.destroy()

    def run(self) -> None:
        """Запускает цикл событий главного окна."""
        self.root.mainloop()

"""Точка входа приложения EduCenter."""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tkinter import messagebox

from database.db import SessionLocal, init_db
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


def show_callback_error(exc_type, exc_value, exc_tb) -> None:
    """Показывает ошибки обработчиков кнопок вместо молчаливого падения."""
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(text)
    try:
        messagebox.showerror(
            "Ошибка в приложении",
            f"{exc_type.__name__}: {exc_value}\n\nПолный текст — в консоли",
        )
    except Exception:
        pass


def main() -> None:
    """Запускает приложение: вход, затем главное окно."""
    init_db()
    login_window = LoginWindow()
    login_window.root.report_callback_exception = show_callback_error
    login_window.run()

    user = login_window.user
    if user is None:
        return

    session = SessionLocal()
    main_window = MainWindow(session, user)
    main_window.root.report_callback_exception = show_callback_error
    main_window.run()
    session.close()


if __name__ == "__main__":
    main()

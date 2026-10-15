"""Диалог смены пароля."""

import tkinter as tk
from tkinter import messagebox

from services.auth_service import change_password


class ChangePasswordDialog:
    """Окно смены пароля: текущий, новый, повтор нового.

    Attributes:
        result: True при успешной смене.
    """

    def __init__(self, parent: tk.Widget, login: str) -> None:
        """Создаёт диалог.

        Args:
            parent: родительский виджет.
            login: логин пользователя.
        """
        self.result = False
        self.login = login

        self.top = tk.Toplevel(parent)
        self.top.title("Смена пароля")
        self.top.transient(parent.winfo_toplevel())
        self.top.grab_set()
        self.top.resizable(False, False)

        form = tk.Frame(self.top, bg="white", padx=24, pady=18)
        form.pack(fill=tk.BOTH, expand=True)

        self.entries: dict[str, tk.Entry] = {}
        for key, label in (
            ("old", "Текущий пароль"),
            ("new", "Новый пароль"),
            ("repeat", "Повторите новый пароль"),
        ):
            tk.Label(form, text=label, bg="white", fg="#5a6478").pack(anchor="w")
            entry = tk.Entry(
                form,
                width=28,
                show="•",
                relief=tk.FLAT,
                bg="#f5f6fa",
                highlightthickness=1,
                highlightbackground="#dfe4ec",
            )
            entry.pack(fill=tk.X, pady=(2, 10), ipady=4)
            self.entries[key] = entry

        save_button = tk.Button(
            form,
            text="Сменить пароль",
            command=self._on_save,
            cursor="hand2",
            bg="#1a1f33",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            bd=0,
            activebackground="#2e3554",
            activeforeground="white",
        )
        save_button.pack(fill=tk.X, ipady=6, pady=(4, 0))

    def _on_save(self) -> None:
        """Проверяет совпадение паролей и сохраняет новый."""
        new = self.entries["new"].get()
        if new != self.entries["repeat"].get():
            messagebox.showerror(
                "Смена пароля", "Новые пароли не совпадают", parent=self.top
            )
            return
        ok, message = change_password(
            self.login,
            self.entries["old"].get(),
            new,
        )
        if ok:
            messagebox.showinfo("Смена пароля", message, parent=self.top)
            self.result = True
            self.top.destroy()
        else:
            messagebox.showerror("Смена пароля", message, parent=self.top)

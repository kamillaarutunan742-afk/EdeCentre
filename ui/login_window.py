"""Окно входа EduCenter: вход, регистрация, восстановление пароля."""

import tkinter as tk
from tkinter import messagebox, ttk

from services.auth_service import (
    authenticate,
    register_user,
    reset_password_with_secret,
)

BG = "#1a1f33"
FIELD_BG = "#f5f6fa"
ROLES = (("student", "Ученик"), ("manager", "Менеджер"), ("admin", "Администратор"))


class LoginWindow:
    """Первое окно приложения.

    Attributes:
        user: вошедший пользователь или None.
    """

    def __init__(self) -> None:
        """Создаёт окно входа."""
        self.user = None
        self.root = tk.Tk()
        self.root.title("EduCenter — вход")
        self.root.geometry("420x500")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        tk.Label(
            self.root,
            text="EduCenter",
            bg=BG,
            fg="white",
            font=("Segoe UI", 22, "bold"),
        ).pack(pady=(34, 2))
        tk.Label(
            self.root, text="Языковая школа — система управления", bg=BG, fg="#aab3c5"
        ).pack(pady=(0, 26))

        form = tk.Frame(self.root, bg=BG)
        form.pack()
        self.login_entry = self._field(form, "Логин")
        self.password_entry = self._field(form, "Пароль", show="•")

        tk.Button(
            self.root,
            text="Войти",
            command=self._on_login,
            cursor="hand2",
            bg="white",
            fg=BG,
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            bd=0,
            activebackground="#dfe4ec",
        ).pack(fill=tk.X, padx=60, pady=(18, 6), ipady=7)
        tk.Button(
            self.root,
            text="Зарегистрироваться",
            command=self._on_register,
            cursor="hand2",
            bg="#2e3554",
            fg="white",
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            bd=0,
            activebackground="#3a4270",
            activeforeground="white",
        ).pack(fill=tk.X, padx=60, pady=4, ipady=6)
        tk.Button(
            self.root,
            text="Забыли пароль?",
            command=self._on_reset,
            cursor="hand2",
            bg=BG,
            fg="#aab3c5",
            font=("Segoe UI", 9, "underline"),
            relief=tk.FLAT,
            bd=0,
            activebackground=BG,
            activeforeground="white",
        ).pack(pady=(14, 0))

    def _field(self, parent: tk.Widget, label: str, show: str = "") -> tk.Entry:
        """Создаёт подписанное поле ввода.

        Args:
            parent: родительский виджет.
            label: подпись поля.
            show: символ маскировки («•» для пароля).

        Returns:
            Поле ввода.
        """
        tk.Label(parent, text=label, bg=BG, fg="#aab3c5", font=("Segoe UI", 9)).pack(
            anchor="w", padx=60, pady=(8, 2)
        )
        entry = tk.Entry(
            parent,
            width=26,
            show=show,
            relief=tk.FLAT,
            bg=FIELD_BG,
            highlightthickness=1,
            highlightbackground="#3a4270",
            font=("Segoe UI", 11),
        )
        entry.pack(ipady=6, padx=60)
        return entry

    def _on_login(self) -> None:
        """Проверяет учётные данные и открывает главное окно."""
        user = authenticate(self.login_entry.get().strip(), self.password_entry.get())
        if user is None:
            messagebox.showerror("Вход", "Неверный логин или пароль", parent=self.root)
            return
        self.user = user
        self.root.destroy()

    def _on_register(self) -> None:
        """Открывает диалог регистрации нового аккаунта."""
        top = tk.Toplevel(self.root)
        top.title("Регистрация")
        top.configure(bg="white")
        top.transient(self.root)
        top.grab_set()
        top.resizable(False, False)

        form = tk.Frame(top, bg="white", padx=24, pady=18)
        form.pack()
        entries: dict[str, tk.Entry] = {}
        for key, label, show in (
            ("login", "Логин", ""),
            ("password", "Пароль (минимум 6 символов)", "•"),
            ("name", "ФИО", ""),
            ("secret", "Секретное слово (для восстановления)", ""),
        ):
            tk.Label(form, text=label, bg="white", fg="#5a6478").pack(anchor="w")
            entry = tk.Entry(
                form,
                width=28,
                show=show,
                relief=tk.FLAT,
                bg=FIELD_BG,
                highlightthickness=1,
                highlightbackground="#dfe4ec",
            )
            entry.pack(fill=tk.X, pady=(2, 10), ipady=4)
            entries[key] = entry

        tk.Label(form, text="Роль", bg="white", fg="#5a6478").pack(anchor="w")
        role_combo = ttk.Combobox(
            form, state="readonly", width=26, values=[label for _, label in ROLES]
        )
        role_combo.current(0)
        role_combo.pack(fill=tk.X, pady=(2, 12), ipady=3)

        def on_save() -> None:
            """Создаёт аккаунт."""
            role = ROLES[role_combo.current()][0]
            user = register_user(
                entries["login"].get().strip(),
                entries["password"].get(),
                role=role,
                full_name=entries["name"].get().strip() or None,
                secret_word=entries["secret"].get().strip(),
            )
            if user is None:
                messagebox.showerror(
                    "Регистрация",
                    "Логин занят или пароль короче 6 символов",
                    parent=top,
                )
                return
            messagebox.showinfo(
                "Регистрация",
                "Аккаунт создан. Запомните секретное слово — по нему "
                "восстанавливается пароль. Теперь войдите",
                parent=top,
            )
            top.destroy()

        tk.Button(
            form,
            text="Создать аккаунт",
            command=on_save,
            cursor="hand2",
            bg=BG,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            bd=0,
            activebackground="#2e3554",
            activeforeground="white",
        ).pack(fill=tk.X, ipady=6)

    def _on_reset(self) -> None:
        """Открывает диалог восстановления пароля по секретному слову."""
        top = tk.Toplevel(self.root)
        top.title("Восстановление пароля")
        top.configure(bg="white")
        top.transient(self.root)
        top.grab_set()
        top.resizable(False, False)

        form = tk.Frame(top, bg="white", padx=24, pady=18)
        form.pack()
        entries: dict[str, tk.Entry] = {}
        for key, label, show in (
            ("login", "Логин", ""),
            ("secret", "Секретное слово", ""),
            ("new", "Новый пароль", "•"),
            ("repeat", "Повторите новый пароль", "•"),
        ):
            tk.Label(form, text=label, bg="white", fg="#5a6478").pack(anchor="w")
            entry = tk.Entry(
                form,
                width=28,
                show=show,
                relief=tk.FLAT,
                bg=FIELD_BG,
                highlightthickness=1,
                highlightbackground="#dfe4ec",
            )
            entry.pack(fill=tk.X, pady=(2, 10), ipady=4)
            entries[key] = entry

        def on_save() -> None:
            """Сохраняет новый пароль после проверки секретного слова."""
            if entries["new"].get() != entries["repeat"].get():
                messagebox.showerror(
                    "Восстановление", "Пароли не совпадают", parent=top
                )
                return
            ok, message = reset_password_with_secret(
                entries["login"].get().strip(),
                entries["secret"].get(),
                entries["new"].get(),
            )
            if ok:
                messagebox.showinfo("Восстановление", message, parent=top)
                top.destroy()
            else:
                messagebox.showerror("Восстановление", message, parent=top)

        tk.Button(
            form,
            text="Сменить пароль",
            command=on_save,
            cursor="hand2",
            bg=BG,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            bd=0,
            activebackground="#2e3554",
            activeforeground="white",
        ).pack(fill=tk.X, ipady=6)

    def run(self) -> None:
        """Запускает цикл событий окна входа."""
        self.root.mainloop()

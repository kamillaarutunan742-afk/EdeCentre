"""Диалог выбора одного значения из списка."""

import tkinter as tk
from tkinter import ttk


class ChoiceDialog:
    """Модальное окно выбора элемента из списка.

    Attributes:
        result: выбранное значение или None при отмене.
    """

    def __init__(
        self, parent: tk.Widget, title: str, options: list, label: str = "Выберите:"
    ) -> None:
        """Создаёт диалог.

        Args:
            parent: родительский виджет.
            title: заголовок окна.
            options: список кортежей (значение, подпись).
            label: подпись над списком.
        """
        self.result = None
        self.options = options

        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.transient(parent.winfo_toplevel())
        self.top.grab_set()
        self.top.resizable(False, False)

        form = tk.Frame(self.top, bg="white", padx=24, pady=18)
        form.pack(fill=tk.BOTH, expand=True)

        if options:
            tk.Label(form, text=label, bg="white", fg="#5a6478").pack(anchor="w")
            combo = ttk.Combobox(
                form,
                state="readonly",
                width=28,
                values=[label for _, label in options],
            )
            combo.current(0)
            combo.pack(fill=tk.X, pady=(4, 14), ipady=3)
            self.combo = combo
        else:
            tk.Label(
                form, text="Нет доступных вариантов", bg="white", fg="#6b7590"
            ).pack(pady=(0, 12))
            self.combo = None

        buttons = tk.Frame(form, bg="white")
        buttons.pack(fill=tk.X)
        tk.Button(
            buttons,
            text="Выбрать",
            command=self._on_choose,
            cursor="hand2",
            bg="#1a1f33",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            bd=0,
            activebackground="#2e3554",
            activeforeground="white",
        ).pack(side=tk.LEFT, padx=(0, 8), ipadx=14, ipady=5)
        tk.Button(
            buttons,
            text="Отмена",
            command=self.top.destroy,
            cursor="hand2",
            bg="#f5f6fa",
            fg="#1a1f33",
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            bd=0,
            activebackground="#e2e6ee",
        ).pack(side=tk.LEFT, ipadx=10, ipady=5)

    def _on_choose(self) -> None:
        """Сохраняет выбранный вариант и закрывает диалог."""
        if self.combo is not None:
            self.result = self.options[self.combo.current()][0]
        self.top.destroy()

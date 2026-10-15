from __future__ import annotations
"""Универсальный диалог ввода данных: поля, выпадающие списки."""

import tkinter as tk
from tkinter import ttk


class FormDialog:
    """Модальное окно с формой.

    Attributes:
        result: словарь {ключ: значение} или None при отмене.
    """

    def __init__(
        self, parent: tk.Widget, title: str, fields: list, initial: dict | None = None
    ) -> None:
        """Создаёт диалог.

        Args:
            parent: родительский виджет.
            title: заголовок окна.
            fields: список кортежей (ключ, подпись, тип, опции);
                тип — «entry» или «combo», опции — список (значение, подпись).
            initial: начальные значения полей.
        """
        self.result = None
        self.fields = fields
        self.initial = initial or {}
        self.widgets: dict[str, tk.Widget] = {}

        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.transient(parent.winfo_toplevel())
        self.top.grab_set()
        self.top.resizable(False, False)

        form = tk.Frame(self.top, bg="white", padx=24, pady=18)
        form.pack(fill=tk.BOTH, expand=True)

        for key, label, kind, options in fields:
            tk.Label(
                form, text=label, bg="white", fg="#5a6478", font=("Segoe UI", 10)
            ).pack(anchor="w")
            if kind == "combo":
                widget = ttk.Combobox(
                    form,
                    state="readonly",
                    width=28,
                    values=[label for _, label in options],
                )
                values = [value for value, _ in options]
                current = self.initial.get(key)
                if current in values and values:
                    widget.current(values.index(current))
                elif values:
                    widget.current(0)
                widget.pack(fill=tk.X, pady=(2, 10), ipady=3)
                widget.options = options
                self.widgets[key] = widget
            else:
                widget = tk.Entry(
                    form,
                    width=30,
                    relief=tk.FLAT,
                    bg="#f5f6fa",
                    highlightthickness=1,
                    highlightbackground="#dfe4ec",
                    font=("Segoe UI", 10),
                )
                if self.initial.get(key) is not None:
                    widget.insert(0, str(self.initial[key]))
                widget.pack(fill=tk.X, pady=(2, 10), ipady=4)
                self.widgets[key] = widget

        buttons = tk.Frame(form, bg="white")
        buttons.pack(fill=tk.X, pady=(6, 0))
        tk.Button(
            buttons,
            text="Сохранить",
            command=self._on_save,
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

        self.top.wait_visibility()
        self.top.focus_set()

    def _on_save(self) -> None:
        """Собирает значения полей и закрывает диалог."""
        data = {}
        for key, _label, kind, _options in self.fields:
            widget = self.widgets[key]
            if kind == "combo":
                index = widget.current()
                if index < 0:
                    data[key] = None
                else:
                    data[key] = widget.options[index][0]
            else:
                data[key] = widget.get().strip()
        self.result = data
        self.top.destroy()

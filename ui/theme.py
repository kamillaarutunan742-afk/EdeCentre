"""Единая тема оформления в стиле прототипа EduCenter."""

import tkinter as tk
from tkinter import ttk

BG_CONTENT = "#f5f6fa"
BG_SIDEBAR = "#1a1f33"
SIDEBAR_ACTIVE = "#2e3554"
TEXT_MUTED = "#9aa7bd"
CARD_BG = "#ffffff"
FONT_BASE = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_CARD_VALUE = ("Segoe UI", 22, "bold")

GREEN = "#22a06b"
RED = "#e5484d"
AMBER_BG = "#fdf3d7"
RED_BG = "#fdecec"


def apply_theme(root: tk.Tk) -> None:
    """Настраивает стили ttk-виджетов для всего приложения.

    Args:
        root: главное окно.
    """
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure("TFrame", background=BG_CONTENT)
    style.configure("Card.TFrame", background=CARD_BG)
    style.configure("TLabel", background=BG_CONTENT, font=FONT_BASE)

    style.configure(
        "Primary.TButton",
        font=FONT_BOLD,
        background="#1a1f33",
        foreground="white",
        padding=(14, 8),
        borderwidth=0,
        cursor="hand2",
    )
    style.map(
        "Primary.TButton",
        background=[("active", "#2e3554"), ("pressed", "#2e3554")],
    )
    style.configure(
        "Secondary.TButton",
        font=FONT_BASE,
        background="#eef1f6",
        foreground="#1a1f33",
        padding=(10, 6),
        borderwidth=0,
        cursor="hand2",
    )
    style.map("Secondary.TButton", background=[("active", "#dfe4ec")])

    style.configure(
        "Treeview",
        font=FONT_BASE,
        rowheight=32,
        background=CARD_BG,
        fieldbackground=CARD_BG,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        font=FONT_BOLD,
        background="#f5f6fa",
        foreground="#5a6478",
        relief="flat",
        padding=6,
    )
    style.map(
        "Treeview",
        background=[("selected", "#e8edfb")],
        foreground=[("selected", "#1a1f33")],
    )
    style.configure("TEntry", padding=6)
    style.configure("TCombobox", padding=6)


def make_header(parent, title="", button_text=None, command=None):
    """Строка раздела: кнопка действия справа, без дублирующего заголовка.

    Args:
        parent: родительский виджет.
        title: не используется (заголовок рисует главное окно), оставлен
            для совместимости старых вызовов.
        button_text: подпись кнопки действия.
        command: обработчик кнопки.

    Returns:
        Контейнер заголовка.
    """
    header = tk.Frame(parent, bg="white", padx=20, pady=14)
    header.pack(fill=tk.X)
    if button_text and command is not None:
        tk.Button(
            header,
            text=button_text,
            command=command,
            cursor="hand2",
            bg="#1a1f33",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            bd=0,
            activebackground="#2e3554",
            activeforeground="white",
        ).pack(side=tk.RIGHT)
    return header

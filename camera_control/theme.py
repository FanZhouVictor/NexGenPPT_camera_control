import sys
import customtkinter as ctk
from customtkinter import ThemeManager

PRIMARY = "#2563EB"
PRIMARY_HOVER = "#1D4ED8"
PRIMARY_SUBTLE = "#E8F0FE"
PRIMARY_PICKED = "#9DBBF7"   # the chosen answer in a row of choices; dark text stays readable on it
ON_PRIMARY = "#FFFFFF"

SIDEBAR = "#EEF4FE"
SIDEBAR_HOVER = "#DCE7FC"

BACKGROUND = "#F8FAFD"
CARD = "#FFFFFF"
BORDER = "#E1E8F2"
TEXT = "#1E293B"
TEXT_MUTED = "#64748B"

STATUS_UNKNOWN = "#94A3B8"

SUCCESS = "#248A3D"
WARNING = "#C93400"
ERROR = "#D70015"
SUCCESS_FILL = "#34C759"
WARNING_FILL = "#FF9500"
ERROR_FILL = "#FF3B30"
SUCCESS_TINT = "#E1F7E6"
WARNING_TINT = "#FFEFD9"
ERROR_TINT = "#FFE2E0"


def apply_theme():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    theme = ThemeManager.theme
    theme["CTk"]["fg_color"] = [BACKGROUND] * 2
    theme["CTkToplevel"]["fg_color"] = [BACKGROUND] * 2
    theme["CTkFrame"].update(fg_color=[CARD] * 2, border_color=[BORDER] * 2)
    theme["CTkLabel"]["text_color"] = [TEXT] * 2
    theme["CTkButton"].update(
        corner_radius=8,
        fg_color=[PRIMARY] * 2,
        hover_color=[PRIMARY_HOVER] * 2,
        text_color=[ON_PRIMARY] * 2,
    )
    if sys.platform == "darwin":
        theme["CTkFont"]["family"] = ".AppleSystemUIFont"  # SF Pro
    elif sys.platform == "win32":
        theme["CTkFont"]["family"] = "Segoe UI"


def font(size=15, bold=False):
    return ctk.CTkFont(size=size, weight="bold" if bold else "normal")


def mono_font(size=12):
    family = "Menlo" if sys.platform == "darwin" else "Consolas"
    return ctk.CTkFont(family=family, size=size)

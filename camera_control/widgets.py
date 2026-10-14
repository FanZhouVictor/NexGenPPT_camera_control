# Small building blocks shared by every page.

import customtkinter as ctk
from camera_control import theme


def section_label(parent, text, first=False):
    ctk.CTkLabel(
        parent, text=text, font=theme.font(12, bold=True), text_color=theme.TEXT_MUTED, anchor="w",
    ).pack(fill="x", pady=(0 if first else 20, 8))


def form_row(parent, label, detail=False):
    # One line of a form: the label on the left, its controls packed into the returned frame.
    # A detail row is a follow-up to the question above it.
    row = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(
        row, text=label, width=104, anchor="w", font=theme.font(13 if detail else 14),
        text_color=theme.TEXT_MUTED if detail else theme.TEXT,
    ).pack(side="left")
    return row


def choice_buttons(row, values, on_change):
    # Pick one of a few answers. Nothing is picked to start with.
    buttons = ctk.CTkSegmentedButton(
        row, values=values, height=28, font=theme.font(13), command=lambda _: on_change(),
        fg_color=theme.PRIMARY_SUBTLE, unselected_color=theme.PRIMARY_SUBTLE,
        unselected_hover_color=theme.SIDEBAR_HOVER, selected_color=theme.PRIMARY_PICKED,
        selected_hover_color=theme.PRIMARY_PICKED, text_color=theme.TEXT, text_color_disabled=theme.TEXT_MUTED,
    )
    buttons.pack(side="left")
    return buttons


def row_entry(row, placeholder, on_change, width=None):
    entry = ctk.CTkEntry(row, placeholder_text=placeholder, height=28, width=width or 140, font=theme.font(13))
    entry.pack(side="left", fill="x" if width is None else "none", expand=width is None)
    entry.bind("<KeyRelease>", lambda _: on_change())
    return entry


def row_menu(row, values, on_change, width=96):
    menu = ctk.CTkOptionMenu(
        row, values=values, width=width, height=28, font=theme.font(13), dropdown_font=theme.font(13),
        fg_color=theme.PRIMARY_SUBTLE, button_color=theme.SIDEBAR_HOVER, button_hover_color=theme.SIDEBAR_HOVER,
        text_color=theme.TEXT, command=lambda _: on_change(),
    )
    menu.pack(side="left", padx=(6, 0))
    return menu


def row_text(row, text):
    ctk.CTkLabel(row, text=text, font=theme.font(13), text_color=theme.TEXT_MUTED).pack(side="left", padx=6)


def secondary_button(parent, text, command, **options):
    return ctk.CTkButton(
        parent, text=text, command=command, font=theme.font(options.pop("size", 13), bold=True),
        fg_color=theme.PRIMARY_SUBTLE, hover_color=theme.SIDEBAR_HOVER, text_color=theme.PRIMARY,
        **options,
    )


class StepList(ctk.CTkFrame):
    # Numbered steps; each one shows as waiting, current (filled) or done (✓).

    def __init__(self, master, steps):
        super().__init__(master, fg_color="transparent")
        self.marks = []
        for number, text in enumerate(steps, start=1):
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", pady=4)
            circle = ctk.CTkFrame(row, width=30, height=30, corner_radius=15)
            circle.pack(side="left")
            mark = ctk.CTkLabel(circle, text=str(number), width=0, height=0, font=theme.font(13, bold=True))
            mark.place(relx=0.5, rely=0.5, anchor="center")
            ctk.CTkLabel(
                row, text=text, font=theme.font(14), anchor="w", justify="left", wraplength=250,
            ).pack(side="left", fill="x", padx=(12, 0))
            self.marks.append((circle, mark))
        self.show(done=0)

    def show(self, done, current=None):
        for index, (circle, mark) in enumerate(self.marks):
            if index < done:
                circle.configure(fg_color=theme.PRIMARY_SUBTLE)
                mark.configure(text="✓", text_color=theme.SUCCESS)
            elif index == current:
                circle.configure(fg_color=theme.PRIMARY)
                mark.configure(text=str(index + 1), text_color=theme.ON_PRIMARY)
            else:
                circle.configure(fg_color=theme.PRIMARY_SUBTLE)
                mark.configure(text=str(index + 1), text_color=theme.PRIMARY)


class StatusRow(ctk.CTkFrame):
    # One result line: a status circle, a bold title and a detail underneath.
    MARKS = {
        "waiting": ("", theme.PRIMARY_SUBTLE, theme.PRIMARY),
        "running": ("…", theme.PRIMARY, theme.ON_PRIMARY),
        "ok": ("✓", theme.SUCCESS_TINT, theme.SUCCESS_FILL),
        "warning": ("!", theme.WARNING_TINT, theme.WARNING_FILL),
        "problem": ("✕", theme.ERROR_TINT, theme.ERROR_FILL),
    }

    def __init__(self, master, title):
        super().__init__(master, fg_color="transparent")
        self.circle = ctk.CTkFrame(self, width=30, height=30, corner_radius=15)
        self.circle.pack(side="left", anchor="n")
        self.mark = ctk.CTkLabel(self.circle, text="", width=0, height=0, font=theme.font(13, bold=True))
        self.mark.place(relx=0.5, rely=0.5, anchor="center")
        self.text = ctk.CTkFrame(self, fg_color="transparent")
        self.text.pack(side="left", fill="x", expand=True, padx=(12, 0))
        ctk.CTkLabel(self.text, text=title, font=theme.font(14, bold=True), anchor="w").pack(fill="x")
        self.detail = ctk.CTkLabel(
            self.text, text="", font=theme.font(13), text_color=theme.TEXT_MUTED,
            anchor="w", justify="left", wraplength=200,
        )
        self.detail.pack(fill="x")

    def show(self, state, detail):
        symbol, background, color = self.MARKS[state]
        self.circle.configure(fg_color=background)
        self.mark.configure(text=symbol, text_color=color)
        self.detail.configure(text=detail)

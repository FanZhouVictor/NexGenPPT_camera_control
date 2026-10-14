# Small building blocks shared by every page.

import customtkinter as ctk
from camera_control import theme


def section_label(parent, text, first=False):
    ctk.CTkLabel(
        parent, text=text, font=theme.font(12, bold=True), text_color=theme.TEXT_MUTED, anchor="w",
    ).pack(fill="x", pady=(0 if first else 20, 8))


def labeled_entry(parent, label, placeholder, on_change):
    ctk.CTkLabel(parent, text=label, font=theme.font(14), anchor="w").pack(fill="x")
    entry = ctk.CTkEntry(parent, placeholder_text=placeholder, height=38, font=theme.font(14))
    entry.pack(fill="x", pady=(2, 12))
    entry.bind("<KeyRelease>", lambda _: on_change())
    return entry


def labeled_choice(parent, label, on_change):
    ctk.CTkLabel(parent, text=label, font=theme.font(14), anchor="w").pack(fill="x")
    box = ctk.CTkComboBox(
        parent, values=[], state="readonly", height=38, font=theme.font(14),
        command=lambda _: on_change(),
    )
    box.pack(fill="x", pady=(2, 12))
    return box


def set_choices(box, values):
    box.configure(values=values)
    if box.get() not in values:
        box.set(values[0])


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

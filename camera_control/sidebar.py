# Sidebar: pick a workflow, see today's captures and the camera status.

import customtkinter as ctk
from camera_control import __version__, theme

TODAY_SHOWN = 8   # most recent captures listed under TODAY


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, workflows, on_select, on_check_camera, on_open_folder):
        # workflows: list of (key, label). on_select(key) runs when one is clicked.
        # on_open_folder(path) runs when one of today's captures is clicked.
        super().__init__(master, width=260, corner_radius=0, fg_color=theme.SIDEBAR)
        self.pack_propagate(False)
        self.on_select = on_select
        self.on_open_folder = on_open_folder
        self.on_check_camera = on_check_camera

        ctk.CTkLabel(
            self, text="NexGenPPT\nCamera Control", font=theme.font(21, bold=True), anchor="w", justify="left",
        ).pack(fill="x", padx=20, pady=(22, 0))
        ctk.CTkLabel(
            self, text=f"version {__version__}", font=theme.font(12),
            text_color=theme.TEXT_MUTED, anchor="w",
        ).pack(fill="x", padx=20)

        self._heading("CAPTURE")
        self.nav_buttons = {}
        for key, label in workflows:
            button = ctk.CTkButton(
                self, text=label, anchor="w", height=44, font=theme.font(16, bold=True),
                command=lambda k=key: self.on_select(k),
            )
            button.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[key] = button

        self._heading("TODAY")
        self.today = ctk.CTkFrame(self, fg_color="transparent")
        self.today.pack(fill="x", padx=20)
        self.show_today([])

        self._build_camera_box()

    def _heading(self, text):
        ctk.CTkLabel(
            self, text=text, font=theme.font(12, bold=True),
            text_color=theme.TEXT_MUTED, anchor="w",
        ).pack(fill="x", padx=20, pady=(26, 6))

    def _build_camera_box(self):
        box = ctk.CTkFrame(self, border_width=1, corner_radius=10)
        box.pack(side="bottom", fill="x", padx=12, pady=16)

        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(12, 8))
        self.camera_dot = ctk.CTkLabel(row, text="●", font=theme.font(16))
        self.camera_dot.pack(side="left", anchor="n")
        self.camera_text = ctk.CTkLabel(
            row, font=theme.font(14, bold=True), anchor="w", justify="left", wraplength=180,
        )
        self.camera_text.pack(side="left", padx=(8, 0))

        self.camera_button = ctk.CTkButton(
            box, height=38, font=theme.font(14, bold=True), command=self.on_check_camera,
            fg_color=theme.PRIMARY_SUBTLE, hover_color=theme.SIDEBAR_HOVER, text_color=theme.PRIMARY,
        )
        self.camera_button.pack(fill="x", padx=14, pady=(0, 14))
        self.show_camera(None)

    def show_camera(self, check):
        if check is None:
            color, text, button = theme.STATUS_UNKNOWN, "Camera not checked yet", "Check camera"
        elif check.state == "ready":
            color, text, button = theme.SUCCESS_FILL, f"Camera ready · {check.checked_at}", "Check again"
        elif check.state == "warning":
            count = len(check.settings_failed)
            color, text, button = theme.WARNING_FILL, f"Camera ready · {count} to set by hand", "View check"
        else:
            color, text, button = theme.ERROR_FILL, "Camera problem", "View problem"
        self.camera_dot.configure(text_color=color)
        self.camera_text.configure(text=text)
        self.camera_button.configure(text=button)

    def show_today(self, captures, todays_folder=None):
        # captures: (time, name, folder), newest first. Clicking one opens its folder;
        # the link under them opens todays_folder, which holds all of today's captures.
        for child in self.today.winfo_children():
            child.destroy()
        if not captures:
            ctk.CTkLabel(
                self.today, text="No captures yet.", font=theme.font(14), text_color=theme.TEXT_MUTED, anchor="w",
            ).pack(fill="x")
            return
        for time, name, folder in captures[:TODAY_SHOWN]:
            self._capture_row(time, name, folder)
        hidden = len(captures) - TODAY_SHOWN
        count = "1 capture" if len(captures) == 1 else f"{len(captures)} captures"
        total = f"{count} today" + (f" · {hidden} more not shown" if hidden > 0 else "")
        ctk.CTkLabel(
            self.today, text=total, font=theme.font(12), text_color=theme.TEXT_MUTED, anchor="w",
        ).pack(fill="x", padx=6, pady=(6, 0))
        if todays_folder:
            link = ctk.CTkLabel(
                self.today, text="Open today's folder", font=theme.font(12, bold=True), text_color=theme.PRIMARY,
                anchor="w", cursor="hand2",
            )
            link.pack(fill="x", padx=6)
            link.bind("<Button-1>", lambda _: self.on_open_folder(todays_folder))

    def _capture_row(self, time, name, folder):
        row = ctk.CTkFrame(self.today, fg_color="transparent", corner_radius=6, cursor="hand2")
        row.pack(fill="x", pady=1)
        parts = [
            row,
            ctk.CTkLabel(row, text=time, width=44, font=theme.font(13), text_color=theme.TEXT_MUTED, anchor="w"),
            ctk.CTkLabel(row, text=name, font=theme.font(13), text_color=theme.PRIMARY, anchor="w"),
        ]
        parts[1].pack(side="left", padx=(6, 0))
        parts[2].pack(side="left", fill="x")

        def hover(on):
            row.configure(fg_color=theme.SIDEBAR_HOVER if on else "transparent")

        def left(event):
            # Moving between the row's own labels also counts as leaving one of them.
            inside = row.winfo_containing(event.x_root, event.y_root)
            hover(inside is not None and str(inside).startswith(str(row)))

        for part in parts:
            part.configure(cursor="hand2")
            part.bind("<Button-1>", lambda _: self.on_open_folder(folder))
            part.bind("<Enter>", lambda _: hover(True))
            part.bind("<Leave>", left)

    def lock(self, locked):
        state = "disabled" if locked else "normal"
        for button in (*self.nav_buttons.values(), self.camera_button):
            button.configure(state=state)

    def highlight(self, key):
        # Show which workflow is selected: blue button on the light sidebar.
        for k, button in self.nav_buttons.items():
            if k == key:
                button.configure(fg_color=theme.PRIMARY, hover_color=theme.PRIMARY, text_color=theme.ON_PRIMARY)
            else:
                button.configure(fg_color=theme.SIDEBAR, hover_color=theme.SIDEBAR_HOVER, text_color=theme.TEXT)

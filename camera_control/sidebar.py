# Sidebar: pick a workflow, see today's captures and the camera status.

import customtkinter as ctk
from camera_control import __version__, theme

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, workflows, on_select, on_check_camera):
        # workflows: list of (key, label). on_select(key) runs when one is clicked.
        super().__init__(master, width=260, corner_radius=0, fg_color=theme.SIDEBAR)
        self.pack_propagate(False)
        self.on_select = on_select
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
        ctk.CTkLabel(
            self, text="No captures yet.", font=theme.font(14),
            text_color=theme.TEXT_MUTED, anchor="w",
        ).pack(fill="x", padx=20)

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

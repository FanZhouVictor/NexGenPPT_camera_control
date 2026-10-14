# Main window: sidebar on the left, the selected page on the right.

import customtkinter as ctk
from camera_control import __version__, theme
from camera_control.camera_setup import CameraSetupPage
from camera_control.sidebar import Sidebar
from camera_control.workflows import WORKFLOWS

CAMERA_SETUP = "camera_setup"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"NexGenPPT Camera Control {__version__}")
        # The tallest page (One specimen, paused for the rotation) needs 1024x776.
        self.geometry("1100x800")
        self.minsize(1024, 780)

        # Kept for the whole session, so leaving the camera page doesn't lose it.
        self.camera_check = None

        self.sidebar = Sidebar(
            self, [(w.key, w.label) for w in WORKFLOWS], self.select, lambda: self.select(CAMERA_SETUP),
        )
        self.sidebar.pack(side="left", fill="y")

        main = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        main.pack(side="left", fill="both", expand=True, padx=32, pady=26)

        self.title_label = ctk.CTkLabel(main, font=theme.font(26, bold=True), anchor="w")
        self.title_label.pack(fill="x")
        self.description_label = ctk.CTkLabel(
            main, font=theme.font(15), text_color=theme.TEXT_MUTED, anchor="w"
        )
        self.description_label.pack(fill="x", pady=(2, 18))

        # Packed before the card, so a tall page shrinks the card and never pushes the buttons off the window.
        self.action_bar = ctk.CTkFrame(main, fg_color="transparent")
        self.action_bar.pack(side="bottom", fill="x", pady=(18, 0))

        self.page_card = ctk.CTkFrame(main, border_width=1, corner_radius=12)
        self.page_card.pack(fill="both", expand=True)

        self.page = None
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.select(CAMERA_SETUP)
        self.after(100, self.bring_to_front)

    def bring_to_front(self):
        # Opens in front of other windows, then behaves normally.
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def select(self, key):
        self.sidebar.highlight(key)
        for child in (*self.page_card.winfo_children(), *self.action_bar.winfo_children()):
            child.destroy()

        if key == CAMERA_SETUP:
            self._set_heading("Camera setup", "Do this at the start of every session, before taking photos.")
            self.page = CameraSetupPage(
                self.page_card, self.action_bar, self.sidebar.lock,
                self.camera_check, self.camera_checked, lambda: self.select(WORKFLOWS[0].key),
            )
        else:
            workflow = next(w for w in WORKFLOWS if w.key == key)
            self._set_heading(workflow.label, workflow.description)
            if workflow.page:
                self.page = workflow.page(self.page_card, self.action_bar, self.sidebar.lock, self.camera_ready())
            else:
                self._show_placeholder(workflow.label)
                return
        self.page.pack(fill="both", expand=True, padx=8, pady=8)

    def _set_heading(self, title, description):
        self.title_label.configure(text=title)
        self.description_label.configure(text=description)

    def _show_placeholder(self, label):
        self.page = None
        ctk.CTkLabel(
            self.page_card, text=f"The {label.lower()} form will go here.",
            font=theme.font(15), text_color=theme.TEXT_MUTED,
        ).pack(expand=True)
        ctk.CTkButton(
            self.action_bar, text="Take photos", height=56, width=220, font=theme.font(18, bold=True),
            state="disabled",
        ).pack(side="right")

    def camera_checked(self, check):
        self.camera_check = check
        self.sidebar.show_camera(check)

    def camera_ready(self):
        return self.camera_check is not None and self.camera_check.camera_ready

    def close(self):
        if self.page:
            self.page.stop()
        self.destroy()


def main():
    theme.apply_theme()
    App().mainloop()

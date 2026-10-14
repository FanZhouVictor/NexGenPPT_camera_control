# Camera setup page: the steps to do on the rig, then the camera check and its result.

import sys

import customtkinter as ctk
from camera_control import theme
from camera_control.camera_check import JOB, SETTINGS_TOTAL, CameraCheck
from camera_control.capture import start_run
from camera_control.diagnostics import DiagnosticsWindow
from camera_control.widgets import StatusRow, secondary_button, section_label

SETUP_STEPS = [
    "Turn on the light box and wait 20 minutes.",
    "Turn the camera dial to M.",
    "Set the lens focus switch to MF.",
    "Set the lens stabilizer switch to OFF.",
    "Check the zoom is taped at 50 mm.",
    "Check the battery and SD card are in.",
    "With the camera off, plug in the USB-C cable.",
    "Turn the camera on.",
    "Close EOS Utility if it is open.",
    "Focus: in Live View, zoom in 10× and turn the focus ring until sharp.",
]
if sys.platform == "win32":
    SETUP_STEPS.insert(9, "Open digiCamControl and leave it open.")


class CameraSetupPage(ctk.CTkFrame):
    def __init__(self, master, action_bar, on_busy, last_check, on_checked, on_start_capturing):
        # last_check belongs to the app, so it survives leaving this page.
        super().__init__(master, fg_color="transparent")
        self.on_busy = on_busy
        self.check = last_check
        self.on_checked = on_checked
        self.on_start_capturing = on_start_capturing
        self.run = None
        self.cancelled = False
        self.diagnostics_window = None
        self.columnconfigure(0, weight=3, uniform="column")
        self.columnconfigure(1, weight=2, uniform="column")
        self.rowconfigure(0, weight=1)

        steps = ctk.CTkFrame(self, fg_color="transparent")
        steps.grid(row=0, column=0, sticky="nsew", padx=(28, 14), pady=24)
        section_label(steps, "BEFORE YOU START", first=True)
        ctk.CTkLabel(
            steps, text="Do these in order, then press Check camera.", font=theme.font(13),
            text_color=theme.TEXT_MUTED, anchor="w",
        ).pack(fill="x", pady=(0, 8))
        for number, text in enumerate(SETUP_STEPS, start=1):
            self._step_line(steps, number, text)

        results = ctk.CTkFrame(self, fg_color="transparent")
        results.grid(row=0, column=1, sticky="nsew", padx=(14, 28), pady=24)
        section_label(results, "CAMERA CHECK", first=True)
        self.camera_row = StatusRow(results, "Camera connected")
        self.settings_row = StatusRow(results, "Settings applied")
        self.log_row = StatusRow(results, "Diagnostics")
        for row in (self.camera_row, self.settings_row, self.log_row):
            row.pack(fill="x", pady=6)
        self.diagnostics_button = secondary_button(
            self.log_row.text, "View diagnostics", self._open_diagnostics, width=130, height=28,
        )
        self.status_label = ctk.CTkLabel(
            results, text="", font=theme.font(14), anchor="w", justify="left", wraplength=240,
        )
        self.status_label.pack(fill="x", pady=(20, 0))

        self.main_button = ctk.CTkButton(
            action_bar, height=56, width=220, font=theme.font(18, bold=True), command=self._main_clicked,
        )
        self.main_button.pack(side="right")
        self.second_button = secondary_button(
            action_bar, "", self._second_clicked, width=150, height=56, size=16,
        )

        if self.check:
            self._show_check()
        else:
            self._show_not_checked()

    def _step_line(self, parent, number, text):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3)
        ctk.CTkLabel(
            row, text=f"{number}.", width=26, font=theme.font(14, bold=True), text_color=theme.PRIMARY, anchor="e",
        ).pack(side="left", anchor="n")
        ctk.CTkLabel(
            row, text=text, font=theme.font(14), anchor="w", justify="left", wraplength=320,
        ).pack(side="left", padx=(8, 0))

    def _set_status(self, text, color=None):
        self.status_label.configure(text=text, text_color=color or theme.TEXT)

    # What the page shows

    def _show_not_checked(self):
        for row in (self.camera_row, self.settings_row, self.log_row):
            row.show("waiting", "Not checked yet.")
        self.diagnostics_button.pack_forget()
        self.second_button.pack_forget()
        self.main_button.configure(text="Check camera", state="normal")
        self._set_status("Go through the steps on the left, then check. Takes about a minute.", theme.TEXT_MUTED)

    def _show_progress(self):
        check = self.check
        if check.camera:
            self.camera_row.show("ok", check.camera)
            if check.settings_done < SETTINGS_TOTAL:
                self.settings_row.show("running", f"Applying {check.settings_done} of {SETTINGS_TOTAL}…")
            else:
                self.settings_row.show("running", "Reading the values back…")
        else:
            self.camera_row.show("running", "Looking for the Canon EOS RP…")

    def _show_check(self):
        check = self.check
        self.second_button.pack_forget()
        self.diagnostics_button.pack_forget()

        if check.camera:
            self.camera_row.show("ok", check.camera)
        else:
            self.camera_row.show("problem", "Could not connect.")

        if check.state == "problem":
            if check.camera:
                self.settings_row.show("problem", f"Stopped after {check.settings_set} of {SETTINGS_TOTAL}.")
            else:
                self.settings_row.show("waiting", "Not applied.")
        elif check.settings_failed:
            self.settings_row.show(
                "warning", f"{check.settings_set} of {SETTINGS_TOTAL} set. Not set: {', '.join(check.settings_failed)}.",
            )
        else:
            on_camera = len(check.settings_on_camera)
            if on_camera:
                kept = "1 is" if on_camera == 1 else f"{on_camera} are"
                self.settings_row.show("ok", f"{check.settings_set} set. {kept} kept on the camera itself.")
            else:
                self.settings_row.show("ok", f"All {SETTINGS_TOTAL} settings set.")

        self.log_row.show("ok" if check.log_path else "waiting", f"Checked at {check.checked_at}.")
        self.diagnostics_button.pack(anchor="w", pady=(4, 0))

        if check.state == "problem":
            if check.cancelled:
                self._set_status("Check cancelled. Press Check again when you're ready.", theme.TEXT_MUTED)
            else:
                self._set_status(f"{check.error}\nFix this, then check again.", theme.ERROR)
            self.main_button.configure(text="Check again", state="normal")
            return
        if check.state == "warning":
            self._set_status(
                "Camera is ready, but some settings could not be set. Set them by hand on the camera.",
                theme.WARNING,
            )
        else:
            self._set_status("Camera is ready. You can start taking photos.", theme.SUCCESS)
        self.main_button.configure(text="Start capturing", state="normal")
        self.second_button.configure(text="Check again")
        self.second_button.pack(side="right", padx=(0, 12))

    def _open_diagnostics(self):
        if self.diagnostics_window and self.diagnostics_window.winfo_exists():
            self.diagnostics_window.focus_force()
        else:
            self.diagnostics_window = DiagnosticsWindow(self, self.check)

    # Running the camera check

    def _main_clicked(self):
        if self.check and self.check.camera_ready:
            self.on_start_capturing()
        else:
            self._start()

    def _second_clicked(self):
        if self.run:
            self.stop()
        else:
            self._start()

    def _start(self):
        self.check = CameraCheck()
        self.cancelled = False
        self._show_not_checked()
        self.on_busy(True)
        self._show_progress()
        self._set_status("Checking the camera. Don't touch it until this finishes.")
        self.main_button.configure(text="Checking…", state="disabled")
        self.second_button.configure(text="Cancel")
        self.second_button.pack(side="right", padx=(0, 12))
        try:
            self.run = start_run(JOB, [])
        except OSError as error:
            self.check.error = f"Could not start the camera check: {error}"
            self._finish(exit_code=1)
            return
        self._poll()

    def _poll(self):
        for line in self.run.new_lines():
            if line is None:
                self._finish(self.run.exit_code)
                return
            self.check.read_line(line)
            self._show_progress()
        self.after(100, self._poll)

    def _finish(self, exit_code):
        self.run = None
        self.check.finish(exit_code, cancelled=self.cancelled)
        self.on_busy(False)
        self.on_checked(self.check)
        self._show_check()

    def stop(self):
        if self.run:
            self.cancelled = True
            self.run.stop()

# Pop-up with the details of a camera check: summary, each setting, and the full log.

from pathlib import Path

import customtkinter as ctk
from camera_control import theme
from camera_control.widgets import secondary_button, section_label

SUMMARY = {
    "ready": ("Camera is ready.", theme.SUCCESS),
    "warning": ("Camera is ready, but some settings could not be set.", theme.WARNING),
    "problem": ("Camera check did not pass.", theme.ERROR),
}


class DiagnosticsWindow(ctk.CTkToplevel):
    def __init__(self, master, check):
        super().__init__(master)
        self.title("Camera check diagnostics")
        self.geometry("640x620")
        self.minsize(520, 480)
        self.transient(master.winfo_toplevel())
        self.log_text = self._read_log(check.log_path)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=20)

        # Packed first so the buttons keep their place when the log fills the window.
        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", pady=(14, 0))
        ctk.CTkButton(
            buttons, text="Close", width=110, height=38, font=theme.font(14, bold=True), command=self.destroy,
        ).pack(side="right")
        self.copy_button = secondary_button(buttons, "Copy log", self._copy_log, width=110, height=38, size=14)
        self.copy_button.pack(side="right", padx=(0, 10))

        ctk.CTkLabel(body, text="Camera check diagnostics", font=theme.font(20, bold=True), anchor="w").pack(fill="x")
        details = " · ".join(part for part in (f"Checked at {check.checked_at}", check.camera) if part)
        ctk.CTkLabel(body, text=details, font=theme.font(13), text_color=theme.TEXT_MUTED, anchor="w").pack(fill="x")
        summary, color = SUMMARY[check.state]
        if check.error:
            summary = check.error
        ctk.CTkLabel(
            body, text=summary, font=theme.font(14, bold=True), text_color=color,
            anchor="w", justify="left", wraplength=580,
        ).pack(fill="x", pady=(10, 0))

        failed = [setting for setting in check.settings if setting.label in check.settings_failed]
        if failed:
            section_label(body, "SET THESE BY HAND ON THE CAMERA")
            for setting in failed:
                self._setting_row(body, setting)

        section_label(body, "FULL LOG")
        log_box = ctk.CTkTextbox(body, font=theme.mono_font(12), border_width=1, corner_radius=8, wrap="none")
        log_box.pack(fill="both", expand=True)
        log_box.insert("1.0", self.log_text)
        log_box.configure(state="disabled")

        self.after(100, self.focus_force)

    def _setting_row(self, parent, setting):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=1)
        ctk.CTkLabel(
            row, text="!", width=20, font=theme.font(14, bold=True), text_color=theme.WARNING_FILL,
        ).pack(side="left")
        ctk.CTkLabel(row, text=f"{setting.label}: {setting.value}", font=theme.font(14), anchor="w").pack(
            side="left", padx=(6, 0),
        )

    def _read_log(self, path):
        if not path:
            return "No log was saved."
        try:
            return Path(path).read_text()
        except OSError as error:
            return f"Could not read the log at {path}: {error}"

    def _copy_log(self):
        self.clipboard_clear()
        self.clipboard_append(self.log_text)
        self.copy_button.configure(text="Copied")
        self.after(1500, lambda: self.copy_button.configure(text="Copy log"))

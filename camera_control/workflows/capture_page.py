# Base page for a capture workflow: fields on the left, steps and result on the right,
# and the buttons that run the workflow's capture job.
#
# A workflow subclasses CapturePage and fills in:
#   job            capture job name, a key of capture.JOBS
#   steps          what happens, shown as a numbered list
#   build_fields   the inputs, placed in `parent`
#   validate       job arguments, output name and summary, or a message saying what to fix
#   read_output    move the steps along as the job prints its progress
#   build_guide    optional: replace the numbered step list (see guide_title)

import datetime
import re

import customtkinter as ctk
from camera_control import theme
from camera_control.capture import start_run
from camera_control.system import open_in_file_browser
from camera_control.widgets import StepList, secondary_button, section_label


class CapturePage(ctk.CTkFrame):
    job = None
    steps = []
    fields_title = "DETAILS"
    guide_title = "WHAT HAPPENS"

    def __init__(self, master, action_bar, on_busy, camera_ready):
        super().__init__(master, fg_color="transparent")
        self.on_busy = on_busy
        self.camera_ready = camera_ready
        self.run = None
        # The form takes the spare width; the guide column stays as wide as its drawing.
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, minsize=342)
        self.rowconfigure(0, weight=1)

        fields = ctk.CTkFrame(self, fg_color="transparent")
        fields.grid(row=0, column=0, sticky="nsew", padx=(28, 14), pady=24)
        section_label(fields, self.fields_title, first=True)
        self.build_fields(fields)

        side = ctk.CTkFrame(self, fg_color="transparent")
        side.grid(row=0, column=1, sticky="nsew", padx=(14, 28), pady=24)
        section_label(side, self.guide_title, first=True)
        self.guide = self.build_guide(side)
        self.guide.pack(fill="x")

        section_label(side, "SAVED AS")
        self.output_label = ctk.CTkLabel(
            side, font=theme.font(15, bold=True), anchor="w", justify="left", wraplength=290,
        )
        self.output_label.pack(fill="x")
        self.folder_label = ctk.CTkLabel(side, font=theme.font(13), text_color=theme.TEXT_MUTED, anchor="w")
        self.folder_label.pack(fill="x")

        self.status_label = ctk.CTkLabel(
            side, text="", font=theme.font(14), anchor="w", justify="left", wraplength=290,
        )
        self.status_label.pack(fill="x", pady=(20, 0))

        self.main_button = ctk.CTkButton(
            action_bar, text="Take photos", height=56, width=220, font=theme.font(18, bold=True),
            command=self._main_clicked,
        )
        self.main_button.pack(side="right")
        self.cancel_button = secondary_button(
            action_bar, "Cancel", self._cancel, width=120, height=56, size=16,
        )
        # Shown beside the main button once a capture has saved something.
        self.open_folder_button = secondary_button(action_bar, "Open folder", None, width=130, height=56, size=16)
        # What is about to be photographed, next to the button that starts it.
        check = ctk.CTkFrame(action_bar, fg_color="transparent")
        check.pack(side="left", fill="y")
        self.summary_title = ctk.CTkLabel(
            check, text="", font=theme.font(11, bold=True), text_color=theme.TEXT_MUTED, anchor="w", height=16,
        )
        self.summary_title.pack(fill="x")
        self.summary_label = ctk.CTkLabel(
            check, text="", font=theme.font(13, bold=True), anchor="w", justify="left", wraplength=400,
        )
        self.summary_label.pack(fill="x")

        self.refresh()

    # For subclasses

    def build_fields(self, parent):
        raise NotImplementedError

    def build_guide(self, parent):
        # Anything with show(done, current=None) that follows the steps.
        return StepList(parent, self.steps)

    def validate(self):
        # Return (job_args, output_name, summary) when the inputs are complete, otherwise what to fix.
        raise NotImplementedError

    def read_output(self, line):
        pass

    def input_widgets(self):
        return []

    def show_progress(self, done, current, status):
        self.guide.show(done, current)
        self.set_status(status)

    def wait_for_continue(self, done, current, status):
        # The job is waiting for Enter: the main button becomes Continue.
        self.show_progress(done, current, status)
        self.main_button.configure(text="Continue", state="normal")

    def set_status(self, text, color=None):
        self.status_label.configure(text=text, text_color=color or theme.TEXT)

    # Form state

    def refresh(self):
        # Call whenever an input changes.
        if self.run:
            return
        self.guide.show(done=0)
        if self.camera_ready:
            self.set_status("")
        else:
            self.set_status("Check the camera before taking photos. Use Check camera in the sidebar.", theme.WARNING)
        self.open_folder_button.pack_forget()
        result = self.validate()
        if isinstance(result, str):
            self.output_label.configure(text=result, text_color=theme.TEXT_MUTED)
            self.folder_label.configure(text="")
            self.summary_title.configure(text="")
            self.summary_label.configure(text="")
        else:
            self.output_label.configure(text=result[1], text_color=theme.TEXT)
            self.summary_title.configure(text="CHECK BEFORE TAKING PHOTOS")
            # A line per piece is set smaller, so the buttons stay on screen.
            self.summary_label.configure(text=result[2], font=theme.font(12 if "\n" in result[2] else 13, bold=True))
            self.folder_label.configure(text=f"in data/raw/camera_sessions/{datetime.date.today()}/")
        self._update_main_button()

    def _update_main_button(self):
        ready = self.camera_ready and not isinstance(self.validate(), str)
        self.main_button.configure(text="Take photos", state="normal" if ready else "disabled")

    def _lock(self, locked):
        for widget in self.input_widgets():
            widget.configure(state="disabled" if locked else self._unlocked_state(widget))
        self.on_busy(locked)

    def _unlocked_state(self, widget):
        # Combo boxes are pick-only unless the page marks them as ones you can also type in.
        pick_only = isinstance(widget, ctk.CTkComboBox) and widget not in self.typed_choices()
        return "readonly" if pick_only else "normal"

    def typed_choices(self):
        return []

    # Running the job

    def _main_clicked(self):
        if self.run:
            self.run.press_enter()
            self.main_button.configure(text="Taking photos…", state="disabled")
        else:
            self._start()

    def _start(self):
        job_args = self.validate()[0]
        self.photos_taken = 0
        self.output_folder = None
        self.error = None
        self.last_line = None
        self.cancelled = False
        self.open_folder_button.pack_forget()
        self._lock(True)
        self.show_progress(done=1, current=1, status="Starting…")
        self.main_button.configure(text="Taking photos…", state="disabled")
        self.cancel_button.pack(side="right", padx=(0, 12))
        try:
            self.run = start_run(self.job, job_args)
        except OSError as error:
            self._finish(f"Could not start the capture: {error}")
            return
        self._poll()

    def _poll(self):
        for line in self.run.new_lines():
            if line is None:
                self._job_ended()
                return
            self._read_line(line)
        self.after(100, self._poll)

    def _read_line(self, line):
        if line.strip():
            self.last_line = line.strip()
        folder = re.search(r"_dir\s+:\s+(\S.*)$", line)
        if folder:
            self.output_folder = folder.group(1).strip()
        if ">>> capture" in line:
            self.photos_taken += 1
        if "ERROR:" in line:
            self.error = line.split("ERROR:", 1)[1].strip()
        self.read_output(line)

    def _job_ended(self):
        exit_code = self.run.exit_code
        self.run = None
        if self.cancelled:
            self._finish("Cancelled. Photos already taken stay in the folder.")
        elif exit_code != 0:
            self._finish(self.error or self.last_line or f"The capture stopped with exit code {exit_code}.")
        else:
            self._finish(None)

    def _finish(self, problem):
        self.run = None
        self.cancel_button.pack_forget()
        self._lock(False)
        self._update_main_button()
        if problem:
            self.set_status(problem, theme.ERROR)
        else:
            self.guide.show(done=len(self.steps))
            self.set_status(f"Done. {self.photos_taken} photos saved.", theme.SUCCESS)
        if self.output_folder:
            folder = self.output_folder
            self.open_folder_button.configure(command=lambda: open_in_file_browser(folder))
            self.open_folder_button.pack(side="right", padx=(0, 12))

    def _cancel(self):
        if self.run:
            self.cancelled = True
            self.run.stop()

    def stop(self):
        self._cancel()

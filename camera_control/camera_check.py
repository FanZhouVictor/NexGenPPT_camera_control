# Result of one camera check, built up line by line from the preflight job's output.

import datetime
import re
from dataclasses import dataclass, field

JOB = "preflight"
SETTINGS_TOTAL = 15
# gphoto2 cannot set these on the EOS RP (every preflight log shows them rejected and "unavailable").
# They are set once on the camera itself and stay set, so a rejection here is expected, not a warning.
SET_ON_CAMERA = {"Picture Style", "Image quality", "Auto Lighting Optimizer"}


@dataclass(frozen=True)
class CameraSetting:
    label: str
    value: str
    applied: bool
    kept_on_camera: bool = False    # the camera tool can't set it; it stays as set on the camera


@dataclass
class CameraCheck:
    camera: str | None = None
    settings: list = field(default_factory=list)
    error: str | None = None
    log_path: str | None = None
    finished: bool = False
    cancelled: bool = False
    checked_at: str | None = None
    last_line: str | None = None

    def read_line(self, line):
        if line.strip():
            self.last_line = line.strip()
        log = re.search(r"Log(?: file)?:\s+(\S.*)$", line)
        if log:
            self.log_path = log.group(1).strip()
        elif "Camera OK" in line:
            # "Camera OK — Canon EOS RP    usb:020,005" -> "Canon EOS RP"
            self.camera = re.split(r"\s{2,}", line.split("—", 1)[-1].strip())[0]
        elif applied := re.search(r"\sOK\s{2,}(.+) = (.*)$", line):
            # "  OK    ISO speed = 100"
            self.settings.append(CameraSetting(applied.group(1), applied.group(2).strip(), True))
        elif rejected := re.search(r"\s(WARN|SKIP)\s{2,}(.+?) \(.*?='(.*?)'\)", line):
            # "  WARN  WB shift A-B (/main/imgsettings/whitebalanceadjusta='0') — not supported ..."
            # "  SKIP  Color space (/main/imgsettings/colorspace='AdobeRGB') — kept on the camera itself"
            kind, label, value = rejected.groups()
            self.settings.append(CameraSetting(label, value, False, kind == "SKIP" or label in SET_ON_CAMERA))
        elif "ERROR:" in line:
            self.error = line.split("ERROR:", 1)[1].strip()

    def finish(self, exit_code, cancelled=False):
        self.finished = True
        self.checked_at = datetime.datetime.now().strftime("%H:%M")
        self.cancelled = cancelled
        if cancelled:
            self.error = "Check cancelled."
        elif exit_code != 0 and not self.error:
            self.error = self.last_line or f"The camera check stopped with exit code {exit_code}."

    @property
    def settings_set(self):
        return sum(setting.applied for setting in self.settings)

    @property
    def settings_failed(self):
        return [s.label for s in self.settings if not s.applied and not s.kept_on_camera]

    @property
    def settings_on_camera(self):
        return [s.label for s in self.settings if s.kept_on_camera]

    @property
    def settings_done(self):
        return len(self.settings)

    @property
    def state(self):
        # "ready", "warning" (some settings need setting by hand) or "problem".
        if self.error or not self.finished:
            return "problem"
        return "warning" if self.settings_failed else "ready"

    @property
    def camera_ready(self):
        return self.state in ("ready", "warning")

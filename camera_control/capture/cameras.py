# Talking to the camera. One class per camera tool; everything else in capture/ is shared.
#
# A camera class provides:
#   check_tools()                  the tool is installed and nothing else holds the camera
#   detect()                       name of the connected camera
#   supports(setting) -> bool      whether the tool can set this ProfileSetting at all
#   apply(setting) -> bool         set one ProfileSetting; False if the camera refused it
#   read(setting) -> str           current value, for the read-back in the log
#   capture(base) -> [paths]       take one photo, saved as base + camera's extension (.CR3/.JPG)

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from camera_control.system import NO_WINDOW, tool_environment

CAMERA_MODEL = "Canon EOS RP"


class CameraError(RuntimeError):
    pass


class Stopped(Exception):
    pass


class Camera:
    def __init__(self, stop_event, log=None):
        self.stop_event = stop_event
        self.log = log or (lambda text, stamp=True: None)

    def supports(self, setting):
        # False for profile settings this camera tool has no way to set.
        return True

    def run_tool(self, command, timeout=120):
        # Runs a command, but gives up as soon as the capture is cancelled.
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=tool_environment(),
            creationflags=NO_WINDOW,
        )
        started = time.monotonic()
        while True:
            try:
                output, _ = process.communicate(timeout=0.1)
                return process.returncode, output
            except subprocess.TimeoutExpired:
                if self.stop_event.is_set():
                    process.kill()
                    process.communicate()
                    raise Stopped()
                if time.monotonic() - started > timeout:
                    process.kill()
                    process.communicate()
                    raise CameraError(f"{Path(command[0]).name} did not answer within {timeout} s.")


class Gphoto2Camera(Camera):
    # macOS (and Linux). Needs gphoto2: brew install gphoto2

    def check_tools(self):
        if not shutil.which("gphoto2", path=tool_environment()["PATH"]):
            raise CameraError("gphoto2 not found. Run: brew install gphoto2")
        if subprocess.run(["pgrep", "-x", "EOS Utility"], capture_output=True).returncode == 0:
            raise CameraError("EOS Utility 3 is running. Quit it first (only one app may own the USB).")
        self._release_usb()

    def _release_usb(self):
        # macOS's PTPCamera service grabs the camera, so it is stopped before each command.
        if sys.platform != "darwin":
            return
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/com.apple.ptpcamerad"], capture_output=True)
        subprocess.run(["killall", "-9", "ptpcamerad", "PTPCamera"], capture_output=True)
        time.sleep(1)

    def detect(self):
        _, output = self.run_tool(["gphoto2", "--auto-detect"])
        for line in output.splitlines():
            if CAMERA_MODEL.lower() in line.lower():
                return line.split("  ")[0].strip()
        self.log("Auto-detect output:")
        for line in output.splitlines():
            self.log(line)
        raise CameraError(f"{CAMERA_MODEL} not found. Check cable, camera power, and that no other app owns the USB.")

    def _with_retry(self, command):
        for _ in range(3):
            code, output = self.run_tool(command)
            if code == 0:
                return output
            self._release_usb()
        return None

    def apply(self, setting):
        return self._with_retry(["gphoto2", "--set-config-value", f"{setting.key}={setting.value}"]) is not None

    def read(self, setting):
        output = self._with_retry(["gphoto2", "--get-config", setting.key]) or ""
        for line in output.splitlines():
            if line.startswith("Current:"):
                return line.split(":", 1)[1].strip()
        return "(unavailable)"

    def capture(self, base):
        for attempt in range(1, 4):
            code, output = self.run_tool(
                ["gphoto2", "--capture-image-and-download", "--filename", f"{base}.%C", "--force-overwrite"],
            )
            for line in output.splitlines():
                self.log(line, stamp=False)
            if code == 0:
                return saved_files(base)
            self.log(f"  capture attempt {attempt}/3 failed — releasing USB and retrying")
            self._release_usb()
            time.sleep(2)
        raise CameraError(f"No image file was saved for {Path(base).name}.")


class DigiCamControlCamera(Camera):
    # Windows. Talks to the digiCamControl app through CameraControlRemoteCmd.exe, so digiCamControl
    # must be open. Commands checked on the lab PC with digiCamControl 2.1.6 and the EOS RP.
    INSTALL_DIRS = [
        Path(r"C:\Program Files (x86)\digiCamControl"),
        Path(r"C:\Program Files\digiCamControl"),
    ]
    # ProfileSetting key -> (digiCamControl property, value in digiCamControl's spelling).
    # Profile settings not listed here cannot be set from digiCamControl and stay as set on the camera.
    PROPERTIES = {
        "/main/imgsettings/iso": ("iso", "100"),
        "/main/capturesettings/aperture": ("aperture", "8.0"),
        "/main/capturesettings/shutterspeed": ("shutterspeed", "1/125"),
        "/main/imgsettings/whitebalance": ("whitebalance", "Manual"),
        "/main/capturesettings/imageformat": ("compressionsetting", "RAW + Large Fine JPEG"),
        "/main/capturesettings/exposurecompensation": ("exposurecompensation", "0.0"),
    }
    DOWNLOAD_TIMEOUT = 60
    # digiCamControl can keep a photo open for a moment after it has arrived, and Windows won't
    # move or delete a file another program has open, so those are retried for this long.
    FILE_RELEASE_TIMEOUT = 15

    def tool_path(self):
        return next(
            (d / "CameraControlRemoteCmd.exe" for d in self.INSTALL_DIRS if (d / "CameraControlRemoteCmd.exe").exists()),
            None,
        )

    def running_programs(self):
        return subprocess.run(["tasklist"], capture_output=True, text=True, creationflags=NO_WINDOW).stdout

    def check_tools(self):
        if not self.tool_path():
            raise CameraError("digiCamControl not found. Install it from digicamcontrol.com.")
        running = self.running_programs()
        if "EOS Utility" in running:
            raise CameraError("EOS Utility is running. Quit it first (only one app may own the USB).")
        if "CameraControl.exe" not in running:
            raise CameraError("digiCamControl is not open. Open it, leave it open, and check again.")

    def command(self, *words):
        # Answers look like ':;response:"100";' or ':;response:["Auto","100"];' (the value is JSON),
        # and errors like ':;response:error;message:Unknow parameter'.
        _, output = self.run_tool([str(self.tool_path()), "/c", *words])
        for line in output.splitlines():
            if line.startswith(":;response:"):
                value = line[len(":;response:"):].rstrip().rstrip(";")
                if value.startswith("error"):
                    message = value.partition("message:")[2] or value
                    raise CameraError(f"digiCamControl could not do '{' '.join(words)}': {message}")
                try:
                    return json.loads(value)
                except ValueError:
                    return value
        problem = " ".join(line.strip() for line in output.splitlines()[1:] if line.strip())
        raise CameraError(f"digiCamControl did not answer '{' '.join(words)}'. {problem}".strip())

    def detect(self):
        cameras = self.command("list", "cameras")
        if not cameras:
            raise CameraError(f"{CAMERA_MODEL} not found. Check cable, camera power, and that no other app owns the USB.")
        mode = self.command("get", "mode")
        if mode != "M":
            raise CameraError(f"The camera mode dial is on {mode}. Turn it to M.")
        transfer = self.command("get", "transfer")
        if "PC" not in str(transfer):
            raise CameraError(f"digiCamControl transfer is '{transfer}'. Set it to 'Save to PC only'.")
        return f"{CAMERA_MODEL} (serial {cameras[0]})"

    def supports(self, setting):
        return setting.key in self.PROPERTIES

    def apply(self, setting):
        name, value = self.PROPERTIES[setting.key]
        try:
            self.command("set", name, value)
            return self.command("get", name) == value
        except CameraError:
            return False

    def read(self, setting):
        try:
            return str(self.command("get", self.PROPERTIES[setting.key][0]))
        except CameraError:
            return "(unavailable)"

    def capture(self, base):
        # digiCamControl names the files itself, so photos land in a staging folder first and are
        # then moved to base + extension (e.g. .CR3 and .JPG), the same names the Mac produces.
        base = Path(base)
        staging = base.parent / "_incoming"
        staging.mkdir(exist_ok=True)
        for leftover in staging.iterdir():
            self._when_released(leftover, leftover.unlink)
        self.command("set", "session.folder", str(staging))
        self.command("capture")

        arrived = self._wait_for_photos(staging)
        saved = []
        for photo in arrived:
            target = base.with_name(base.name + photo.suffix.upper())
            self._when_released(photo, lambda: shutil.move(str(photo), str(target)))
            self.log(f"Saving file as {target}", stamp=False)
            saved.append(target)
        try:
            staging.rmdir()
        except OSError:
            pass   # digiCamControl still has the folder open; it is emptied before the next photo
        return sorted(saved)

    def _when_released(self, photo, action):
        # Runs action (moving or deleting photo), waiting while another program still has it open.
        started = time.monotonic()
        while True:
            try:
                return action()
            except PermissionError:
                if time.monotonic() - started > self.FILE_RELEASE_TIMEOUT:
                    raise CameraError(
                        f"{photo.name} is still open in another program after {self.FILE_RELEASE_TIMEOUT} s. "
                        "Close any program showing the photo (such as a viewer or Explorer preview) and try again."
                    )
                if self.stop_event.is_set():
                    raise Stopped()
                time.sleep(0.25)

    def _wait_for_photos(self, folder):
        # Done when a raw file has arrived and nothing has changed for 2 seconds.
        started = time.monotonic()
        last_change, last_seen = started, {}
        while time.monotonic() - started < self.DOWNLOAD_TIMEOUT:
            if self.stop_event.is_set():
                raise Stopped()
            seen = {p: p.stat().st_size for p in folder.iterdir() if p.is_file()}
            if seen != last_seen:
                last_seen, last_change = seen, time.monotonic()
            elif any(p.suffix.lower() == ".cr3" for p in seen) and time.monotonic() - last_change > 2:
                return sorted(seen)
            time.sleep(0.25)
        if last_seen:
            raise CameraError("The photo arrived without a RAW (.CR3) file. Set image quality to RAW + Large Fine JPEG.")
        raise CameraError("No photo arrived from digiCamControl. Check that it is set to transfer photos to the PC.")


def saved_files(base):
    base = Path(base)
    return sorted(p for p in base.parent.glob(base.name + ".*") if p.suffix.lower() != ".log")


def camera_for_this_computer(stop_event, log=None):
    camera_class = DigiCamControlCamera if sys.platform == "win32" else Gphoto2Camera
    return camera_class(stop_event, log)

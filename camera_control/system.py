# Paths and small helpers that differ between macOS and Windows.

import os
import subprocess
import sys
from pathlib import Path

APP_FOLDER = "NexGenPPT Camera Control"
# Where Homebrew installs gphoto2. Apps opened from Finder or the Dock don't get these on PATH.
TOOL_DIRS = ["/opt/homebrew/bin", "/usr/local/bin"]


def tool_environment():
    env = dict(os.environ)
    paths = env.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin").split(os.pathsep)
    env["PATH"] = os.pathsep.join([*paths, *(d for d in TOOL_DIRS if d not in paths)])
    return env


def documents_folder():
    # The user's Documents folder. On Windows it can have been moved, e.g. into OneDrive.
    if sys.platform == "win32":
        import ctypes
        path = ctypes.create_unicode_buffer(260)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, path) == 0:   # 5: CSIDL_PERSONAL
            return Path(path.value)
    return Path.home() / "Documents"


def shown_path(path):
    # How a folder is shown to the operator: "Documents/NexGenPPT Camera Control/..." rather than
    # the full path, when it is inside their home folder.
    path = Path(path)
    try:
        return path.relative_to(Path.home()).as_posix()
    except ValueError:
        return str(path)


def open_in_file_browser(path):
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)])
    else:
        subprocess.run(["xdg-open", str(path)])

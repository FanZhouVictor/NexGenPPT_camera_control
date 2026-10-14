# Paths and small helpers that differ between macOS and Windows.

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Where Homebrew installs gphoto2. Apps opened from Finder or the Dock don't get these on PATH.
TOOL_DIRS = ["/opt/homebrew/bin", "/usr/local/bin"]


def tool_environment():
    env = dict(os.environ)
    paths = env.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin").split(os.pathsep)
    env["PATH"] = os.pathsep.join([*paths, *(d for d in TOOL_DIRS if d not in paths)])
    return env


def open_in_file_browser(path):
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)])
    else:
        subprocess.run(["xdg-open", str(path)])

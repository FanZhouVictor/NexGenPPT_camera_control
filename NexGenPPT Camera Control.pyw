# Opens NexGenPPT Camera Control on Windows without a console window, updating it first.
# Double-click this file, or a desktop shortcut to it (see "Lab PC" in README.md).

import subprocess
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_PYTHON = HERE / ".venv" / "Scripts" / "pythonw.exe"
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0   # CREATE_NO_WINDOW


def quietly(*command, timeout):
    # Runs a command with no window. Failing (no Git, no internet) is fine: the current version opens.
    try:
        subprocess.run(command, cwd=HERE, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired):
        pass


def show_error(details):
    # pythonw has no console, so a start-up problem would otherwise vanish without a trace.
    (HERE / "launch_error.log").write_text(details)
    import tkinter
    from tkinter import messagebox
    root = tkinter.Tk()
    root.withdraw()
    messagebox.showerror(
        "NexGenPPT Camera Control",
        f"The app could not start.\n\n{details.strip().splitlines()[-1]}\n\nDetails are in {HERE / 'launch_error.log'}",
    )


# Double-clicking a .pyw file starts the computer's own Python; the app runs in its .venv instead.
if APP_PYTHON.exists() and Path(sys.executable).resolve() != APP_PYTHON.resolve():
    subprocess.Popen([str(APP_PYTHON), __file__], cwd=HERE, creationflags=NO_WINDOW)
    sys.exit()

quietly("git", "pull", "--ff-only", "--quiet", timeout=30)
quietly(sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-r", "requirements.txt",
        timeout=300)

try:
    sys.path.insert(0, str(HERE))
    from camera_control.app import main
    main()
except Exception:
    show_error(traceback.format_exc())

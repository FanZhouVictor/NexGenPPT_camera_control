@echo off
rem Opens NexGenPPT Camera Control on Windows, updating it first.
rem Make a desktop shortcut to this file; see "Lab PC" in README.md.
cd /d "%~dp0"

rem Get the latest version. Without internet this fails quietly and the current version opens.
git pull --ff-only --quiet

rem Install any new libraries the new version needs.
.venv\Scripts\pip install --quiet --disable-pip-version-check -r requirements.txt

start "" .venv\Scripts\pythonw.exe -m camera_control

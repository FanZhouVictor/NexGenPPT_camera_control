# Main window: sidebar on the left, the selected page on the right.

import sys
import tkinter
from pathlib import Path

import customtkinter as ctk
from camera_control import __version__, theme
from camera_control.camera_setup import CameraSetupPage
from camera_control.capture.case_capture import todays_captures, todays_folder
from camera_control.sidebar import Sidebar
from camera_control.system import open_in_file_browser
from camera_control.workflows import WORKFLOWS

CAMERA_SETUP = "camera_setup"
ASSETS = Path(__file__).resolve().parent / "assets"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"NexGenPPT Camera Control {__version__}")
        self._set_icon()
        # Sized for the Specimen photos page: its form needs the width, the rotation pause the height.
        self.geometry("1180x800")
        self.minsize(1100, 790)

        # Kept for the whole session, so leaving the camera page doesn't lose it.
        self.camera_check = None

        self.sidebar = Sidebar(
            self, [(w.key, w.label) for w in WORKFLOWS], self.select, lambda: self.select(CAMERA_SETUP),
            open_in_file_browser,
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
        self.sidebar.show_today(todays_captures(), todays_folder())
        self.select(CAMERA_SETUP)
        self.after(100, self.bring_to_front)

    def _set_icon(self):
        # The app's own icon for the window and the taskbar or Dock, instead of Python's.
        if sys.platform == "win32":
            self.iconbitmap(str(ASSETS / "icon.ico"))
            self.after(300, self._sharpen_windows_icon)
        else:
            self.icon = tkinter.PhotoImage(file=str(ASSETS / "icon.png"))   # kept, or Tk drops the image
            self.iconphoto(True, self.icon)

    def _sharpen_windows_icon(self):
        # Tk hands Windows only its 32 px icon, which the taskbar stretches (and blurs) on screens
        # scaled above 100%. Give the window the sizes this screen uses, straight from the .ico.
        import ctypes
        from ctypes import wintypes
        WM_SETICON, ICON_SMALL, ICON_BIG = 0x0080, 0, 1
        IMAGE_ICON, LR_LOADFROMFILE, SM_CXICON, SM_CXSMICON = 1, 0x0010, 11, 49
        user32 = ctypes.windll.user32
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.LoadImageW.argtypes = [
            wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT,
        ]
        user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        try:
            window = int(self.wm_frame(), 16)
            try:
                dpi = user32.GetDpiForWindow(wintypes.HWND(window))
                size_of = lambda metric: user32.GetSystemMetricsForDpi(metric, dpi)
            except AttributeError:   # Windows older than 10 has no per-screen sizes
                size_of = user32.GetSystemMetrics
            for which, metric in ((ICON_BIG, SM_CXICON), (ICON_SMALL, SM_CXSMICON)):
                size = size_of(metric)
                icon = user32.LoadImageW(None, str(ASSETS / "icon.ico"), IMAGE_ICON, size, size, LR_LOADFROMFILE)
                if icon:
                    user32.SendMessageW(window, WM_SETICON, which, icon)
        except (OSError, ValueError):
            pass   # the icon Tk set stays; only its sharpness is lost

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
                self.page_card, self.action_bar, self.set_busy,
                self.camera_check, self.camera_checked, lambda: self.select(WORKFLOWS[0].key),
            )
        else:
            workflow = next(w for w in WORKFLOWS if w.key == key)
            self._set_heading(workflow.label, workflow.description)
            if workflow.page:
                self.page = workflow.page(self.page_card, self.action_bar, self.set_busy, self.camera_ready())
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

    def set_busy(self, busy):
        # Pages call this while the camera is working. Afterwards a capture may have been saved.
        self.sidebar.lock(busy)
        if not busy:
            self.sidebar.show_today(todays_captures(), todays_folder())

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
    if sys.platform == "win32":
        # Groups the window under its own taskbar button and icon, not Python's.
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("NexGenPPT.CameraControl")
    theme.apply_theme()
    App().mainloop()

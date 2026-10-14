# Runs a capture job in a background thread. The job prints its progress line by line,
# and the pages read those lines to move their steps along.

import queue
import threading

from camera_control.capture.cameras import CameraError, Stopped


class CaptureRun:
    def __init__(self, job, args):
        self.lines = queue.Queue()
        self.stop_event = threading.Event()
        self._enter_pressed = threading.Event()
        self._exit_code = None
        threading.Thread(target=self._run, args=(job, args), daemon=True).start()

    def _run(self, job, args):
        try:
            job(self, args)
            self._exit_code = 0
        except Stopped:
            self._exit_code = 1
        except CameraError as error:
            self.print(f"ERROR: {error}")
            self._exit_code = 1
        except Exception as error:
            self.print(f"ERROR: {type(error).__name__}: {error}")
            self._exit_code = 1
        self.lines.put(None)

    # For jobs

    def print(self, text):
        self.lines.put(text)

    def wait_for_enter(self):
        while not self._enter_pressed.wait(0.1):
            if self.stop_event.is_set():
                raise Stopped()
        self._enter_pressed.clear()

    # For pages

    def new_lines(self):
        # Lines printed since the last call. None marks the end of the output.
        out = []
        while True:
            try:
                out.append(self.lines.get_nowait())
            except queue.Empty:
                return out

    def press_enter(self):
        self._enter_pressed.set()

    def stop(self):
        self.stop_event.set()

    @property
    def exit_code(self):
        return self._exit_code

# Capture jobs the pages can start. Each runs in a background thread (see run.py).

from camera_control.capture.case_capture import capture_batch, capture_case
from camera_control.capture.preflight import run_preflight
from camera_control.capture.run import CaptureRun

JOBS = {
    "batch": capture_batch,
    "case": capture_case,
    "preflight": run_preflight,
}


def start_run(job, args):
    return CaptureRun(JOBS[job], args)

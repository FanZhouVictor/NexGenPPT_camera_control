# Camera check: find the camera, apply the session profile, read it back, and log everything.
# Prints the lines camera_check.py reads.

import datetime

from camera_control.capture.cameras import CameraError, camera_for_this_computer
from camera_control.capture.case_capture import output_root
from camera_control.capture.profile import SESSION_PROFILE

RULE = "=" * 57


def run_preflight(run, args):
    now = datetime.datetime.now()
    log_dir = output_root() / now.strftime("%Y-%m-%d")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"preflight_{now:%Y-%m-%d-%H%M%S}.log"

    with open(log_path, "a") as log_file:
        def log(text, stamp=True):
            line = f"{datetime.datetime.now():%H:%M:%S} {text}" if stamp else text
            log_file.write(line + "\n")
            log_file.flush()
            run.print(line)

        log(RULE)
        log(f" EOS RP preflight — {now:%Y-%m-%d %H:%M:%S}")
        log(" Mode: APPLY settings")
        log(" WB:   post-processing via ColorChecker N5 patch (Camera Raw)")
        log(f" Log:  {log_path}")
        log(RULE)

        camera = camera_for_this_computer(run.stop_event, log)
        try:
            camera.check_tools()
            log("Detecting camera over USB...")
            log(f"Camera OK — {camera.detect()}")

            log("")
            log("Applying session profile...")
            for setting in SESSION_PROFILE:
                if not camera.supports(setting):
                    log(f"  SKIP  {setting.label} ({setting.key}='{setting.value}') — kept on the camera itself")
                elif camera.apply(setting):
                    log(f"  OK    {setting.label} = {setting.value}")
                else:
                    log(f"  WARN  {setting.label} ({setting.key}='{setting.value}') — "
                        "not supported on this body or rejected; continuing")

            log("")
            log("Verifying (read-back)...")
            for setting in SESSION_PROFILE:
                if camera.supports(setting):
                    log(f"  {setting.label} = {camera.read(setting)}")
        except CameraError as error:
            # Into the log file only; run.py prints the error for the app.
            log_file.write(f"{datetime.datetime.now():%H:%M:%S} ERROR: {error}\n")
            raise

        log("")
        log(RULE)
        log(" PREFLIGHT SUMMARY")
        log(RULE)
        log(" Mode:     APPLY settings")
        log(" WB:       set in post via ColorChecker N5 patch (Camera Raw)")
        log(f" Log file: {log_path}")
        log(RULE)

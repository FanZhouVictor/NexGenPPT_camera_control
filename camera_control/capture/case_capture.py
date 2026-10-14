# One specimen: 2 photos at 0°, pause for the 180° turn, 2 more photos, then case_manifest.json.

import datetime
import json
import os
from pathlib import Path

from camera_control.capture.cameras import CameraError, camera_for_this_computer
from camera_control.capture.case_rules import InvalidCase, case_slug, check_case
from camera_control.system import PROJECT_ROOT

ROTATIONS = [0, 180]
REPS_PER_ROTATION = 2
PREFIX = "[acquire_case]"


def output_root():
    return Path(os.environ.get("CAMERA_OUTPUT_ROOT") or PROJECT_ROOT / "data" / "raw" / "camera_sessions")


def parse_args(args):
    # ["--test", "C187", "--coupon", "parent", ...] -> {"test": "C187", "coupon": "parent", ...}
    return {args[i].lstrip("-"): args[i + 1] for i in range(0, len(args) - 1, 2)}


def capture_case(run, args):
    options = parse_args(args)
    test, coupon, treatment, stage = (options.get(k, "") for k in ("test", "coupon", "treatment", "stage"))
    try:
        check_case(test, coupon, treatment, stage)
    except InvalidCase as error:
        raise CameraError(str(error))

    slug = case_slug(test, coupon, treatment, stage)
    now = datetime.datetime.now()
    date, session_time = now.strftime("%Y-%m-%d"), now.strftime("%H%M%S")
    case_dir = output_root() / date / f"{slug}_{session_time}"

    run.print(f"{PREFIX} case_slug   : {slug}")
    run.print(f"{PREFIX} case_dir    : {case_dir}")
    run.print(f"{PREFIX} rotations   : {' '.join(map(str, ROTATIONS))}")
    run.print(f"{PREFIX} reps each   : {REPS_PER_ROTATION}")
    run.print(f"{PREFIX} total frames: {REPS_PER_ROTATION * len(ROTATIONS)}")
    run.print("")
    case_dir.mkdir(parents=True, exist_ok=True)

    for rotation in ROTATIONS:
        rotation_dir = case_dir / f"rot_{rotation}deg"
        rotation_dir.mkdir(exist_ok=True)
        if rotation != ROTATIONS[0]:
            run.print("")
            run.print(f"{PREFIX} " + "=" * 60)
            run.print(f"{PREFIX}   PAUSE  ── rotate the specimen 180° (in-plane), keep the ")
            run.print(f"{PREFIX}            ColorChecker at the right edge of the A3 sheet.")
            run.print(f"{PREFIX}   After the rotation, press <enter> to continue.")
            run.print(f"{PREFIX} " + "=" * 60)
            run.wait_for_enter()
        for rep in range(1, REPS_PER_ROTATION + 1):
            label = f"{slug}_{rotation}deg_r{rep:02d}"
            run.print("")
            run.print(f"{PREFIX} >>> capture rot {rotation}° rep {rep:02d} : label = {label}")
            capture_frame(run, rotation_dir, label)

    manifest = case_dir / "case_manifest.json"
    write_manifest(manifest, case_dir, slug, test, coupon, treatment, stage, date, session_time)
    run.print(f"{PREFIX} manifest    : {manifest}")
    run.print("")
    run.print(f"{PREFIX} " + "=" * 60)
    run.print(f"{PREFIX}   CASE COMPLETE")
    run.print(f"{PREFIX}   slug : {slug}")
    run.print(f"{PREFIX}   dir  : {case_dir}")
    run.print(f"{PREFIX}   next : stage the next case on the jig and re-run")
    run.print(f"{PREFIX} " + "=" * 60)


def capture_frame(run, folder, label):
    # One photo: <folder>/<YYYY-MM-DD-HHMMSS>-<label>.{CR3,JPG,log}
    base = folder / f"{datetime.datetime.now():%Y-%m-%d-%H%M%S}-{label}"
    log_path = base.with_name(base.name + ".log")

    with open(log_path, "a") as log_file:
        def log(text, stamp=True):
            line = f"{datetime.datetime.now():%H:%M:%S} {text}" if stamp else text
            log_file.write(line + "\n")
            log_file.flush()
            run.print(line)

        camera = camera_for_this_computer(run.stop_event, log)
        try:
            camera.check_tools()
            log("Detecting camera...")
            camera.detect()
            log("Camera OK")
            log(f"Output folder : {folder}")
            log(f"Filename base : {base.name}")
            log(f"Capture log   : {log_path}")
            log("Firing shutter (drive mode: 2 s self-timer — stand clear)...")
            camera.capture(base)
        except CameraError as error:
            # Into this photo's log only; run.py prints the error for the app.
            log_file.write(f"{datetime.datetime.now():%H:%M:%S} ERROR: {error}\n")
            raise
        log("=" * 57)
        log(" CAPTURE COMPLETE")
        log(f" Label   : {label}")
        log(f" Saved to: {base}.*")
        log(f" Log     : {log_path}")
        log("=" * 57)


def write_manifest(manifest, case_dir, slug, test, coupon, treatment, stage, date, session_time):
    frames = []
    for rotation in ROTATIONS:
        rotation_dir = case_dir / f"rot_{rotation}deg"
        if not rotation_dir.is_dir():
            continue
        raw_files = sorted(set(rotation_dir.rglob("*.cr3")) | set(rotation_dir.rglob("*.CR3")))
        for path in raw_files:
            frames.append({
                "rotation_deg": rotation,
                "basename": path.stem,
                "cr3": path.relative_to(case_dir).as_posix(),
            })
    payload = {
        "case_slug": slug,
        "test": test,
        "coupon": coupon,
        "treatment": treatment,
        "stage": stage,
        "date": date,
        "session_start_local": session_time,
        "rotations_deg": ROTATIONS,
        "reps_per_rotation": REPS_PER_ROTATION,
        "background": "BWblue",
        "frames": frames,
    }
    manifest.write_text(json.dumps(payload, indent=2) + "\n")

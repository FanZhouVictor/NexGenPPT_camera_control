# One specimen: 2 photos at 0°, pause for the 180° turn, 2 more photos, then case_manifest.json.

import datetime
import json
import os
import re
from pathlib import Path

from camera_control.capture.cameras import CameraError, camera_for_this_computer
from camera_control.capture.specimen import (
    InvalidSpecimen, check_specimen, folder_name, piece_names, remember_pieces, specimen_name, summary,
)
from camera_control.system import APP_FOLDER, documents_folder

ROTATIONS = [0, 180]
REPS_PER_ROTATION = 2
PREFIX = "[acquire_case]"


def output_root():
    # Photos are saved in Documents/NexGenPPT Camera Control unless CAMERA_OUTPUT_ROOT names another folder.
    return Path(os.environ.get("CAMERA_OUTPUT_ROOT") or documents_folder() / APP_FOLDER)


def todays_folder():
    return output_root() / datetime.date.today().strftime("%Y-%m-%d")


def todays_captures():
    # Captures finished today (they have a case_manifest.json), newest first,
    # as ("13:59", "C205_P2", the capture's folder).
    folder = todays_folder()
    captures = []
    for manifest in folder.glob("*/case_manifest.json"):
        try:
            data = json.loads(manifest.read_text())
        except (OSError, ValueError):
            continue
        started = str(data.get("session_start_local", ""))
        captures.append((started, data.get("case_slug") or manifest.parent.name, manifest.parent))
    return [
        (f"{started[:2]}:{started[2:4]}", name, folder)
        for started, name, folder in sorted(captures, key=lambda capture: capture[0], reverse=True)
    ]


def capture_case(run, specimen):
    # specimen: the answers from the specimen form (see specimen.py).
    try:
        check_specimen(specimen)
    except InvalidSpecimen as error:
        raise CameraError(str(error))

    slug = specimen_name(specimen)
    if specimen["object"] == "piece":
        remember_pieces(output_root(), specimen["sample_id"], piece_names(specimen))
    now = datetime.datetime.now()
    date, session_time = now.strftime("%Y-%m-%d"), now.strftime("%H%M%S")
    case_dir = output_root() / date / f"{folder_name(specimen)}_{session_time}"

    run.print(f"{PREFIX} case_slug   : {slug}")
    run.print(f"{PREFIX} specimen    : {summary(specimen)}")
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
    write_manifest(manifest, case_dir, slug, specimen, date, session_time)
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


def write_manifest(manifest, case_dir, slug, specimen, date, session_time):
    frames = []
    for rotation in ROTATIONS:
        rotation_dir = case_dir / f"rot_{rotation}deg"
        if not rotation_dir.is_dir():
            continue
        raw_files = sorted(set(rotation_dir.rglob("*.cr3")) | set(rotation_dir.rglob("*.CR3")))
        for path in raw_files:
            frames.append({
                "rotation_deg": rotation,
                "rep": int(re.search(r"_r(\d+)$", path.stem).group(1)),
                "basename": path.stem,
                "cr3": path.relative_to(case_dir).as_posix(),
            })
    payload = {
        "case_slug": slug,
        "summary": summary(specimen),
        **specimen,
        "date": date,
        "session_start_local": session_time,
        "rotations_deg": ROTATIONS,
        "reps_per_rotation": REPS_PER_ROTATION,
        "background": "BWblue",
        "frames": frames,
    }
    manifest.write_text(json.dumps(payload, indent=2) + "\n")

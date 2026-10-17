# Capture jobs run against the fake camera tools in tests/fakes, so no camera is needed.
# The fakes are shell scripts, so these run on macOS and Linux only.
#
#   python -m unittest discover tests

import datetime
import json
import os
import re
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from camera_control.camera_check import CameraCheck
from camera_control.capture.cameras import CameraError, DigiCamControlCamera, Gphoto2Camera
from camera_control.capture.case_capture import capture_case, todays_captures
from camera_control.capture.preflight import run_preflight
from camera_control.capture.run import CaptureRun
from camera_control.capture.specimen import (
    InvalidSpecimen, check_specimen, duration, folder_name, known_pieces, specimen_name, summary,
)

FAKES = Path(__file__).resolve().parent / "fakes"
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}-\d{6}")
PARENT = {
    "sample_id": "C187", "object": "parent", "piece": None, "pieces_total": None, "description": None,
    "contamination": "before",
    "aged": "no", "aged_for": None,
    "washed": "no", "wash_condition": None, "since_wash": None, "wetness": None, "order": None,
    "notes": "",
}
PIECE = {
    **PARENT, "sample_id": "C205", "object": "piece", "piece": "P2", "pieces_total": 4,
    "contamination": "after",
    "aged": "yes", "aged_for": {"value": 7.0, "unit": "days"},
    "washed": "yes", "wash_condition": "PER", "since_wash": {"value": 6.0, "unit": "hours"}, "wetness": "dry",
    "order": "aged_then_washed",
}
def masked(text):
    return TIMESTAMP.sub("<time>", text)


def run_job(job, args):
    run = CaptureRun(job, args)
    lines = []
    while True:
        for line in run.new_lines():
            if line is None:
                return run.exit_code, lines
            lines.append(line)
            if "PAUSE" in line:
                run.press_enter()
        time.sleep(0.02)


def camera_check():
    exit_code, lines = run_job(run_preflight, [])
    check = CameraCheck()
    for line in lines:
        check.read_line(line)
    check.finish(exit_code)
    return check


class Specimens(unittest.TestCase):
    def test_names(self):
        self.assertEqual(specimen_name(PARENT), "C187_parent")
        self.assertEqual(specimen_name(PIECE), "C205_P2")
        self.assertEqual(specimen_name({**PARENT, "object": "other", "description": "offcut"}), "C187_other")

    def test_folder_names_say_the_condition(self):
        self.assertEqual(folder_name(PARENT), "C187_parent_clean")
        self.assertEqual(folder_name(PIECE), "C205_P2_contam_aged7d_washed")
        self.assertEqual(folder_name({**PIECE, "aged_for": "unknown"}), "C205_P2_contam_aged_washed")
        self.assertEqual(folder_name({**PIECE, "aged_for": {"value": 1.5, "unit": "hours"}}),
                         "C205_P2_contam_aged1.5h_washed")

    def test_summary(self):
        self.assertEqual(summary(PARENT), "C187 · whole parent · before contamination · not aged · not washed")
        self.assertEqual(
            summary(PIECE),
            "C205 · P2 · after contamination · aged 7 days · 6 hours after wash (PER) · dry · aged, then washed",
        )

    def test_any_combination_of_answers_is_allowed(self):
        check_specimen(PARENT)
        check_specimen(PIECE)
        check_specimen({**PIECE, "contamination": "before", "washed": "no", "wetness": None, "order": None})
        check_specimen({**PARENT, "aged": "yes", "aged_for": "unknown"})

    def test_missing_answers(self):
        for change, problem in [
            ({"sample_id": ""}, "sample ID"),
            ({"sample_id": "C 187/a"}, "letters, numbers"),
            ({"object": None}, "what you are photographing"),
            ({"object": "piece", "pieces_total": 4}, "which piece"),
            ({"object": "piece", "piece": "P5", "pieces_total": 4}, "which piece"),
            ({"object": "piece", "piece": "P1"}, "how many pieces"),
            ({"object": "other"}, "Describe"),
            ({"contamination": None}, "contamination"),
            ({"contamination": "unknown"}, "contamination"),
            ({"aged": "unknown"}, "aged"),
            ({"washed": "unknown"}, "washed"),
            ({"washed": "yes", "wetness": "unknown"}, "how wet"),
            ({"aged": None}, "aged"),
            ({"washed": "yes"}, "how wet"),
            ({"aged": "yes", "washed": "yes", "wetness": "dry"}, "first"),
        ]:
            with self.subTest(change=change), self.assertRaisesRegex(InvalidSpecimen, problem):
                check_specimen({**PARENT, **change})

    def test_pieces_can_be_renamed(self):
        names = ["L", "ML", "MR", "R"]
        renamed = {**PIECE, "piece": "ML", "piece_names": names}
        check_specimen(renamed)
        self.assertEqual(specimen_name(renamed), "C205_ML")
        self.assertEqual(summary(renamed).split(" · ")[1], "ML")
        for change, problem in [
            ({"piece": "P2"}, "which piece"),                       # the old name is gone
            ({"piece_names": ["L", "ML", "MR"]}, "4 different piece names"),
            ({"piece_names": ["L", "ML", "ml", "R"]}, "different piece names"),
            ({"piece_names": ["L", "M-L", "MR", "R"]}, "letters and numbers only"),
            ({"piece_names": ["L", "ML", "MR", "farrightend"]}, "up to 8"),
        ]:
            with self.subTest(change=change), self.assertRaisesRegex(InvalidSpecimen, problem):
                check_specimen({**renamed, **change})

    def test_times(self):
        self.assertEqual(duration("", "hours"), "unknown")
        self.assertEqual(duration(" 1,5 ", "days"), {"value": 1.5, "unit": "days"})
        self.assertEqual(summary({**PARENT, "aged": "yes", "aged_for": duration("1", "days")}).split(" · ")[3],
                         "aged 1 day")
        for text in ("soon", "-2", "inf"):
            with self.subTest(text=text), self.assertRaises(InvalidSpecimen):
                duration(text, "hours")


class FakeToolTest(unittest.TestCase):
    camera_class = None

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved_env = dict(os.environ)
        os.environ["PATH"] = f"{FAKES}{os.pathsep}{os.environ['PATH']}"
        os.environ["CAMERA_OUTPUT_ROOT"] = str(self.tmp / "out")
        self.patches = [
            mock.patch("camera_control.capture.preflight.camera_for_this_computer", self.camera_class),
            mock.patch("camera_control.capture.case_capture.camera_for_this_computer", self.camera_class),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        os.environ.clear()
        os.environ.update(self.saved_env)
        shutil.rmtree(self.tmp)

    def saved_names(self):
        return sorted(masked(p.name) for p in (self.tmp / "out").rglob("*") if p.is_file())

    def assert_case_saved(self):
        exit_code, lines = run_job(capture_case, PARENT)
        self.assertEqual(exit_code, 0, lines[-3:])
        names = self.saved_names()
        self.assertEqual(len(names), 13)   # 4 photos x (CR3, JPG, log) + manifest
        self.assertIn("<time>-C187_parent_0deg_r01.CR3", names)
        self.assertIn("<time>-C187_parent_180deg_r02.JPG", names)
        manifest = json.loads(next((self.tmp / "out").rglob("case_manifest.json")).read_text())
        self.assertEqual([(frame["rotation_deg"], frame["rep"]) for frame in manifest["frames"]],
                         [(0, 1), (0, 2), (180, 1), (180, 2)])
        self.assertEqual({key: manifest[key] for key in PARENT}, PARENT)
        self.assertEqual(manifest["summary"], summary(PARENT))


@unittest.skipUnless(os.name == "posix", "the fake gphoto2 is a shell script")
class Gphoto2Capture(FakeToolTest):
    camera_class = Gphoto2Camera

    def setUp(self):
        super().setUp()
        for name in ("FAKE_CAMERA", "FAKE_REJECT"):
            os.environ.pop(name, None)

    def test_camera_check_sets_every_setting(self):
        check = camera_check()
        self.assertEqual(check.state, "ready")
        self.assertEqual(check.camera, "Canon EOS RP")
        self.assertEqual(check.settings_set, 15)
        self.assertTrue(Path(check.log_path).exists())

    def test_rejected_settings_are_a_warning(self):
        os.environ["FAKE_REJECT"] = "whitebalanceadjust"
        check = camera_check()
        self.assertEqual(check.state, "warning")
        self.assertEqual(check.settings_failed, ["WB shift A-B", "WB shift G-M"])

    def test_missing_camera_is_a_problem(self):
        os.environ["FAKE_CAMERA"] = "missing"
        check = camera_check()
        self.assertEqual(check.state, "problem")
        self.assertIn("not found", check.error)

    def test_case_capture(self):
        self.assert_case_saved()

    def test_piece_capture_saves_every_answer_and_remembers_the_piece_count(self):
        exit_code, lines = run_job(capture_case, PIECE)
        self.assertEqual(exit_code, 0, lines[-3:])
        self.assertIn("<time>-C205_P2_180deg_r02.CR3", self.saved_names())
        folder = next((self.tmp / "out").rglob("case_manifest.json")).parent.name
        self.assertRegex(folder, r"^C205_P2_contam_aged7d_washed_\d{6}$")
        manifest = json.loads(next((self.tmp / "out").rglob("case_manifest.json")).read_text())
        self.assertEqual({key: manifest[key] for key in PIECE}, PIECE)
        self.assertEqual(known_pieces(self.tmp / "out", "C205"), ["P1", "P2", "P3", "P4"])
        self.assertIsNone(known_pieces(self.tmp / "out", "C187"))

    def test_todays_captures_lists_finished_captures_newest_first(self):
        self.assertEqual(todays_captures(), [])
        run_job(capture_case, PARENT)
        time.sleep(1.1)   # folder names carry the time to the second
        run_job(capture_case, PIECE)
        unfinished = self.tmp / "out" / datetime.date.today().strftime("%Y-%m-%d") / "C999_parent_clean_235959"
        unfinished.mkdir()   # a cancelled capture has photos but no manifest
        captures = todays_captures()
        self.assertEqual([name for _, name, _ in captures], ["C205_P2", "C187_parent"])
        self.assertRegex(captures[0][0], r"^\d\d:\d\d$")
        self.assertTrue((captures[0][2] / "case_manifest.json").exists())

    def test_incomplete_answers_stop_the_capture(self):
        exit_code, lines = run_job(capture_case, {**PARENT, "aged": None})
        self.assertEqual(exit_code, 1)
        self.assertIn("aged", lines[-1])
        self.assertEqual(self.saved_names(), [])


@unittest.skipUnless(os.name == "posix", "the fake digiCamControl is a shell script")
class DigiCamControlCapture(FakeToolTest):
    camera_class = DigiCamControlCamera

    def setUp(self):
        super().setUp()
        os.environ["FAKE_DCC_STATE"] = str(self.tmp / "state")
        os.environ.pop("FAKE_DCC", None)
        self.patches += [
            mock.patch.object(DigiCamControlCamera, "tool_path", lambda camera: FAKES / "CameraControlRemoteCmd"),
            mock.patch.object(DigiCamControlCamera, "running_programs", lambda camera: "CameraControl.exe"),
        ]
        for patch in self.patches[-2:]:
            patch.start()

    def test_camera_check_sets_what_it_can_and_keeps_the_rest_on_the_camera(self):
        check = camera_check()
        self.assertEqual(check.state, "ready")
        self.assertEqual(check.camera, "Canon EOS RP (serial 292027001666)")
        self.assertEqual(check.settings_set, 6)
        self.assertEqual(len(check.settings_on_camera), 9)
        self.assertEqual(check.settings_failed, [])

    def test_no_camera_is_a_problem(self):
        os.environ["FAKE_DCC"] = "nocamera"
        check = camera_check()
        self.assertEqual(check.state, "problem")
        self.assertIn("not found", check.error)

    def test_wrong_transfer_mode_is_a_problem(self):
        os.environ["FAKE_DCC"] = "cameraonly"
        check = camera_check()
        self.assertEqual(check.state, "problem")
        self.assertIn("Save to PC only", check.error)

    def test_tool_errors_are_reported(self):
        camera = DigiCamControlCamera(threading.Event())
        with self.assertRaisesRegex(CameraError, "Unknow parameter"):
            camera.command("list", "transfer")

    def test_case_capture_names_files_like_the_mac(self):
        self.assert_case_saved()
        self.assertEqual(list((self.tmp / "out").rglob("_incoming")), [])

    def test_photo_without_raw_file_is_an_error(self):
        os.environ["FAKE_DCC"] = "jpegonly"
        with mock.patch.object(DigiCamControlCamera, "DOWNLOAD_TIMEOUT", 4):
            exit_code, lines = run_job(capture_case, PARENT)
        self.assertEqual(exit_code, 1)
        self.assertIn("RAW", lines[-1])


if __name__ == "__main__":
    unittest.main()

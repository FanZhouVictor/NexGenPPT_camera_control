# Capture jobs run against the fake camera tools in tests/fakes, so no camera is needed.
# The fakes are shell scripts, so these run on macOS and Linux only.
#
#   python -m unittest discover tests

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
from camera_control.capture.case_capture import capture_case
from camera_control.capture.case_rules import InvalidCase, check_case
from camera_control.capture.preflight import run_preflight
from camera_control.capture.run import CaptureRun

FAKES = Path(__file__).resolve().parent / "fakes"
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}-\d{6}")
CASE_ARGS = ["--test", "C187", "--coupon", "parent", "--treatment", "none", "--stage", "pre_exposure"]


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


class CaseRules(unittest.TestCase):
    def test_valid_cases(self):
        check_case("C187", "parent", "none", "pre_exposure")
        check_case("C187", "parent", "as_exposed", "post_exposure")
        check_case("C187", "parent", "env_aging_7d", "post_exposure_aged")
        check_case("C194", "left_center", "PER", "post_treatment")

    def test_invalid_cases(self):
        for case in [
            ("187", "parent", "none", "pre_exposure"),
            ("C187", "top", "none", "pre_exposure"),
            ("C187", "parent", "PER", "pre_exposure"),
            ("C187", "left", "env_aging_7d", "post_exposure_aged"),
            ("C187", "parent", "PER", "post_treatment"),
            ("C187", "left", "none", "pre_exposure"),
        ]:
            with self.subTest(case=case), self.assertRaises(InvalidCase):
                check_case(*case)


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
        exit_code, lines = run_job(capture_case, CASE_ARGS)
        self.assertEqual(exit_code, 0, lines[-3:])
        names = self.saved_names()
        self.assertEqual(len(names), 13)   # 4 photos x (CR3, JPG, log) + manifest
        self.assertIn("<time>-C187_parent_none_pre_exposure_0deg_r01.CR3", names)
        self.assertIn("<time>-C187_parent_none_pre_exposure_180deg_r02.JPG", names)
        manifest = json.loads(next((self.tmp / "out").rglob("case_manifest.json")).read_text())
        self.assertEqual([frame["rotation_deg"] for frame in manifest["frames"]], [0, 0, 180, 180])


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
            exit_code, lines = run_job(capture_case, CASE_ARGS)
        self.assertEqual(exit_code, 1)
        self.assertIn("RAW", lines[-1])


if __name__ == "__main__":
    unittest.main()

# One specimen alone on the paper: 2 photos at 0°, rotate 180°, 2 more photos.

import re

from camera_control.placement_guide import PlacementGuide
from camera_control.widgets import labeled_choice, labeled_entry, set_choices
from camera_control.workflows.capture_page import CapturePage

STAGES = {
    "Pre-exposure": "pre_exposure",
    "Post-exposure": "post_exposure",
    "Post-exposure, aged": "post_exposure_aged",
    "Post-treatment": "post_treatment",
}
COUPONS = {
    "Parent": "parent",
    "Left": "left",
    "Center": "center",
    "Right": "right",
    "Left + center": "left_center",
    "Center + right": "center_right",
    "Left + center + right": "left_center_right",
}
TREATMENTS = {
    "None": "none",
    "As exposed": "as_exposed",
    "Environmental aging": "env_aging",
    "PER": "PER",
    "Advanced cleaning": "advanced_cleaning",
}
AGING = "Environmental aging"

# Coupons and treatments each stage allows (same rules as capture/case_rules.py).
STRIPS = [coupon for coupon in COUPONS if coupon != "Parent"]
ALLOWED_BY_STAGE = {
    "Pre-exposure": (["Parent"], ["None"]),
    "Post-exposure": (["Parent"], ["As exposed"]),
    "Post-exposure, aged": (["Parent"], [AGING]),
    "Post-treatment": (STRIPS, ["As exposed", AGING, "PER", "Advanced cleaning"]),
}


class SingleSpecimenPage(CapturePage):
    job = "case"
    fields_title = "SPECIMEN"
    guide_title = "HOW TO PLACE IT"
    steps = [
        "Place the specimen label at the top, with all four edges on the white paper.",
        "Take 2 photos at 0°.",
        "Rotate the specimen 180°, then continue.",
        "Take 2 more photos at 180°.",
    ]

    def build_fields(self, parent):
        self.test_id = labeled_entry(parent, "Test ID", "e.g. C187", self.refresh)
        self.stage = labeled_choice(parent, "Stage", self._stage_changed)
        self.coupon = labeled_choice(parent, "Coupon", self.refresh)
        self.treatment = labeled_choice(parent, "Treatment", self._treatment_changed)
        self.aging_days = labeled_entry(parent, "Aging days", "Only for environmental aging", self.refresh)
        set_choices(self.stage, list(STAGES))
        self._apply_stage_rules()

    def build_guide(self, parent):
        return PlacementGuide(
            parent, self.steps, rotate_at=2,
            idle_caption="Specimen label at the top (0°). All four edges must be inside the white paper.",
        )

    def refresh(self):
        test_id = self.test_id.get().strip().upper()
        self.guide.set_specimen_label(test_id if re.fullmatch(r"C\d+", test_id) else "C187")
        super().refresh()

    def input_widgets(self):
        return [self.test_id, self.stage, self.coupon, self.treatment, self.aging_days]

    def _stage_changed(self):
        self._apply_stage_rules()
        self.refresh()

    def _treatment_changed(self):
        self.refresh_inputs()
        self.refresh()

    def _apply_stage_rules(self):
        coupons, treatments = ALLOWED_BY_STAGE[self.stage.get()]
        set_choices(self.coupon, coupons)
        set_choices(self.treatment, treatments)
        self.refresh_inputs()

    def refresh_inputs(self):
        if self.treatment.get() == AGING:
            self.aging_days.configure(state="normal")
        else:
            self.aging_days.delete(0, "end")
            self.aging_days.configure(state="disabled")

    def validate(self):
        test_id = self.test_id.get().strip().upper()
        if not test_id:
            return "Enter the test ID."
        if not re.fullmatch(r"C\d+", test_id):
            return "Test ID must look like C187."
        treatment = TREATMENTS[self.treatment.get()]
        if treatment == "env_aging":
            days = self.aging_days.get().strip()
            if not days.isdigit() or int(days) == 0:
                return "Enter the number of aging days."
            treatment = f"env_aging_{int(days)}d"
        coupon = COUPONS[self.coupon.get()]
        stage = STAGES[self.stage.get()]
        job_args = ["--test", test_id, "--coupon", coupon, "--treatment", treatment, "--stage", stage]
        return job_args, f"{test_id}_{coupon}_{treatment}_{stage}"

    def read_output(self, line):
        total = 4
        if ">>> capture rot 0° " in line:
            self.show_progress(1, 1, f"Taking photo {self.photos_taken} of {total}. Stand clear of the camera.")
        elif ">>> capture rot 180° " in line:
            self.show_progress(3, 3, f"Taking photo {self.photos_taken} of {total}. Stand clear of the camera.")
        elif "PAUSE" in line:
            self.wait_for_continue(
                2, 2, "Rotate the specimen 180° in place so its label is at the bottom. "
                "Keep all four edges inside the white paper and leave the ColorChecker where it is, "
                "then press Continue.",
            )

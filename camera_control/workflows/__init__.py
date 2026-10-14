# Every capture workflow the app offers, in sidebar order.
# To add one: write a CapturePage subclass in this folder and set it as `page` below.

from dataclasses import dataclass

from camera_control.workflows.single_specimen import SingleSpecimenPage


@dataclass(frozen=True)
class Workflow:
    key: str
    label: str
    description: str
    page: type | None = None


WORKFLOWS = [
    Workflow(
        "single_specimen", "One specimen",
        "A single piece alone on the paper · 4 photos, you rotate it halfway.",
        SingleSpecimenPage,
    ),
    Workflow(
        "batch_paper", "Batch paper",
        "Several numbered pieces on one paper · 2 photos, no rotation.",
    ),
    Workflow(
        "decon_wash_set", "Decon wash set",
        "Pieces 1–4 and the baseline, one at a time · 4 photos per piece.",
    ),
]

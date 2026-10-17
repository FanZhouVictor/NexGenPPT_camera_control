# Every capture workflow the app offers, in sidebar order.
# To add one: write a CapturePage subclass in this folder and set it as `page` below.

from dataclasses import dataclass

from camera_control.workflows.specimen_photos import SpecimenPhotosPage


@dataclass(frozen=True)
class Workflow:
    key: str
    label: str
    description: str
    page: type | None = None


WORKFLOWS = [
    Workflow(
        "specimen_photos", "Specimen photos",
        "A whole parent or one cut piece alone on the paper · 4 photos, you rotate it halfway.",
        SpecimenPhotosPage,
    ),
]

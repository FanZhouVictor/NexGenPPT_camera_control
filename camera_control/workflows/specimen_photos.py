# Photographing one specimen alone on the paper: a whole parent, one cut piece, or something else.
# The form asks what it is and what state it is in; follow-up questions appear only when an answer
# makes them apply, and no combination is ruled out. Each capture is 2 photos at 0°, a 180° turn,
# and 2 more.

import tkinter

import customtkinter as ctk
from camera_control import theme
from camera_control.capture.case_capture import output_root
from camera_control.capture.specimen import (
    UNITS, UNKNOWN, InvalidSpecimen, check_piece_names, check_specimen, default_piece_names, duration,
    folder_name, known_pieces, summary,
)
from camera_control.placement_guide import PlacementGuide
from camera_control.widgets import TypedChoice, choice_buttons, form_row, row_entry, row_menu, row_text
from camera_control.workflows.capture_page import CapturePage

OBJECTS = {"Parent": "parent", "Piece": "piece", "Other": "other"}
CONTAMINATION = {"Before": "before", "After": "after"}
YES_NO = {"Yes": "yes", "No": "no"}
WETNESS = {"Wet": "wet", "Damp": "damp", "Dry": "dry"}
ORDERS = {"Aged, then washed": "aged_then_washed", "Washed, then aged": "washed_then_aged"}
# Suggestions only: the operator can type any other wash condition.
WASH_CONDITIONS = ["PER", "Advanced cleaning"]
DEFAULT_PIECES = 3

STEPS = [
    "Place the specimen label at the top, with all four edges on the white paper.",
    "Take 2 photos at 0°.",
    "Rotate the specimen 180°, then continue.",
    "Take 2 more photos at 180°.",
]


class SpecimenPhotosPage(CapturePage):
    job = "case"
    steps = STEPS
    fields_title = "SPECIMEN"
    guide_title = "HOW TO PLACE IT"

    def build_fields(self, parent):
        # Scrolls when every follow-up question is showing at once.
        form = ctk.CTkScrollableFrame(
            parent, fg_color="transparent", scrollbar_button_color=theme.BORDER,
            scrollbar_button_hover_color=theme.STATUS_UNKNOWN,
        )
        form.pack(fill="both", expand=True)
        self.rows = []      # (row, shown) in form order; shown() says whether the row applies
        self.piece_buttons = {}   # piece name -> its button, left to right as the sample was cut
        self.piece = tkinter.StringVar(value="")   # the one piece on the paper

        row = self._row(form, "Sample ID")
        self.sample_id = row_entry(row, "Parent sample, e.g. C205", self._sample_changed)
        row = self._row(form, "Photographing")
        self.object = choice_buttons(row, list(OBJECTS), self.refresh)
        row = self._row(form, "Cut into", self._has_pieces, detail=True)
        self.pieces_total = row_entry(row, "", self._total_changed, width=44)
        self.pieces_total.insert(0, str(DEFAULT_PIECES))
        row_text(row, "pieces, named left to right:")
        row = self._row(form, "Piece names", self._has_pieces, detail=True)
        self.piece_names = row_entry(row, "P1, P2, P3", self._names_changed)
        self.piece_names.insert(0, ", ".join(default_piece_names(DEFAULT_PIECES)))
        row = self._row(form, "Which piece", self._has_pieces, detail=True)
        self.piece_choices = ctk.CTkFrame(row, fg_color="transparent")
        self.piece_choices.pack(side="left")
        row = self._row(form, "What is it", lambda: self._object() == "other", detail=True)
        self.description = row_entry(row, "e.g. final small piece", self.refresh)

        heading = ctk.CTkFrame(form, fg_color="transparent")
        ctk.CTkLabel(
            heading, text="CONDITION NOW", font=theme.font(12, bold=True), text_color=theme.TEXT_MUTED, anchor="w",
        ).pack(fill="x", pady=(8, 0))
        self.rows.append((heading, lambda: True))

        row = self._row(form, "Contamination")
        self.contamination = choice_buttons(row, list(CONTAMINATION), self.refresh)
        row = self._row(form, "Aged")
        self.aged = choice_buttons(row, list(YES_NO), self.refresh)
        row = self._row(form, "Aged for", self._is_aged, detail=True)
        self.aged_for, self.aged_for_unit = self._time(row, "days", "")
        row = self._row(form, "Washed")
        self.washed = choice_buttons(row, list(YES_NO), self.refresh)
        row = self._row(form, "Wash condition", self._is_washed, detail=True)
        self.wash_condition = self._typed_choice(row, WASH_CONDITIONS)
        row = self._row(form, "Wash ended", self._is_washed, detail=True)
        self.since_wash, self.since_wash_unit = self._time(row, "hours", "ago")
        row = self._row(form, "Now it is", self._is_washed, detail=True)
        self.wetness = choice_buttons(row, list(WETNESS), self.refresh)
        row = self._row(form, "Order", lambda: self._is_aged() and self._is_washed(), detail=True)
        self.order = self._typed_choice(row, list(ORDERS))

        row = self._row(form, "Notes")
        self.notes = row_entry(row, "Optional", self.refresh)

        self._build_piece_buttons(default_piece_names(DEFAULT_PIECES))

    def _row(self, form, label, shown=lambda: True, detail=False):
        row = form_row(form, label, detail)
        self.rows.append((row, shown))
        return row

    def _time(self, row, unit, after):
        # A number and its unit. Left empty, the time is saved as unknown.
        entry = row_entry(row, "unknown", self.refresh, width=76)
        menu = row_menu(row, UNITS, self.refresh)
        menu.set(unit)
        if after:
            row_text(row, after)
        return entry, menu

    def _typed_choice(self, row, values):
        box = TypedChoice(row, values, "Type here or select", self.refresh)
        box.pack(side="left", fill="x", expand=True)
        return box

    def build_guide(self, parent):
        return PlacementGuide(
            parent, STEPS, rotate_at=2,
            idle_caption="Specimen label at the top (0°). All four edges must be inside the white paper.",
        )

    # What the form says

    def _object(self):
        return OBJECTS.get(self.object.get())

    def _has_pieces(self):
        return self._object() == "piece"

    def _is_aged(self):
        return self.aged.get() == "Yes"

    def _is_washed(self):
        return self.washed.get() == "Yes"

    def _total(self):
        text = self.pieces_total.get().strip()
        return int(text) if text.isdigit() and 2 <= int(text) <= 12 else None

    def _typed_names(self):
        return [name.strip() for name in self.piece_names.get().split(",") if name.strip()]

    def _specimen(self):
        # The answers as saved in case_manifest.json. Raises InvalidSpecimen for names or times that don't fit.
        kind = self._object()
        is_piece = kind == "piece"
        if is_piece and self._total():
            check_piece_names(self._typed_names(), self._total())
        aged, washed = self._is_aged(), self._is_washed()
        order = self.order.get().strip()
        return {
            "sample_id": self.sample_id.get().strip().upper(),
            "object": kind,
            "piece": (self.piece.get() or None) if is_piece else None,
            "pieces_total": self._total() if is_piece else None,
            "piece_names": list(self.piece_buttons) if is_piece else None,
            "description": self.description.get().strip() if kind == "other" else None,
            "contamination": CONTAMINATION.get(self.contamination.get()),
            "aged": YES_NO.get(self.aged.get()),
            "aged_for": duration(self.aged_for.get(), self.aged_for_unit.get()) if aged else None,
            "washed": YES_NO.get(self.washed.get()),
            "wash_condition": (self.wash_condition.get().strip() or UNKNOWN) if washed else None,
            "since_wash": duration(self.since_wash.get(), self.since_wash_unit.get()) if washed else None,
            "wetness": WETNESS.get(self.wetness.get()) if washed else None,
            "order": (ORDERS.get(order, order) or None) if aged and washed else None,
            "notes": self.notes.get().strip(),
        }

    def validate(self):
        try:
            specimen = self._specimen()
            check_specimen(specimen)
        except InvalidSpecimen as problem:
            return str(problem)
        return specimen, folder_name(specimen), summary(specimen)

    # Keeping the form in step with the answers

    def refresh(self):
        if not self.run:
            self._show_rows()
            # A cut piece is drawn at its share of the parent's width, labelled with its name.
            if self._has_pieces():
                self.guide.set_specimen(self.piece.get() or "?", 1 / (self._total() or 1))
            else:
                self.guide.set_specimen(self.sample_id.get().strip().upper() or "C205")
        super().refresh()

    def _show_rows(self):
        wanted = [row for row, shown in self.rows if shown()]
        if wanted != getattr(self, "showing", None):
            for row, _ in self.rows:
                row.pack_forget()
            for row in wanted:
                row.pack(fill="x", pady=2)
            self.showing = wanted

    def _sample_changed(self):
        # A sample seen before gets back its piece count and names; any other sample starts from
        # P1, P2, ... so names typed for one sample never carry over to the next.
        known = known_pieces(output_root(), self.sample_id.get().strip().upper())
        names = known or default_piece_names(self._total() or DEFAULT_PIECES)
        if names != list(self.piece_buttons):
            self._show_names(names)
        self.refresh()

    def _total_changed(self):
        # A new count starts the names again from P1, P2, ...
        total = self._total()
        if total:
            self._show_names(default_piece_names(total))
        self.refresh()

    def _show_names(self, names):
        self._set_entry(self.pieces_total, str(len(names)))
        self._set_entry(self.piece_names, ", ".join(names))
        self._build_piece_buttons(names)

    def _names_changed(self):
        names = self._typed_names()
        try:
            check_piece_names(names, self._total() or 0)
        except InvalidSpecimen:
            self.refresh()   # says what is wrong with the names; the piece buttons stay as they were
            return
        if names != list(self.piece_buttons):
            self._build_piece_buttons(names)
        self.refresh()

    def _set_entry(self, entry, text):
        entry.delete(0, "end")
        entry.insert(0, text)

    def _build_piece_buttons(self, names):
        # A renamed piece keeps its place, and stays chosen if it was.
        old = list(self.piece_buttons)
        chosen = old.index(self.piece.get()) if self.piece.get() in old else None
        for button in self.piece_buttons.values():
            button.destroy()
        self.piece_buttons = {}
        per_line = 4 if max(map(len, names)) <= 3 else 2
        for index, piece in enumerate(names):
            button = ctk.CTkRadioButton(
                self.piece_choices, text=piece, value=piece, variable=self.piece, width=54, height=24,
                radiobutton_width=18, radiobutton_height=18, font=theme.font(13), command=self.refresh,
            )
            button.grid(row=index // per_line, column=index % per_line, pady=2, padx=(0, 6), sticky="w")
            self.piece_buttons[piece] = button
        self.piece.set(names[chosen] if chosen is not None and chosen < len(names) else "")

    def input_widgets(self):
        return [
            self.sample_id, self.object, self.pieces_total, self.piece_names, *self.piece_buttons.values(),
            self.description, self.contamination, self.aged, self.aged_for, self.aged_for_unit,
            self.washed, self.wash_condition, self.since_wash, self.since_wash_unit, self.wetness, self.order,
            self.notes,
        ]

    def typed_choices(self):
        return [self.wash_condition, self.order]

    def read_output(self, line):
        if ">>> capture rot 0° " in line:
            self.show_progress(1, 1, f"Taking photo {self.photos_taken} of 4. Stand clear of the camera.")
        elif ">>> capture rot 180° " in line:
            self.show_progress(3, 3, f"Taking photo {self.photos_taken} of 4. Stand clear of the camera.")
        elif "PAUSE" in line:
            self.wait_for_continue(
                2, 2, "Rotate the specimen 180° in place so its label is at the bottom. "
                "Keep all four edges inside the white paper and leave the ColorChecker where it is, "
                "then press Continue.",
            )

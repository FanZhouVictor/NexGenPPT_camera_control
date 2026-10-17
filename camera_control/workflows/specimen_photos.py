# Photographing specimens. The form asks what is on the paper and what state it is in;
# follow-up questions appear only when an answer makes them apply, and no combination is ruled out.
#
# One specimen alone (a whole parent, one cut piece, or something else) gets 2 photos at 0°,
# a 180° turn, and 2 more. Several pieces of one sample in the same picture get 2 photos at 0°;
# each piece can have its own condition.

import re

import customtkinter as ctk
from camera_control import theme
from camera_control.capture.case_capture import output_root
from camera_control.capture.specimen import (
    UNITS, UNKNOWN, InvalidSpecimen, batch_folder_name, batch_summary, check_batch, check_piece_names,
    check_specimen, default_piece_names, duration, folder_name, known_pieces, summary,
)
from camera_control.placement_guide import PlacementGuide
from camera_control.widgets import TypedChoice, choice_buttons, form_row, row_entry, row_menu, row_text
from camera_control.workflows.capture_page import CapturePage

OBJECTS = {"Parent": "parent", "Pieces": "piece", "Other": "other"}
CONTAMINATION = {"Before": "before", "After": "after"}
YES_NO = {"Yes": "yes", "No": "no"}
WETNESS = {"Wet": "wet", "Damp": "damp", "Dry": "dry"}
ORDERS = {"Aged, then washed": "aged_then_washed", "Washed, then aged": "washed_then_aged"}
# Suggestions only: the operator can type any other wash condition.
WASH_CONDITIONS = ["PER", "Advanced cleaning"]
DEFAULT_PIECES = 4
ALL = "All"

STEPS = [
    "Place the specimen label at the top, with all four edges on the white paper.",
    "Take 2 photos at 0°.",
    "Rotate the specimen 180°, then continue.",
    "Take 2 more photos at 180°.",
]
BATCH_STEPS = [
    "Place the pieces left to right in this order, labels at the top.",
    "Take 2 photos at 0°. The pieces are not rotated.",
]


class SpecimenPhotosPage(CapturePage):
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
        self.boxes = {}     # piece name -> its tick box, left to right as the sample was cut
        # When pieces in one picture have different conditions: each piece's answers, and the
        # piece whose answers the form is showing. Empty while one set of answers covers them all.
        self.own, self.editing = {}, None

        row = self._row(form, "Sample ID")
        self.sample_id = row_entry(row, "Parent sample, e.g. C205", self._sample_changed)
        row = self._row(form, "Photographing")
        self.object = choice_buttons(row, list(OBJECTS), self._pieces_ticked)
        row = self._row(form, "Cut into", self._has_pieces, detail=True)
        self.pieces_total = row_entry(row, "", self._total_changed, width=44)
        self.pieces_total.insert(0, str(DEFAULT_PIECES))
        row_text(row, "pieces, named left to right:")
        row = self._row(form, "Piece names", self._has_pieces, detail=True)
        self.piece_names = row_entry(row, "P1, P2, P3, P4", self._names_changed)
        self.piece_names.insert(0, ", ".join(default_piece_names(DEFAULT_PIECES)))
        row = self._row(form, "On the paper", self._has_pieces, detail=True)
        self.piece_boxes = ctk.CTkFrame(row, fg_color="transparent")
        self.piece_boxes.pack(side="left")
        row = self._row(form, "What is it", lambda: self._object() == "other", detail=True)
        self.description = row_entry(row, "e.g. final small piece", self.refresh)

        heading = ctk.CTkFrame(form, fg_color="transparent")
        ctk.CTkLabel(
            heading, text="CONDITION NOW", font=theme.font(12, bold=True), text_color=theme.TEXT_MUTED, anchor="w",
        ).pack(fill="x", pady=(8, 0))
        self.rows.append((heading, lambda: True))

        row = self._row(form, "Condition of", self._is_batch, detail=True)
        self.condition_of = choice_buttons(row, [ALL], self._condition_of_changed)
        self.condition_of.set(ALL)
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

        self._build_piece_boxes(default_piece_names(DEFAULT_PIECES))

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
        return PlacementGuide(parent, STEPS, rotate_at=2, idle_caption="")

    # Which capture the answers lead to

    @property
    def job(self):
        return "batch" if self._is_batch() else "case"

    @property
    def steps(self):
        return BATCH_STEPS if self._is_batch() else STEPS

    def _object(self):
        return OBJECTS.get(self.object.get())

    def _has_pieces(self):
        return self._object() == "piece"

    def _on_paper(self):
        # The ticked pieces, left to right.
        return [piece for piece, box in self.boxes.items() if box.get()]

    def _is_batch(self):
        return self._has_pieces() and len(self._on_paper()) >= 2

    def _is_aged(self):
        return self.aged.get() == "Yes"

    def _is_washed(self):
        return self.washed.get() == "Yes"

    def _total(self):
        text = self.pieces_total.get().strip()
        return int(text) if text.isdigit() and 2 <= int(text) <= 12 else None

    # Reading the form

    def _answers(self):
        # The condition answers exactly as the form shows them.
        return {
            "contamination": self.contamination.get(),
            "aged": self.aged.get(), "aged_for": self.aged_for.get(), "aged_for_unit": self.aged_for_unit.get(),
            "washed": self.washed.get(), "wash_condition": self.wash_condition.get(),
            "since_wash": self.since_wash.get(), "since_wash_unit": self.since_wash_unit.get(),
            "wetness": self.wetness.get(), "order": self.order.get(),
        }

    def _show_answers(self, answers):
        for key, buttons in [("contamination", self.contamination), ("aged", self.aged),
                             ("washed", self.washed), ("wetness", self.wetness)]:
            buttons.set(answers[key])
        for entry, key in ((self.aged_for, "aged_for"), (self.since_wash, "since_wash")):
            entry.delete(0, "end")
            entry.insert(0, answers[key])
        self.aged_for_unit.set(answers["aged_for_unit"])
        self.since_wash_unit.set(answers["since_wash_unit"])
        self.wash_condition.set(answers["wash_condition"])
        self.order.set(answers["order"])
        self.focus_set()   # an emptied entry only shows its "unknown" hint once it loses focus

    def _condition(self, answers):
        # As saved in case_manifest.json. Raises InvalidSpecimen for a time that isn't a number.
        aged, washed = answers["aged"] == "Yes", answers["washed"] == "Yes"
        order = answers["order"].strip()
        return {
            "contamination": CONTAMINATION.get(answers["contamination"]),
            "aged": YES_NO.get(answers["aged"]),
            "aged_for": duration(answers["aged_for"], answers["aged_for_unit"]) if aged else None,
            "washed": YES_NO.get(answers["washed"]),
            "wash_condition": (answers["wash_condition"].strip() or UNKNOWN) if washed else None,
            "since_wash": duration(answers["since_wash"], answers["since_wash_unit"]) if washed else None,
            "wetness": WETNESS.get(answers["wetness"]) if washed else None,
            "order": (ORDERS.get(order, order) or None) if aged and washed else None,
        }

    def _typed_names(self):
        return [name.strip() for name in self.piece_names.get().split(",") if name.strip()]

    def _record(self):
        sample_id, notes = self.sample_id.get().strip().upper(), self.notes.get().strip()
        on_paper = self._on_paper()
        names = list(self.boxes)
        if self._has_pieces() and self._total():
            check_piece_names(self._typed_names(), self._total())
        if self._is_batch():
            pieces = []
            for position, piece in enumerate(on_paper, start=1):
                answers = self.own[piece] if self.own and piece != self.editing else self._answers()
                try:
                    pieces.append({"piece": piece, "position": position, **self._condition(answers)})
                except InvalidSpecimen as problem:
                    raise InvalidSpecimen(f"{piece}: {problem}")
            return {
                "sample_id": sample_id, "object": "pieces", "pieces_total": self._total(),
                "piece_names": names, "pieces": pieces, "notes": notes,
            }
        kind = self._object()
        return {
            "sample_id": sample_id,
            "object": kind,
            "piece": on_paper[0] if kind == "piece" and on_paper else None,
            "pieces_total": self._total() if kind == "piece" else None,
            "piece_names": names if kind == "piece" else None,
            "description": self.description.get().strip() if kind == "other" else None,
            **self._condition(self._answers()),
            "notes": notes,
        }

    def validate(self):
        try:
            record = self._record()
            if record["object"] == "pieces":
                check_batch(record)
                return record, batch_folder_name(record), batch_summary(record)
            check_specimen(record)
            return record, folder_name(record), summary(record)
        except InvalidSpecimen as problem:
            # Problems in a batch name the piece, which only helps when pieces have their own answers.
            return str(problem) if self.own else re.sub(r"^[A-Za-z0-9]+: ", "", str(problem))

    # Keeping the form in step with the answers

    def refresh(self):
        if not self.run:
            self._show_rows()
            sample = self.sample_id.get().strip().upper() or "C205"
            on_paper = self._on_paper()
            share = 1 / self._total() if self._has_pieces() and self._total() else 1
            alone = "Specimen label at the top (0°). All four edges must be inside the white paper."
            if self._is_batch():
                self.guide.set_layout(on_paper, BATCH_STEPS, None, f"{len(on_paper)} pieces, left to right: "
                                      f"{', '.join(on_paper)}. Labels at the top.", share)
            elif self._has_pieces():
                self.guide.set_layout(on_paper or ["?"], STEPS, 2, alone, share)
            else:
                self.guide.set_layout([sample], STEPS, 2, alone)
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
        # What a sample was cut into only has to be entered the first time.
        known = known_pieces(output_root(), self.sample_id.get().strip().upper())
        if known and known != list(self.boxes):
            self._set_entry(self.pieces_total, str(len(known)))
            self._set_entry(self.piece_names, ", ".join(known))
            self._build_piece_boxes(known)
            self._pieces_ticked()
        else:
            self.refresh()

    def _total_changed(self):
        # Keeps the names already there and adds or drops pieces at the right-hand end.
        total = self._total()
        if total:
            names = (list(self.boxes) + default_piece_names(total)[len(self.boxes):])[:total]
            self._set_entry(self.piece_names, ", ".join(names))
            self._build_piece_boxes(names)
        self._pieces_ticked()

    def _names_changed(self):
        names = self._typed_names()
        try:
            check_piece_names(names, self._total() or 0)
        except InvalidSpecimen:
            self.refresh()   # says what is wrong with the names; the tick boxes stay as they were
            return
        if names != list(self.boxes):
            self._build_piece_boxes(names)
        self._pieces_ticked()

    def _set_entry(self, entry, text):
        entry.delete(0, "end")
        entry.insert(0, text)

    def _build_piece_boxes(self, names):
        # A renamed piece keeps its place, its tick and its own answers.
        old = list(self.boxes)
        ticked = [index for index, box in enumerate(self.boxes.values()) if box.get()]
        renamed = dict(zip(old, names))
        self.own = {renamed[piece]: answers for piece, answers in self.own.items() if piece in renamed}
        self.editing = renamed.get(self.editing)
        for box in self.boxes.values():
            box.destroy()
        self.boxes = {}
        per_line = 4 if max(map(len, names)) <= 3 else 2
        for index, piece in enumerate(names):
            box = ctk.CTkCheckBox(
                self.piece_boxes, text=piece, width=54, height=24, checkbox_width=18, checkbox_height=18,
                font=theme.font(13), command=self._pieces_ticked,
            )
            box.grid(row=index // per_line, column=index % per_line, pady=2, padx=(0, 6), sticky="w")
            if index in ticked:
                box.select()
            self.boxes[piece] = box

    def _pieces_ticked(self):
        on_paper = self._on_paper() if self._has_pieces() else []
        if len(on_paper) < 2:
            self.own, self.editing = {}, None
        elif self.own:
            # A piece added to the paper starts from the answers on screen.
            shown = self._answers()
            if self.editing:
                self.own[self.editing] = shown
            self.own = {piece: self.own.get(piece, shown) for piece in on_paper}
            if self.editing not in on_paper:
                self.editing = on_paper[0]
                self._show_answers(self.own[self.editing])
        self.condition_of.configure(values=[ALL, *on_paper])
        self.condition_of.set(self.editing or ALL)
        self.refresh()

    def _condition_of_changed(self):
        piece = self.condition_of.get()
        if piece == ALL:
            # The answers on screen now cover every piece.
            self.own, self.editing = {}, None
        else:
            if self.own:
                self.own[self.editing] = self._answers()
            else:
                # Every piece starts from the shared answers, then is changed where it differs.
                self.own = {each: self._answers() for each in self._on_paper()}
            self.editing = piece
            self._show_answers(self.own[piece])
        self.refresh()

    def input_widgets(self):
        return [
            self.sample_id, self.object, self.pieces_total, self.piece_names, *self.boxes.values(),
            self.description,
            self.condition_of, self.contamination, self.aged, self.aged_for, self.aged_for_unit,
            self.washed, self.wash_condition, self.since_wash, self.since_wash_unit, self.wetness, self.order,
            self.notes,
        ]

    def typed_choices(self):
        return [self.wash_condition, self.order]

    def read_output(self, line):
        if self._is_batch():
            if ">>> capture rot 0° " in line:
                self.show_progress(1, 1, f"Taking photo {self.photos_taken} of 2 · {len(self._on_paper())} pieces "
                                   "in the picture. Stand clear of the camera.")
        elif ">>> capture rot 0° " in line:
            self.show_progress(1, 1, f"Taking photo {self.photos_taken} of 4. Stand clear of the camera.")
        elif ">>> capture rot 180° " in line:
            self.show_progress(3, 3, f"Taking photo {self.photos_taken} of 4. Stand clear of the camera.")
        elif "PAUSE" in line:
            self.wait_for_continue(
                2, 2, "Rotate the specimen 180° in place so its label is at the bottom. "
                "Keep all four edges inside the white paper and leave the ColorChecker where it is, "
                "then press Continue.",
            )

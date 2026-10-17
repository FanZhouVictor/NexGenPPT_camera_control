# Drawing of how to place a specimen on the rig, with a caption for the current step.
# The specimen turns 180° from `rotate_at` onwards; the ColorChecker never moves.

import tkinter as tk

import customtkinter as ctk
from camera_control import theme

BACKDROP = "#C7D8F2"        # BWblue broadcloth under the sheet
SHEET = "#FFFFFF"           # A3 paper
SHEET_EDGE = "#CBD5E1"
FABRIC = "#E8DCC8"
FABRIC_EDGE = "#A8977C"

# ColorChecker Classic as it stands in the photos: upright, row by row from the top.
COLORCHECKER = [
    ["#67BDAA", "#E0A32E", "#0885A1", "#343434"],
    ["#8580B1", "#9DBC40", "#BB5695", "#555555"],
    ["#576C43", "#5E3C6C", "#E7C71F", "#7A7A79"],
    ["#627A9D", "#C15A63", "#AF363C", "#A0A0A0"],
    ["#C29682", "#505BA6", "#469449", "#C8C8C8"],
    ["#735244", "#D67E2C", "#383D96", "#F3F3F2"],
]

WIDTH, HEIGHT = 300, 190


class PlacementGuide(ctk.CTkFrame):
    def __init__(self, master, steps, rotate_at, idle_caption):
        super().__init__(master, fg_color="transparent")
        self.steps = steps
        self.rotate_at = rotate_at
        self.idle_caption = idle_caption
        self.specimen_label = "C205"
        self.share = 1

        self.canvas = tk.Canvas(self, width=WIDTH, height=HEIGHT, bg=theme.CARD, highlightthickness=0)
        self.canvas.pack(anchor="w")
        self.step_label = ctk.CTkLabel(self, font=theme.font(13, bold=True), text_color=theme.PRIMARY, anchor="w")
        self.step_label.pack(fill="x", pady=(8, 0))
        self.caption = ctk.CTkLabel(
            self, font=theme.font(14), anchor="w", justify="left", wraplength=WIDTH,
        )
        self.caption.pack(fill="x")
        self.show(done=0)

    def show(self, done, current=None):
        total = len(self.steps)
        if done >= total:
            self._draw_rig(rotated=True, rotating=False)
            self.step_label.configure(text="All steps done")
            self.caption.configure(text="Stage the next specimen: label at the top, all four edges on the white paper.")
        elif current is None:
            self._draw_rig(rotated=False, rotating=False)
            self.step_label.configure(text=f"{total} steps")
            self.caption.configure(text=self.idle_caption)
        else:
            self._draw_rig(rotated=current >= self.rotate_at, rotating=current == self.rotate_at)
            self.step_label.configure(text=f"Step {current + 1} of {total}")
            self.caption.configure(text=self.steps[current])

    def set_specimen(self, label, share=1):
        # label: what is written on the specimen, e.g. "C205" or "P2"; drawn upside down once rotated.
        # share: how much of the parent's width it has; a piece cut from 4 has 1/4.
        self.specimen_label, self.share = label, share

    def _draw_rig(self, rotated, rotating):
        # Proportions follow a real capture: the A3 sheet fills most of the frame, the specimen
        # almost fills the sheet, and the ColorChecker card stands on the backdrop to its right.
        c = self.canvas
        c.delete("all")
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill=BACKDROP, width=0)

        sheet = (12, 18, 230, 172)
        c.create_rectangle(*sheet, fill=SHEET, outline=SHEET_EDGE)

        # The specimen's label sits on its top edge, with the TOP arrow pointing at it.
        # After rotating, both are at the bottom and the label is upside down.
        # A cut piece is drawn at its real share of the parent's width, in the middle of the paper.
        x0, y0, x1, y1 = sheet[0] + 5, sheet[1] + 5, sheet[2] - 5, sheet[3] - 5
        centre, middle = (y0 + y1) / 2, (x0 + x1) / 2
        width = (x1 - x0) * self.share
        c.create_rectangle(middle - width / 2, y0, middle + width / 2, y1, fill=FABRIC, outline=FABRIC_EDGE, width=2)
        top_text = width >= 40
        if rotated:
            c.create_text(middle, y1 - 14, text=self.specimen_label, angle=180, font=theme.font(10), fill=FABRIC_EDGE)
            c.create_line(middle, y1 - 50, middle, y1 - 28, arrow=tk.LAST, width=2, fill=theme.TEXT)
            if top_text:
                c.create_text(middle, y1 - 60, text="TOP", font=theme.font(11, bold=True), fill=theme.TEXT)
        else:
            c.create_text(middle, y0 + 14, text=self.specimen_label, font=theme.font(10), fill=FABRIC_EDGE)
            c.create_line(middle, y0 + 50, middle, y0 + 28, arrow=tk.LAST, width=2, fill=theme.TEXT)
            if top_text:
                c.create_text(middle, y0 + 60, text="TOP", font=theme.font(11, bold=True), fill=theme.TEXT)

        patch, gap = 8, 2
        card_width = 4 * (patch + gap) + gap
        card_height = 6 * (patch + gap) + gap
        left = (sheet[2] + WIDTH) / 2 - card_width / 2
        top = centre - card_height / 2 - 4
        c.create_text(left + card_width / 2, top - 9, text="ColorChecker", font=theme.font(8), fill=theme.TEXT)
        c.create_rectangle(left, top, left + card_width, top + card_height, fill="#1F1F1F", width=0)
        for row, colours in enumerate(COLORCHECKER):
            for column, colour in enumerate(colours):
                x = left + gap + column * (patch + gap)
                y = top + gap + row * (patch + gap)
                c.create_rectangle(x, y, x + patch, y + patch, fill=colour, width=0)

        if rotating:
            side = x0 + (x1 - x0) / 4
            c.create_text(side, centre - 8, text="↻", font=theme.font(26, bold=True), fill=theme.PRIMARY)
            c.create_text(side, centre + 18, text="180°", font=theme.font(10, bold=True), fill=theme.PRIMARY)

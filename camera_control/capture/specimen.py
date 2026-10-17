# What is being photographed: the answers from the specimen form, and what is built from them.
#
# A specimen is a plain dict, saved as it is into case_manifest.json:
#   sample_id            "C205"                       the parent sample's ID
#   object               "parent" | "piece" | "other"
#   piece                "P2"                         its name, fixed by where it was cut
#   pieces_total         4
#   piece_names          ["P1", "P2", "P3", "P4"]     left to right as cut; the operator can rename them
#   description          what it is, for object "other"
#   notes                free text
# plus its condition:
#   contamination        "before" | "after"
#   aged                 "yes" | "no"
#   aged_for             duration
#   washed               "yes" | "no"
#   wash_condition       "PER", or "unknown"
#   since_wash           duration since the last wash ended
#   wetness              "wet" | "damp" | "dry"
#   order                "aged_then_washed" | "washed_then_aged" | a short description
# A duration is {"value": 6.0, "unit": "hours"}, or "unknown" when the time was left empty.
# None means the question did not apply.

import json
import math
import re

UNKNOWN = "unknown"
UNITS = ["minutes", "hours", "days"]
OBJECTS = ["parent", "piece", "other"]
ORDERS = {"aged_then_washed": "aged, then washed", "washed_then_aged": "washed, then aged"}


class InvalidSpecimen(ValueError):
    pass


def duration(text, unit):
    # "" -> "unknown", "1.5" -> {"value": 1.5, "unit": unit}.
    text = text.strip().replace(",", ".")
    if not text:
        return UNKNOWN
    try:
        value = float(text)
    except ValueError:
        value = math.nan
    if not math.isfinite(value) or value < 0:
        raise InvalidSpecimen("Times must be numbers, like 6 or 1.5. Leave a time empty if you don't know it.")
    return {"value": value, "unit": unit}


# Checks: each raises InvalidSpecimen saying what is still missing or wrong.

def check_specimen(specimen):
    _check_sample_id(specimen)
    kind = specimen.get("object")
    if kind not in OBJECTS:
        raise InvalidSpecimen("Choose what you are photographing.")
    if kind == "piece":
        _check_piece(specimen.get("piece"), piece_names(specimen))
    if kind == "other" and not specimen.get("description"):
        raise InvalidSpecimen("Describe what you are photographing.")
    check_condition(specimen)


def check_condition(condition):
    for key, answers, question in [
        ("contamination", ["before", "after"], "Choose before or after contamination."),
        ("aged", ["yes", "no"], "Choose whether it was aged."),
        ("washed", ["yes", "no"], "Choose whether it was washed."),
    ]:
        if condition.get(key) not in answers:
            raise InvalidSpecimen(question)
    if condition["washed"] == "yes" and condition.get("wetness") not in ["wet", "damp", "dry"]:
        raise InvalidSpecimen("Choose how wet it is now.")
    if condition["aged"] == "yes" and condition["washed"] == "yes" and not condition.get("order"):
        raise InvalidSpecimen("Choose whether it was aged or washed first.")


def _check_sample_id(record):
    sample_id = record.get("sample_id") or ""
    if not sample_id:
        raise InvalidSpecimen("Enter the sample ID.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", sample_id):
        raise InvalidSpecimen("Sample ID can only have letters, numbers and dashes, like C205.")


def _pieces_total(record):
    total = record.get("pieces_total")
    if not isinstance(total, int) or total < 2:
        raise InvalidSpecimen("Enter how many pieces the sample was cut into.")
    return total


def default_piece_names(total):
    return [f"P{number}" for number in range(1, total + 1)]


def piece_names(record):
    # The sample's pieces, left to right as they were cut: P1, P2, ... unless renamed.
    total = _pieces_total(record)
    names = record.get("piece_names") or default_piece_names(total)
    check_piece_names(names, total)
    return names


def check_piece_names(names, total):
    # Names go into file names, and "-" joins them there, so letters and numbers only.
    proper = all(re.fullmatch(r"[A-Za-z0-9]{1,8}", name) for name in names)
    if len(names) != total or not proper or len({name.lower() for name in names}) != total:
        raise InvalidSpecimen(f"Enter {total} different piece names: letters and numbers only, up to 8 each.")


def _check_piece(piece, names):
    if piece not in names:
        raise InvalidSpecimen("Choose which piece is on the paper.")


# Names. Photo files say the sample and piece; the capture's folder also says the condition,
# so folders can be told apart at a glance: "C205_P2_contam_aged7d_washed".

def specimen_name(specimen):
    # "C205_parent", "C205_P2", "C205_other".
    part = specimen["piece"] if specimen["object"] == "piece" else specimen["object"]
    return f"{specimen['sample_id']}_{part}"


def folder_name(specimen):
    return "_".join([specimen_name(specimen), *_tags(specimen)])


def _tags(condition):
    tags = ["clean" if condition["contamination"] == "before" else "contam"]
    if condition["aged"] == "yes":
        time = condition.get("aged_for")
        short = {"minutes": "min", "hours": "h", "days": "d"}
        tags.append(f"aged{time['value']:g}{short[time['unit']]}" if isinstance(time, dict) else "aged")
    if condition["washed"] == "yes":
        tags.append("washed")
    return tags


# Summaries: what the operator checks before shooting.

def summary(specimen):
    # "C205 · P2 · after contamination · aged 7 days · 6 hours after wash (PER) · dry · aged, then washed"
    kind = specimen["object"]
    what = {"parent": "whole parent", "piece": specimen.get("piece")}.get(kind) or specimen["description"]
    return " · ".join([specimen["sample_id"], what, *_condition_parts(specimen)])


def _condition_parts(condition):
    parts = [f"{condition['contamination']} contamination"]
    aged = condition["aged"] == "yes"
    parts.append(" ".join(filter(None, ["aged", _spoken(condition.get("aged_for"))])) if aged else "not aged")
    if condition["washed"] == "yes":
        since = _spoken(condition.get("since_wash"))
        wash = f"{since} after wash" if since else "washed"
        kind = condition.get("wash_condition")
        parts.append(f"{wash} ({kind})" if kind and kind != UNKNOWN else wash)
        parts.append(condition["wetness"])
        if aged:
            parts.append(ORDERS.get(condition["order"], condition["order"]))
    else:
        parts.append("not washed")
    return parts


def _spoken(time):
    # {"value": 6.0, "unit": "hours"} -> "6 hours". Nothing for an unknown time.
    if not isinstance(time, dict):
        return ""
    unit = time["unit"][:-1] if time["value"] == 1 else time["unit"]
    return f"{time['value']:g} {unit}"


# What each sample was cut into, so it only has to be entered once per sample.

def known_pieces(root, sample_id):
    # The sample's piece names, left to right, or None for a sample not seen before.
    return _read_samples(root).get(sample_id, {}).get("piece_names")


def remember_pieces(root, sample_id, names):
    samples = _read_samples(root)
    if samples.get(sample_id, {}).get("piece_names") != names:
        samples[sample_id] = {"piece_names": names}
        root.mkdir(parents=True, exist_ok=True)
        (root / "samples.json").write_text(json.dumps(samples, indent=2, sort_keys=True) + "\n")


def _read_samples(root):
    try:
        samples = json.loads((root / "samples.json").read_text())
    except (OSError, ValueError):
        return {}
    return samples if isinstance(samples, dict) else {}

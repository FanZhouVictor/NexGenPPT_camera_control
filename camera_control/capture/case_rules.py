# Which (test, coupon, treatment, stage) combinations are valid.

import re

COUPONS = ["parent", "left", "center", "right", "left_center", "center_right", "left_center_right"]
STAGES = ["pre_exposure", "post_exposure", "post_exposure_aged", "post_treatment"]


class InvalidCase(ValueError):
    pass


def check_case(test, coupon, treatment, stage):
    # Raises InvalidCase saying what is wrong.
    if not re.fullmatch(r"C[0-9]+", test or ""):
        raise InvalidCase("--test required, format Cxxx")
    if coupon not in COUPONS:
        raise InvalidCase("--coupon: parent|left|center|right | left_center|center_right|left_center_right")
    if not re.fullmatch(r"as_exposed|env_aging_[0-9]+d|PER|advanced_cleaning|none", treatment or ""):
        raise InvalidCase("--treatment: as_exposed | env_aging_<N>d | PER | advanced_cleaning | none")
    if stage not in STAGES:
        raise InvalidCase("--stage: pre_exposure|post_exposure|post_exposure_aged|post_treatment")

    if stage == "pre_exposure" and treatment != "none":
        raise InvalidCase("pre_exposure stage requires treatment=none")
    if stage == "post_exposure_aged":
        if coupon != "parent":
            raise InvalidCase("post_exposure_aged stage requires --coupon parent")
        if not re.fullmatch(r"env_aging_[0-9]+d", treatment):
            raise InvalidCase("post_exposure_aged stage requires --treatment env_aging_<N>d")
    if stage == "post_exposure" and treatment != "as_exposed":
        raise InvalidCase("post_exposure stage uses treatment=as_exposed (parent immediately out of the smoke chamber)")
    if stage == "post_treatment" and coupon == "parent":
        raise InvalidCase("post_treatment stage applies to a coupon strip, not the parent")
    if stage == "post_treatment" and treatment == "none":
        raise InvalidCase(
            "post_treatment stage requires a real treatment (as_exposed | env_aging_<N>d | PER | advanced_cleaning)"
        )
    if coupon != "parent" and stage != "post_treatment":
        raise InvalidCase("non-parent coupons are only captured at stage=post_treatment")


def case_slug(test, coupon, treatment, stage):
    return f"{test}_{coupon}_{treatment}_{stage}"

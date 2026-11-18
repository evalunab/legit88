"""Step 3: combine all findings into one verdict.

Rule of thumb, kept simple on purpose so it is easy to explain to a jury:
- at least one red finding        -> RED    "Serious risk signals"
- two or more orange findings     -> ORANGE "Check before you go"
- otherwise                       -> GREEN  "No major risk signal found"
We never say "scam": we report signals, the backpacker decides.
"""

from . import checks
from .extractor import extract
from .models import GREEN, ORANGE, RED, Report

HEADLINES = {
    RED: "Serious risk signals found",
    ORANGE: "Check a few things before you go",
    GREEN: "No major risk signal found",
}
ORDER = {RED: 0, ORANGE: 1, GREEN: 2, "info": 3}


def build_report(ad) -> Report:
    findings = (
        checks.check_red_flags(ad)
        + checks.check_employer(ad)
        + checks.check_location(ad)
        + checks.check_pay(ad)
    )
    findings.sort(key=lambda f: ORDER[f.level])

    reds = sum(f.level == RED for f in findings)
    oranges = sum(f.level == ORANGE for f in findings)
    verdict = RED if reds else ORANGE if oranges >= 2 else GREEN

    questions = [f.question for f in findings if f.question]
    return Report(verdict=verdict, headline=HEADLINES[verdict], findings=findings, questions=questions, ad=ad)


def analyse(text: str = "", image_bytes: bytes = None, image_type: str = "image/png") -> Report:
    """The whole pipeline: read the ad, run the checks, give a verdict."""
    ad = extract(text, image_bytes, image_type)
    return build_report(ad)

"""Step 2: run every check on the extracted facts.

Each check returns a list of `Finding`s (red, orange, green or info).
Rates and postcode lists change: the numbers below are dated so they are easy to update.
"""

import csv
from difflib import SequenceMatcher
from pathlib import Path

from . import abn as abn_service
from .models import GREEN, INFO, ORANGE, RED, Finding, JobAd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Horticulture Award [MA000028], Level 1 adult, from 1 July 2026.
# Confirmed by the project owner on Fair Work "Pay and piece rates" (horticulture.fairwork.gov.au/pay-and-piece-rates).
AWARD_UPDATED = "1 July 2026"
MIN_HOURLY_PERMANENT = 25.74
MIN_HOURLY_CASUAL = 32.18  # includes the 25% casual loading
PIECE_RATE_TARGET_CASUAL = round(MIN_HOURLY_CASUAL * 1.15, 2)  # piece rates must let an average worker earn 15% more
HOURS_PER_DAY = 7.6

FREE_EMAIL_DOMAINS = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "live.com", "icloud.com", "proton.me", "protonmail.com"}

LABOUR_HIRE_REGISTERS = {
    "QLD": "https://www.labourhire.qld.gov.au/",
    "VIC": "https://labourhireauthority.vic.gov.au/",
    "SA": "https://www.cbs.sa.gov.au/",
}


# ---------- Postcode: does the job count toward the 88 days? ----------

def _load_postcodes():
    rows = []
    with open(DATA_DIR / "regional_postcodes.csv", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


REGIONAL = _load_postcodes()


def state_from_postcode(postcode: str):
    """Guess the state from the first digit(s) of a postcode."""
    p = int(postcode)
    if 800 <= p <= 999:
        return "NT"
    if 2600 <= p <= 2618 or 2900 <= p <= 2920:
        return "ACT"
    return {"2": "NSW", "3": "VIC", "4": "QLD", "5": "SA", "6": "WA", "7": "TAS"}.get(postcode[0])


def _matching_row(postcode: str, state: str = None):
    """Return the CSV row that contains this postcode, or None."""
    state = state or state_from_postcode(postcode)
    p = int(postcode)
    for row in REGIONAL:
        if row["state"] != state:
            continue
        if row["from_postcode"] == "ALL":
            return row
        if int(row["from_postcode"]) <= p <= int(row["to_postcode"]):
            return row
    return None


def is_regional(postcode: str, state: str = None) -> bool:
    return _matching_row(postcode, state) is not None


def needs_verification(state: str) -> bool:
    """True for states whose rows in the CSV are still to be compared with the official list."""
    # TODO verify the VIC / QLD / WA rows against the Home Affairs "specified work" list.
    return any(r["state"] == state and r.get("status") == "to_verify" for r in REGIONAL)


def check_location(ad: JobAd):
    if not ad.postcode:
        return [Finding(ORANGE, "No exact location",
                        "The ad gives no postcode, so we cannot tell if this job counts toward your 88 days.",
                        "What is the exact address or postcode of the farm?")]
    findings = []
    state = ad.state or state_from_postcode(ad.postcode)
    guessed = state_from_postcode(ad.postcode)
    if ad.state and guessed and ad.state != guessed and {ad.state, guessed} != {"NSW", "ACT"}:  # NSW/ACT share a border
        findings.append(Finding(ORANGE, "State and postcode do not match",
                                f"The ad says {ad.state} but postcode {ad.postcode} is normally in {guessed}.",
                                "Can you confirm the farm's exact address, state and postcode?"))
    if is_regional(ad.postcode, state):
        note = (" Our list for this state is still being checked against the official Home Affairs list: "
                "please confirm the postcode there.") if needs_verification(state) else ""
        findings.append(Finding(GREEN, f"Postcode {ad.postcode} is in regional Australia",
                                f"{state} {ad.postcode} is on the specified-work list for plant and animal cultivation." + note))
    else:
        findings.append(Finding(RED, f"Postcode {ad.postcode} is not on the regional list",
                                f"Work in {state} {ad.postcode} is unlikely to count toward your 88 days for farm work.",
                                "Can you confirm the farm's postcode? Days only count in eligible regional postcodes."))
    if ad.work_type == "hospitality":
        findings.append(Finding(ORANGE, "Hospitality only counts in some areas",
                                "Tourism and hospitality work counts only in Northern Australia and remote or very remote areas.",
                                "Is this postcode in Northern or remote Australia for hospitality work?"))
    return findings


# ---------- Pay: is it at least the legal minimum? ----------

def check_pay(ad: JobAd):
    if ad.cash_only:
        return [Finding(RED, "Cash in hand / no payslips",
                        "Cash-only work without payslips cannot count toward your 88 days and often hides underpayment.",
                        "Will I receive payslips and be paid into my Australian bank account?")]
    if ad.pay_amount is None:
        return [Finding(ORANGE, "No pay rate stated",
                        "The ad does not say how much you will earn.",
                        "What is the hourly rate, or the piece rate and the average earnings per hour?")]

    minimum = MIN_HOURLY_PERMANENT if ad.employment_type in ("full_time", "part_time") else MIN_HOURLY_CASUAL
    label = "permanent" if minimum == MIN_HOURLY_PERMANENT else "casual"

    if ad.pay_unit == "piece":
        return [Finding(INFO, "Paid by piece rate",
                        f"Piece rates are legal, but they must let an average worker earn at least 15% above the minimum "
                        f"(about A${PIECE_RATE_TARGET_CASUAL}/h for a casual, rates from {AWARD_UPDATED}).",
                        "Can I see the written piece rate agreement, and what do average pickers earn per hour?")]

    hourly = ad.pay_amount
    if ad.pay_unit == "day":
        hourly = ad.pay_amount / HOURS_PER_DAY
    elif ad.pay_unit == "week":
        hourly = ad.pay_amount / (HOURS_PER_DAY * 5)
    elif ad.pay_unit not in (None, "hour"):
        return []

    if hourly < MIN_HOURLY_PERMANENT:
        return [Finding(RED, f"Pay below the legal minimum (≈ A${hourly:.2f}/h)",
                        f"The Horticulture Award minimum is A${MIN_HOURLY_PERMANENT}/h (A${MIN_HOURLY_CASUAL}/h for casuals) "
                        f"from {AWARD_UPDATED}. Underpaid work may not count toward your 88 days.")]
    if hourly < minimum:
        return [Finding(ORANGE, f"Pay may be below the {label} minimum (≈ A${hourly:.2f}/h)",
                        f"Casual workers must get at least A${MIN_HOURLY_CASUAL}/h, including the 25% casual loading.",
                        "Is this a casual job, and does the rate include the 25% casual loading?")]
    return [Finding(GREEN, f"Pay meets the minimum (≈ A${hourly:.2f}/h)",
                    f"At or above the {label} minimum of A${minimum}/h from {AWARD_UPDATED}.")]


# ---------- Employer: does the business exist? ----------

def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def check_employer(ad: JobAd):
    findings = []
    if not ad.abn:
        findings.append(Finding(ORANGE, "No ABN in the ad",
                                "Legitimate employers have an ABN. You can ask for it and check it for free.",
                                "What is your ABN (Australian Business Number)?"))
        try:
            matches = abn_service.search_name(ad.employer_name)
        except Exception:
            matches = None
        if matches:
            names = "; ".join(f"{m['name']} ({m['state']} {m['postcode']})" for m in matches)
            findings.append(Finding(INFO, "Possible matches in the business register", names))
        return findings

    if not abn_service.is_valid_abn(ad.abn):
        return [Finding(RED, "This ABN is not a valid number",
                        f"{ad.abn} fails the official ABN checksum: it was mistyped or made up.",
                        "Can you send your ABN again? The one in the ad is not valid.")]

    try:
        record = abn_service.lookup_abn(ad.abn)
    except Exception:
        record = None
    if record is None:
        findings.append(Finding(INFO, "ABN format is valid",
                                "The number passes the official checksum. Live register check not run (no ABN Lookup key, or service unreachable)."))
        return findings
    if not record["found"]:
        return [Finding(RED, "ABN not found in the business register", record.get("message", ""))]
    if record["status"] != "Active":
        return [Finding(RED, f"ABN is {record['status']}",
                        f"{record['name']}: this business is not active in the register.")]

    findings.append(Finding(GREEN, "ABN is active", f"Registered to {record['name']} ({record['state']} {record['postcode']})."))
    names = [record["name"]] + list(record["business_names"])
    if ad.employer_name and max(_similar(ad.employer_name, n) for n in names) < 0.5:
        findings.append(Finding(ORANGE, "Name does not match the ABN",
                                f"The ad says \"{ad.employer_name}\" but the ABN belongs to \"{record['name']}\".",
                                "Why is the business name different from the ABN holder?"))
    return findings


# ---------- Red flags in the wording ----------

def check_red_flags(ad: JobAd):
    findings = []
    if ad.upfront_fee:
        reason = f" ({ad.upfront_fee_reason})" if ad.upfront_fee_reason else ""
        findings.append(Finding(RED, f"Asks for money before you start{reason}",
                                "Fair Work says it is illegal to ask a worker to pay to get or keep a job. Fake ads often ask for a deposit."))
    if ad.promises_visa_signoff:
        findings.append(Finding(RED, "Promises a guaranteed visa sign-off",
                                "Selling or guaranteeing 88-day sign-offs is a known scam and can lead to visa refusal for fraud."))
    if ad.urgency_pressure:
        findings.append(Finding(ORANGE, "Pressure to decide fast",
                                "Urgency is a common pressure tactic. Take time to check the employer."))
    if ad.is_labour_hire:
        register = LABOUR_HIRE_REGISTERS.get(ad.state or "")
        where = f" Check the licence register: {register}" if register else ""
        findings.append(Finding(ORANGE, "Labour hire agency",
                                "Agencies supply workers to farms. In Queensland, Victoria and South Australia they must hold a licence." + where,
                                "What is your labour hire licence number, and which farm will I work on?"))
    free_mail = [e for e in ad.contact_emails if e.split("@")[-1].lower() in FREE_EMAIL_DOMAINS]
    if free_mail:
        findings.append(Finding(INFO, "Contact uses a free email address",
                                f"{free_mail[0]}: common for small farms, but scammers use them too."))
    if ad.accommodation_cost_per_week and ad.accommodation_cost_per_week > 250:
        findings.append(Finding(INFO, f"Accommodation costs A${ad.accommodation_cost_per_week:.0f}/week",
                                "Check it is optional and that deductions are agreed in writing.",
                                "Is the accommodation optional, and will deductions be agreed in writing?"))
    return findings

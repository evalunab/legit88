"""Step 1: read the ad and pull out the facts we need to check.

Two ways to do it:
- `extract_with_llm`: sends the ad (text or screenshot) to an AI model and asks for a
  JSON answer. Smart: understands messy wording, other languages and images.
- `extract_with_rules`: a simple backup with regular expressions (pattern matching).
  It works without any API key, so the app never breaks during a demo.
"""

import base64
import json
import re

from .config import LLM_MODEL, get_secret
from .models import JobAd

SYSTEM_PROMPT = """You extract facts from job ads aimed at Working Holiday backpackers in Australia.
Return ONLY a JSON object with exactly these keys (use null when the ad does not say):
{
 "employer_name": string|null,
 "abn": string|null (11 digits, no spaces),
 "is_labour_hire": boolean (true if the advertiser is an agency or contractor supplying workers to farms),
 "location_text": string|null,
 "postcode": string|null (4 digits; infer it ONLY if the exact town is named and you are sure),
 "state": "NSW"|"VIC"|"QLD"|"SA"|"WA"|"TAS"|"NT"|"ACT"|null,
 "work_type": "picking_packing"|"pruning"|"farm_general"|"hospitality"|"construction"|"other"|null,
 "pay_amount": number|null (in AUD),
 "pay_unit": "hour"|"day"|"week"|"piece"|null,
 "employment_type": "casual"|"full_time"|"part_time"|null,
 "cash_only": boolean (true if pay is cash in hand / no payslips / no tax),
 "upfront_fee": boolean (true if the worker must pay anything before starting: deposit, bond, registration, placement, transport or accommodation paid in advance),
 "upfront_fee_reason": string|null,
 "promises_visa_signoff": boolean (true if the ad promises or sells a guaranteed 88-day / 2nd year visa sign-off),
 "urgency_pressure": boolean (true if it pushes to decide or pay immediately),
 "accommodation_cost_per_week": number|null,
 "contact_emails": [string],
 "contact_phones": [string]
}
Never invent facts. Do not judge whether the ad is a scam."""

STATES = {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}


def _clean(data: dict, source: str) -> JobAd:
    """Turn the raw dictionary into a tidy JobAd, ignoring bad values."""

    def text(key):
        v = data.get(key)
        return str(v).strip() if v not in (None, "", "null") else None

    def number(key):
        try:
            v = data.get(key)
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    abn = text("abn")
    if abn:
        abn = re.sub(r"\D", "", abn) or None
    postcode = text("postcode")
    if postcode and not re.fullmatch(r"\d{4}", postcode):
        postcode = None
    state = (text("state") or "").upper() or None
    if state not in STATES:
        state = None

    return JobAd(
        employer_name=text("employer_name"),
        abn=abn,
        is_labour_hire=bool(data.get("is_labour_hire")),
        location_text=text("location_text"),
        postcode=postcode,
        state=state,
        work_type=text("work_type"),
        pay_amount=number("pay_amount"),
        pay_unit=text("pay_unit"),
        employment_type=text("employment_type"),
        cash_only=bool(data.get("cash_only")),
        upfront_fee=bool(data.get("upfront_fee")),
        upfront_fee_reason=text("upfront_fee_reason"),
        promises_visa_signoff=bool(data.get("promises_visa_signoff")),
        urgency_pressure=bool(data.get("urgency_pressure")),
        accommodation_cost_per_week=number("accommodation_cost_per_week"),
        contact_emails=list(data.get("contact_emails") or []),
        contact_phones=list(data.get("contact_phones") or []),
        extracted_by=source,
    )


def extract_with_llm(text: str = "", image_bytes: bytes = None, image_type: str = "image/png") -> JobAd:
    """Ask the AI model (through OpenRouter) to read the ad. Needs OPENROUTER_API_KEY."""
    from openai import OpenAI  # OpenRouter speaks the same language as the OpenAI library

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=get_secret("OPENROUTER_API_KEY"))
    content = []
    if text:
        content.append({"type": "text", "text": f"Job ad:\n{text}"})
    if image_bytes:
        b64 = base64.b64encode(image_bytes).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:{image_type};base64,{b64}"}})

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": content}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    raw = response.choices[0].message.content
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    return _clean(json.loads(raw), "llm")


# ---------- Backup: pattern matching, no AI needed ----------

FEE_WORDS = r"(deposit|bond|registration fee|placement fee|admin fee|pay (?:in advance|upfront|first)|upfront|transfer .{0,20}before)"
CASH_WORDS = r"(cash in hand|cash only|cash-in-hand|paid in cash|no payslip|no tax)"
SIGNOFF_WORDS = r"(guaranteed? (?:88|second|2nd)|sign(?:ed)?[- ]off|we sign your|88 days guaranteed|visa days guaranteed)"
URGENCY_WORDS = r"(urgent|asap|today only|limited spots|only \d+ spots|first come|act now|don'?t miss)"
AGENCY_WORDS = r"(labou?r hire|recruitment agency|staffing agency|employment agency)"


def extract_with_rules(text: str) -> JobAd:
    """Simple extraction with regular expressions. Less smart, but free and offline."""
    t = text or ""
    low = t.lower()
    data = {}

    abn = re.search(r"\bABN[:\s#]*((?:\d\s?){11})", t, re.I)
    data["abn"] = abn.group(1) if abn else None

    pc = re.search(r"\b(NSW|VIC|QLD|SA|WA|TAS|NT|ACT)\b[\s,]*(\d{4})\b", t, re.I) or re.search(
        r"\b(\d{4})\b[\s,]*(NSW|VIC|QLD|SA|WA|TAS|NT|ACT)\b", t, re.I
    )
    if pc:
        a, b = pc.group(1), pc.group(2)
        data["state"], data["postcode"] = (a, b) if a.isalpha() else (b, a)
    else:
        st = re.search(r"\b(NSW|VIC|QLD|SA|WA|TAS|NT|ACT)\b", t)
        data["state"] = st.group(1) if st else None

    pay = re.search(r"\$\s?(\d+(?:\.\d{1,2})?)\s*(?:/|per|an|a)\s*(hour|hr|h|day|week|bin|kg|bucket|tray|crate)", low)
    if pay:
        unit = pay.group(2)
        data["pay_amount"] = float(pay.group(1))
        data["pay_unit"] = {"hr": "hour", "h": "hour"}.get(unit, unit)
        if unit in ("bin", "kg", "bucket", "tray", "crate"):
            data["pay_unit"] = "piece"

    if re.search(r"\b(pick|picking|packing|packer|harvest)", low):
        data["work_type"] = "picking_packing"
    elif re.search(r"\b(prun|vineyard)", low):
        data["work_type"] = "pruning"
    elif re.search(r"\b(farm|orchard|nursery)", low):
        data["work_type"] = "farm_general"
    elif re.search(r"\b(bar|cafe|café|hostel reception|hospitality|waitress|waiter)", low):
        data["work_type"] = "hospitality"

    if "casual" in low:
        data["employment_type"] = "casual"

    data["cash_only"] = bool(re.search(CASH_WORDS, low))
    fee = re.search(FEE_WORDS, low)
    data["upfront_fee"] = bool(fee)
    data["upfront_fee_reason"] = fee.group(0) if fee else None
    data["promises_visa_signoff"] = bool(re.search(SIGNOFF_WORDS, low))
    data["urgency_pressure"] = bool(re.search(URGENCY_WORDS, low))
    data["is_labour_hire"] = bool(re.search(AGENCY_WORDS, low))
    data["contact_emails"] = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", t)
    data["contact_phones"] = re.findall(r"(?:\+61|0)4\d{2}\s?\d{3}\s?\d{3}", t)

    name = re.search(r"^\s*([A-Z][\w&'. ]{2,60}(?:Farm|Farms|Orchard|Orchards|Pty Ltd|Pty|Growers|Produce|Labour|Harvest\w*))", t, re.M)
    data["employer_name"] = name.group(1).strip() if name else None
    return _clean(data, "rules")


def extract(text: str = "", image_bytes: bytes = None, image_type: str = "image/png") -> JobAd:
    """Use the AI if a key is set, otherwise fall back to the rules."""
    if get_secret("OPENROUTER_API_KEY"):
        try:
            return extract_with_llm(text, image_bytes, image_type)
        except Exception as error:  # network problem, bad answer...
            print(f"LLM extraction failed, using rules instead: {error}")
            ad = extract_with_rules(text)
            ad.ai_failed = True  # the page tells the user a simpler reader was used
            return ad
    return extract_with_rules(text)

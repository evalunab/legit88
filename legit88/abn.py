"""Check the employer's ABN (Australian Business Number).

1. `is_valid_abn` checks the 11 digits with the official checksum formula.
   A fake ABN typed at random fails this test. No internet needed.
2. `lookup_abn` asks the government's ABN Lookup service whether the business exists
   and is active. Needs a free key (GUID) from abr.business.gov.au.
3. `search_name` looks for businesses by name when the ad gives no ABN.
"""

import json
import re

import requests

from .config import get_secret

ABR_URL = "https://abr.business.gov.au/json/"
WEIGHTS = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]


def is_valid_abn(abn: str) -> bool:
    """Official ABN checksum: subtract 1 from the first digit, weight, sum, divide by 89."""
    digits = re.sub(r"\D", "", abn or "")
    if len(digits) != 11:
        return False
    numbers = [int(d) for d in digits]
    numbers[0] -= 1
    return sum(n * w for n, w in zip(numbers, WEIGHTS)) % 89 == 0


def _jsonp_to_dict(text: str) -> dict:
    """The service answers `callback({...})`; we keep only the {...} part."""
    start, end = text.find("("), text.rfind(")")
    return json.loads(text[start + 1 : end])


def lookup_abn(abn: str):
    """Return the official record for an ABN, or None if we have no key or no answer."""
    guid = get_secret("ABN_LOOKUP_GUID")
    if not guid:
        return None
    response = requests.get(
        ABR_URL + "AbnDetails.aspx",
        params={"abn": re.sub(r"\D", "", abn), "guid": guid, "callback": "callback"},
        timeout=10,
    )
    data = _jsonp_to_dict(response.text)
    if data.get("Message"):  # e.g. "Search text is not a valid ABN or ACN"
        return {"found": False, "message": data["Message"]}
    return {
        "found": bool(data.get("Abn")),
        "status": data.get("AbnStatus"),  # "Active" or "Cancelled"
        "name": data.get("EntityName"),
        "business_names": data.get("BusinessName") or [],
        "state": data.get("AddressState"),
        "postcode": data.get("AddressPostcode"),
        "registered_since": data.get("AbnStatusEffectiveFrom"),
    }


def search_name(name: str, max_results: int = 3):
    """Search the register by business name. Returns a short list of matches."""
    guid = get_secret("ABN_LOOKUP_GUID")
    if not guid or not name:
        return None
    response = requests.get(
        ABR_URL + "MatchingNames.aspx",
        params={"name": name, "maxResults": max_results, "guid": guid, "callback": "callback"},
        timeout=10,
    )
    data = _jsonp_to_dict(response.text)
    return [
        {"abn": n.get("Abn"), "name": n.get("Name"), "state": n.get("State"), "postcode": n.get("Postcode"), "score": n.get("Score")}
        for n in data.get("Names", [])[:max_results]
    ]

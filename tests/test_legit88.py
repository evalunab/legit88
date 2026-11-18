"""Automatic tests. Run them with:  python -m pytest
They use the rule-based reader, so they need no API key and no internet."""

import os
from pathlib import Path

import pytest

from legit88 import checks
from legit88.abn import is_valid_abn
from legit88.extractor import extract_with_rules
from legit88.models import GREEN, ORANGE, RED, JobAd
from legit88.verdict import build_report

SAMPLES = Path(__file__).parent / "samples"


@pytest.fixture(autouse=True)
def no_keys(monkeypatch):
    """Make sure tests never call the paid AI or the internet."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ABN_LOOKUP_GUID", raising=False)
    monkeypatch.setattr("legit88.abn.get_secret", lambda name: None)


def report_for(name):
    return build_report(extract_with_rules((SAMPLES / name).read_text()))


# --- ABN checksum ---
def test_valid_abn():
    assert is_valid_abn("51 824 753 556")


def test_invalid_abn():
    assert not is_valid_abn("12 345 678 901")
    assert not is_valid_abn("123")


# --- Postcodes ---
@pytest.mark.parametrize("postcode,expected", [
    ("2450", True),   # Coffs Harbour NSW
    ("3630", True),   # Shepparton VIC
    ("2000", False),  # Sydney CBD
    ("4000", False),  # Brisbane CBD
    ("5000", True),   # all of South Australia
    ("7000", True),   # all of Tasmania
])
def test_regional_postcodes(postcode, expected):
    assert checks.is_regional(postcode) is expected


# --- Pay ---
def test_pay_below_minimum_is_red():
    findings = checks.check_pay(JobAd(pay_amount=20, pay_unit="hour"))
    assert findings[0].level == RED


def test_casual_pay_ok_is_green():
    findings = checks.check_pay(JobAd(pay_amount=33.5, pay_unit="hour", employment_type="casual"))
    assert findings[0].level == GREEN


def test_cash_only_is_red():
    assert checks.check_pay(JobAd(pay_amount=35, pay_unit="hour", cash_only=True))[0].level == RED


# --- Whole pipeline on example ads ---
def test_fake_ad_is_red():
    report = report_for("fake_berry_farm_deposit.txt")
    assert report.verdict == RED
    titles = " ".join(f.title for f in report.findings)
    assert "money before you start" in titles
    assert "visa sign-off" in titles
    assert "Cash in hand" in titles


def test_legit_looking_ad_is_green():
    report = report_for("legit_looking_orchard.txt")
    assert report.verdict == GREEN


def test_llm_answer_is_cleaned(monkeypatch):
    """Simulate the AI's answer (no real call) and check we read it correctly."""
    import json
    import types

    fake_json = json.dumps({"employer_name": "Green Valley Farm", "abn": "51 824 753 556", "postcode": "2450",
                            "state": "nsw", "pay_amount": "34", "pay_unit": "hour", "upfront_fee": False,
                            "contact_emails": ["a@b.com"]})

    class FakeClient:
        def __init__(self, **kwargs):
            message = types.SimpleNamespace(content="```json\n" + fake_json + "\n```")
            answer = types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **kw: answer))

    import openai
    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    from legit88.extractor import extract_with_llm

    ad = extract_with_llm("any ad")
    assert ad.abn == "51824753556" and ad.state == "NSW" and ad.pay_amount == 34.0
    assert ad.extracted_by == "llm"


# --- More rules from the spec ---
def test_casual_pay_between_minimums_is_orange():
    assert checks.check_pay(JobAd(pay_amount=28, pay_unit="hour", employment_type="casual"))[0].level == ORANGE


def test_piece_rate_is_info():
    assert checks.check_pay(JobAd(pay_amount=2, pay_unit="piece"))[0].level == "info"


def test_missing_abn_and_postcode_are_orange():
    assert checks.check_employer(JobAd())[0].level == ORANGE
    assert checks.check_location(JobAd())[0].level == ORANGE


def test_valid_abn_without_key_is_not_red():
    findings = checks.check_employer(JobAd(abn="51 824 753 556"))
    assert all(f.level != RED for f in findings)


def test_upfront_fee_and_visa_promise_are_red():
    levels = [f.level for f in checks.check_red_flags(JobAd(upfront_fee=True, promises_visa_signoff=True))]
    assert levels == [RED, RED]


def test_two_oranges_make_orange_and_one_does_not():
    # urgency + labour hire = 2 orange signals -> ORANGE
    two = build_report(JobAd(abn="51824753556", postcode="2450", state="NSW", pay_amount=35, pay_unit="hour",
                             urgency_pressure=True, is_labour_hire=True))
    assert two.verdict == ORANGE
    one = build_report(JobAd(abn="51824753556", postcode="2450", state="NSW", pay_amount=35, pay_unit="hour",
                             urgency_pressure=True))
    assert one.verdict == GREEN


def test_vic_qld_wa_rows_are_marked_to_verify():
    assert all(checks.needs_verification(s) for s in ("VIC", "QLD", "WA"))
    assert not checks.needs_verification("NSW")


def test_regex_does_not_overreact_to_common_words():
    ad = extract_with_rules("Riverbend Orchards. Our contractor-free team, call the agency of tourism. Start immediately.")
    assert not ad.is_labour_hire and not ad.urgency_pressure


def test_state_postcode_mismatch_is_orange():
    findings = checks.check_location(JobAd(postcode="3630", state="NSW"))
    assert any(f.level == ORANGE and "do not match" in f.title for f in findings)
    assert not any("do not match" in f.title for f in checks.check_location(JobAd(postcode="3630", state="VIC")))


def test_failed_ai_falls_back_and_is_flagged(monkeypatch):
    from legit88 import extractor
    monkeypatch.setattr(extractor, "get_secret", lambda name: "fake-key")
    monkeypatch.setattr(extractor, "extract_with_llm", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    ad = extractor.extract("Apple picking Shepparton VIC 3630 $33 per hour")
    assert ad.ai_failed and ad.extracted_by == "rules"


def test_agency_in_city_is_red():
    report = report_for("agency_piece_rate_city.txt")
    assert report.verdict == RED  # invalid ABN + Brisbane CBD not regional
    assert report.ad.is_labour_hire

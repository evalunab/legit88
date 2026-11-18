"""Shared data structures.

Think of these as "forms" that every part of the app fills in:
- `JobAd` holds what we extracted from the ad (employer, ABN, pay...).
- `Finding` is one result of one check (e.g. "ABN is active").
- `Report` is the final answer shown to the user.
"""

from dataclasses import dataclass, field
from typing import Optional

# The three levels a finding can have, plus "info" for neutral facts.
RED = "red"
ORANGE = "orange"
GREEN = "green"
INFO = "info"


@dataclass
class JobAd:
    employer_name: Optional[str] = None
    abn: Optional[str] = None
    is_labour_hire: bool = False
    location_text: Optional[str] = None
    postcode: Optional[str] = None
    state: Optional[str] = None  # NSW, VIC, QLD, SA, WA, TAS, NT, ACT
    work_type: Optional[str] = None  # picking_packing, pruning, farm_general, hospitality, construction, other
    pay_amount: Optional[float] = None
    pay_unit: Optional[str] = None  # hour, day, week, piece
    employment_type: Optional[str] = None  # casual, full_time, part_time
    cash_only: bool = False
    upfront_fee: bool = False
    upfront_fee_reason: Optional[str] = None
    promises_visa_signoff: bool = False
    urgency_pressure: bool = False
    accommodation_cost_per_week: Optional[float] = None
    contact_emails: list = field(default_factory=list)
    contact_phones: list = field(default_factory=list)
    extracted_by: str = "rules"  # "llm" or "rules"
    ai_failed: bool = False  # True if the AI was tried but failed, so the simple rules were used


@dataclass
class Finding:
    level: str  # RED, ORANGE, GREEN or INFO
    title: str
    detail: str
    question: Optional[str] = None  # a question the backpacker should ask the employer


@dataclass
class Report:
    verdict: str  # RED, ORANGE or GREEN
    headline: str
    findings: list
    questions: list
    ad: JobAd

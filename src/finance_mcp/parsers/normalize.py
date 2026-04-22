"""Merchant-name normalization (PRD §7.4).

Turns raw bank narrations like::

    "UPI-SWIGGY-swiggy@axl-551234123456-PAYMENT FROM PHONE"

into a tidy merchant key like::

    "SWIGGY"

The pipeline is intentionally deterministic and regex-driven so that
the same raw description always produces the same dedup hash key.
"""

from __future__ import annotations

import re

# Order matters: longer/more-specific prefixes first so we don't leave stubs.
_PREFIX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^UPI\s*[-/:]\s*", re.IGNORECASE),
    re.compile(r"^NEFT\s+(?:DR|CR)\s*[-/:]\s*", re.IGNORECASE),
    re.compile(r"^NEFT\s*[-/:]\s*", re.IGNORECASE),
    re.compile(r"^IMPS\s*[-/:]\s*", re.IGNORECASE),
    re.compile(r"^ACH\s+[DC]\s*[-/:]\s*", re.IGNORECASE),
    re.compile(r"^ACH\s*[-/:]\s*", re.IGNORECASE),
    re.compile(r"^POS\s+\d+X+\s+", re.IGNORECASE),  # POS 4567XXXX MERCHANT
    re.compile(r"^POS\s+", re.IGNORECASE),
    re.compile(r"^ATM\s+", re.IGNORECASE),
    re.compile(r"^NACH\s*[-/:]\s*", re.IGNORECASE),
)

# VPA handles (@ybl, @axl, @paytm, @oksbi, @okhdfcbank, @okicici, @ibl).
# The character class excludes `-`, so the match stops at the `-` that
# separates the VPA from the surrounding tokens (e.g. "SWIGGY-swiggy@axl").
_VPA_PATTERN = re.compile(r"[A-Za-z0-9._+]+@[A-Za-z][A-Za-z0-9]+")

# Reference numbers: a 6+ digit run surrounded by separators or end-of-string.
_REFNO_PATTERN = re.compile(r"(?:(?<=[-/\s])|^)\d{6,}(?=[-/\s]|$)")

# Masked account numbers like "XXXXXX1234" or "4567XX9012" — require at
# least one X AND at least one digit to avoid eating plain digit or plain
# letter tokens.
_MASKED_ACCT_PATTERN = re.compile(r"\b(?=[0-9Xx]*X)(?=[0-9Xx]*\d)[0-9Xx]{4,}\b")

# Common trailing suffixes that add no signal.
_TAIL_SUFFIXES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\s*[-/]?\s*PAYMENT\s+FROM\s+PHONE\s*$", re.IGNORECASE),
    re.compile(r"\s*[-/]?\s*PAYMENT\s+RECEIVED\s*$", re.IGNORECASE),
    re.compile(r"\s*[-/]?\s*COLLECT\s+REQUEST\s*$", re.IGNORECASE),
)

_SEPARATOR_RE = re.compile(r"[\s\-/]+")
_WHITESPACE_RE = re.compile(r"\s+")

_MAX_LEN = 80


def normalize_merchant(raw: str) -> str:
    """Return a normalized merchant key for a raw narration.

    The transformation:

    1. Uppercase.
    2. Strip known transaction-channel prefixes (UPI/POS/NEFT/IMPS/ACH/ATM).
    3. Remove VPA handles (``@ybl``, ``@axl``, etc).
    4. Remove embedded / trailing reference numbers (6+ digits).
    5. Remove masked account numbers (``XXXXXX1234``).
    6. Strip noisy trailing suffixes.
    7. Collapse whitespace and trailing separators.
    8. Truncate to 80 characters.

    Empty input returns an empty string.
    """
    if not raw:
        return ""

    s = raw.strip().upper()

    # 1. Strip prefixes (apply until no further match — handles stacked prefixes).
    changed = True
    while changed:
        changed = False
        for pat in _PREFIX_PATTERNS:
            new = pat.sub("", s, count=1)
            if new != s:
                s = new.lstrip()
                changed = True

    # 2. Strip VPAs.
    s = _VPA_PATTERN.sub(" ", s)

    # 3. Strip masked account numbers.
    s = _MASKED_ACCT_PATTERN.sub(" ", s)

    # 4. Strip reference numbers (6+ digit runs after a separator).
    s = _REFNO_PATTERN.sub(" ", s)

    # 5. Strip noisy tail suffixes.
    for pat in _TAIL_SUFFIXES:
        s = pat.sub("", s)

    # 6. Collapse separators / whitespace.
    s = _SEPARATOR_RE.sub(" ", s)
    s = _WHITESPACE_RE.sub(" ", s).strip(" -/")

    return s[:_MAX_LEN]


__all__ = ["normalize_merchant"]

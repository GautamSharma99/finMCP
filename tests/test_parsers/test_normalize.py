"""Tests for `normalize_merchant` (PRD §7.4)."""

from __future__ import annotations

import pytest

from finance_mcp.parsers.normalize import normalize_merchant


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # 1. UPI prefix + VPA + ref number + noise suffix.
        ("UPI-SWIGGY-swiggy@axl-551234123456-PAYMENT FROM PHONE", "SWIGGY"),
        # 2. UPI prefix with okhdfc VPA.
        ("UPI-ZOMATO-zomato@okhdfcbank-123456", "ZOMATO"),
        # 3. POS with masked card number.
        ("POS 4567XXXX UBER INDIA SYSTEMS", "UBER INDIA SYSTEMS"),
        # 4. POS without mask.
        ("POS BLINKIT GROCERIES", "BLINKIT GROCERIES"),
        # 5. NEFT DR with embedded 4-digit bank code (kept; only 6+-digit runs are stripped).
        ("NEFT DR-AXISCN0123-ACME CORP SALARY", "AXISCN0123 ACME CORP SALARY"),
        # 6. IMPS prefix.
        ("IMPS-P2P-john@ybl-12345678", "P2P"),
        # 7. ACH D (direct debit).
        ("ACH D-NETFLIX SUBSCRIPTION", "NETFLIX SUBSCRIPTION"),
        # 8. ATM withdrawal.
        ("ATM WDL HDFC KORAMANGALA", "WDL HDFC KORAMANGALA"),
        # 9. Multiple VPAs.
        ("UPI-AMAZON-amazon@apl-99887766-payment@paytm", "AMAZON"),
        # 10. Already clean uppercase merchant name.
        ("SPOTIFY", "SPOTIFY"),
        # 11. Lowercase gets uppercased.
        ("netflix", "NETFLIX"),
        # 12. Whitespace collapse.
        ("UPI-  FLIPKART   -ref@ybl", "FLIPKART"),
        # 13. Long ref number only.
        ("SALARY CREDIT 0123456789", "SALARY CREDIT"),
        # 14. Empty string.
        ("", ""),
        # 15. Only a ref number and VPA.
        ("UPI-someone@ybl-123456", ""),
        # 16. Masked account alone.
        ("TRANSFER TO XXXXXX9876", "TRANSFER TO"),
        # 17. Hyphen separator cleanup.
        ("UPI--HDFC---BESCOM--123456", "HDFC BESCOM"),
        # 18. Trailing PAYMENT RECEIVED.
        ("UPI-ACT FIBERNET-bill@ybl-PAYMENT RECEIVED", "ACT FIBERNET"),
        # 19. Stacked prefixes get stripped iteratively.
        ("UPI-UPI-OLA-ola@paytm-778899112233", "OLA"),
        # 20. NEFT CR (credit) — 4-digit bank code kept.
        ("NEFT CR-CITI0042-INTEREST CREDIT", "CITI0042 INTEREST CREDIT"),
        # 21. Trailing truncation safety: extremely long description.
        ("UPI-" + "A" * 200, "A" * 80),
        # 22. One-letter merchant survives — algorithm doesn't discard by length.
        ("UPI-X-ref@ybl-123456", "X"),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize_merchant(raw) == expected


def test_normalize_truncates_to_80() -> None:
    out = normalize_merchant("X" * 500)
    assert len(out) == 80

"""Generate reproducible dummy bank CSVs for the finance_mcp demo (PRD §9).

Produces one HDFC Savings CSV and one ICICI Credit Card CSV per month,
with realistic Indian-bank narrations and patterns:

- Salary credit on the 1st (HDFC)
- Rent debit around the 5th (HDFC)
- Monthly subscriptions: Netflix, Spotify, ACT Fibernet
- 2-5 Swiggy/Zomato per week (weekend-weighted)
- 1-3 Uber/Ola per week
- Big purchases every 2-4 weeks
- 1 credit card bill payment per month (HDFC → ICICI)
- 1-2 refunds randomly per month
- Closing balances that correctly sum

Usage:

    python scripts/generate_dummy_data.py --output-dir sample_data/ \\
        --months 6 --seed 42 --monthly-income 120000
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import typer
from faker import Faker

app = typer.Typer(add_completion=False)

# --- Narration templates ---------------------------------------------------

_UPI_SUFFIX_POOL = ("PAYMENT FROM PHONE", "COLLECT REQUEST", "PAYMENT RECEIVED")
_UPI_VPA_POOL = ("@ybl", "@axl", "@paytm", "@oksbi", "@okhdfcbank")


def _upi(merchant: str, handle: str | None = None) -> str:
    handle = handle or merchant.lower().replace(" ", "")
    vpa = random.choice(_UPI_VPA_POOL)
    ref = random.randint(100_000_000_000, 999_999_999_999)
    suffix = random.choice(_UPI_SUFFIX_POOL)
    return f"UPI-{merchant}-{handle}{vpa}-{ref}-{suffix}"


def _pos(merchant: str) -> str:
    card = f"{random.randint(4000, 5999)}XXXX"
    return f"POS {card} {merchant}"


def _neft(merchant: str, credit: bool = False) -> str:
    direction = "CR" if credit else "DR"
    bank_ref = f"{random.choice(('AXISCN', 'HDFCN', 'SBIN'))}{random.randint(1000, 9999)}"
    return f"NEFT {direction}-{bank_ref}-{merchant}"


def _ach(merchant: str) -> str:
    return f"ACH D-{merchant}"


# --- Event model -----------------------------------------------------------


@dataclass
class HdfcRow:
    day: date
    narration: str
    ref: str
    withdrawal: Decimal
    deposit: Decimal


@dataclass
class IciciRow:
    day: date
    details: str
    ref: str
    amount: Decimal
    drcr: str  # "DR" or "CR"


_RESTAURANT_BRANDS = (
    ("SWIGGY", 250, 650),
    ("ZOMATO", 200, 700),
    ("BLINKIT", 300, 1400),
    ("SWIGGY INSTAMART", 200, 900),
)
_TRANSPORT_BRANDS = (("UBER INDIA SYSTEMS", 120, 450), ("OLA", 100, 400))
_BIG_PURCHASES = (
    ("AMAZON INDIA", 2000, 9500),
    ("FLIPKART", 1500, 8000),
    ("IKEA BANGALORE", 2500, 15000),
    ("CROMA ELECTRONICS", 3000, 22000),
)
_REFUND_SOURCES = ("AMAZON INDIA", "FLIPKART", "SWIGGY", "UBER INDIA")


def _rand_money(lo: int, hi: int) -> Decimal:
    paise = random.randint(lo * 100, hi * 100)
    return Decimal(paise) / Decimal(100)


def _ref(prefix: str, counter: int) -> str:
    return f"{prefix}{counter:07d}"


# --- Month simulation ------------------------------------------------------


def _simulate_month(
    year: int,
    month: int,
    starting_balance: Decimal,
    monthly_income: Decimal,
    rent: Decimal,
    fake: Faker,
) -> tuple[list[HdfcRow], list[IciciRow], Decimal]:
    """Return (hdfc_rows, icici_rows, ending_balance) for a single month."""
    # Count days in month.
    next_month = date(year + (1 if month == 12 else 0), (month % 12) + 1, 1)
    days_in_month = (next_month - date(year, month, 1)).days

    hdfc: list[HdfcRow] = []
    icici: list[IciciRow] = []
    balance = starting_balance
    hdfc_ctr = 0
    icici_ctr = 0

    def add_hdfc(d: date, narr: str, w: Decimal, dep: Decimal) -> None:
        nonlocal balance, hdfc_ctr
        hdfc_ctr += 1
        balance = balance + dep - w
        hdfc.append(HdfcRow(d, narr, _ref("NEF", hdfc_ctr), w, dep))

    def add_icici(d: date, narr: str, amt: Decimal, drcr: str) -> None:
        nonlocal icici_ctr
        icici_ctr += 1
        icici.append(IciciRow(d, narr, _ref("ICRT", icici_ctr), amt, drcr))

    # Salary on the 1st (HDFC).
    add_hdfc(
        date(year, month, 1), _neft("ACME CORP SALARY", credit=True), Decimal(0), monthly_income
    )

    # Rent ~5th (HDFC).
    rent_day = min(5 + random.randint(-1, 1), days_in_month)
    add_hdfc(date(year, month, rent_day), _neft("LANDLORD RENT"), rent, Decimal(0))

    # Monthly subscriptions (HDFC).
    subs: tuple[tuple[str, int, Decimal], ...] = (
        ("NETFLIX", 8, Decimal("649.00")),
        ("SPOTIFY", 10, Decimal("119.00")),
        ("ACT FIBERNET", 12, Decimal("1049.00")),
    )
    for name, day, amt in subs:
        d = date(year, month, min(day, days_in_month))
        add_hdfc(d, _ach(name), amt, Decimal(0))

    # Food delivery — weekend weighted (2-5 per week).
    week = 1
    d0 = date(year, month, 1)
    while d0.month == month:
        weekly = random.randint(2, 5)
        for _ in range(weekly):
            offset = random.choices(range(7), weights=[1, 1, 1, 1, 2, 3, 2])[0]
            day = d0 + timedelta(days=offset)
            if day.month != month:
                break
            brand, lo, hi = random.choice(_RESTAURANT_BRANDS)
            amt = _rand_money(lo, hi)
            # Alternate between HDFC UPI and ICICI credit card.
            if random.random() < 0.55:
                add_hdfc(day, _upi(brand), amt, Decimal(0))
            else:
                add_icici(day, brand, amt, "DR")
        d0 = d0 + timedelta(days=7)
        week += 1

    # Ride-hailing (1-3/week).
    d0 = date(year, month, 1)
    while d0.month == month:
        for _ in range(random.randint(1, 3)):
            offset = random.randint(0, 6)
            day = d0 + timedelta(days=offset)
            if day.month != month:
                break
            brand, lo, hi = random.choice(_TRANSPORT_BRANDS)
            amt = _rand_money(lo, hi)
            if random.random() < 0.5:
                add_hdfc(day, _upi(brand), amt, Decimal(0))
            else:
                add_icici(day, brand, amt, "DR")
        d0 = d0 + timedelta(days=7)

    # Big purchases every 2-4 weeks.
    gap = random.randint(14, 28)
    d = date(year, month, random.randint(1, min(gap, days_in_month)))
    while d.month == month:
        brand, lo, hi = random.choice(_BIG_PURCHASES)
        amt = _rand_money(lo, hi)
        if random.random() < 0.5:
            add_hdfc(d, _pos(brand), amt, Decimal(0))
        else:
            add_icici(d, brand, amt, "DR")
        d = d + timedelta(days=random.randint(14, 28))

    # Utility bills mid-month (HDFC).
    bescom_day = min(18 + random.randint(-2, 2), days_in_month)
    add_hdfc(date(year, month, bescom_day), _upi("BESCOM"), _rand_money(1200, 3500), Decimal(0))

    # Credit card bill payment HDFC → ICICI near end of month.
    cc_total = sum((r.amount for r in icici if r.drcr == "DR"), Decimal(0)) - sum(
        (r.amount for r in icici if r.drcr == "CR"), Decimal(0)
    )
    if cc_total > 0:
        bill_day = min(days_in_month - 3, 27 + random.randint(0, 2))
        d_bill = date(year, month, bill_day)
        add_hdfc(d_bill, "TRANSFER-ICICI CREDIT CARD PAYMENT", cc_total, Decimal(0))
        add_icici(d_bill, "PAYMENT THANK YOU", cc_total, "CR")

    # 1-2 refunds per month on ICICI.
    for _ in range(random.randint(1, 2)):
        day = date(year, month, random.randint(1, days_in_month))
        src = random.choice(_REFUND_SOURCES)
        add_icici(day, f"REFUND-{src}", _rand_money(200, 2500), "CR")

    # Interest credit on the last day.
    add_hdfc(
        date(year, month, days_in_month),
        "NEFT CR-CITI0042-SAVINGS INTEREST CREDIT",
        Decimal(0),
        _rand_money(80, 350),
    )

    # Sort by date for stable output.
    hdfc.sort(key=lambda r: (r.day, r.narration))
    icici.sort(key=lambda r: (r.day, r.details))

    # Recompute HDFC running balance after sort.
    bal = starting_balance
    for row in hdfc:
        bal = bal + row.deposit - row.withdrawal
        # mutate via replacement since dataclass isn't frozen; store running
        row_balance = bal
        row.__dict__["running_balance"] = row_balance  # type: ignore[index]
    return hdfc, icici, bal


# --- CSV writers -----------------------------------------------------------


def _write_hdfc_csv(path: Path, rows: list[HdfcRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(
            [
                "Date",
                "Narration",
                "Chq./Ref.No.",
                "Value Dt",
                "Withdrawal Amt.",
                "Deposit Amt.",
                "Closing Balance",
            ]
        )
        for r in rows:
            bal = r.__dict__.get("running_balance")
            w.writerow(
                [
                    r.day.strftime("%d/%m/%y"),
                    r.narration,
                    r.ref,
                    r.day.strftime("%d/%m/%y"),
                    f"{r.withdrawal:.2f}" if r.withdrawal else "",
                    f"{r.deposit:.2f}" if r.deposit else "",
                    f"{bal:.2f}" if bal is not None else "",
                ]
            )


def _write_icici_csv(path: Path, rows: list[IciciRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(
            ["Transaction Date", "Transaction Details", "Ref No", "Amount (INR)", "Debit/Credit"]
        )
        for r in rows:
            w.writerow(
                [
                    r.day.strftime("%d-%m-%Y"),
                    r.details,
                    r.ref,
                    f"{r.amount:.2f}",
                    r.drcr,
                ]
            )


# --- Entry point -----------------------------------------------------------


def _months_back(anchor: date, n: int) -> list[tuple[int, int]]:
    """Return `n` (year, month) pairs ending at `anchor`, oldest first."""
    out: list[tuple[int, int]] = []
    y, m = anchor.year, anchor.month
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


@app.command()
def generate(
    output_dir: Path = typer.Option(Path("sample_data"), "--output-dir"),  # noqa: B008
    months: int = typer.Option(6, "--months", min=1, max=24),
    monthly_income: int = typer.Option(120000, "--monthly-income"),
    rent: int = typer.Option(35000, "--rent"),
    seed: int = typer.Option(42, "--seed"),
    anchor_year: int = typer.Option(2025, "--anchor-year"),
    anchor_month: int = typer.Option(6, "--anchor-month"),
) -> None:
    """Generate `months` of HDFC + ICICI dummy CSVs into `output_dir`."""
    random.seed(seed)
    fake = Faker("en_IN")
    Faker.seed(seed)

    output_dir.mkdir(parents=True, exist_ok=True)

    anchor = date(anchor_year, anchor_month, 1)
    month_list = _months_back(anchor, months)

    balance = Decimal("50000.00")  # starting HDFC balance
    for year, month in month_list:
        hdfc_rows, icici_rows, balance = _simulate_month(
            year, month, balance, Decimal(monthly_income), Decimal(rent), fake
        )
        stamp = f"{year}_{month:02d}"
        _write_hdfc_csv(output_dir / f"hdfc_savings_{stamp}.csv", hdfc_rows)
        _write_icici_csv(output_dir / f"icici_creditcard_{stamp}.csv", icici_rows)
        typer.echo(f"wrote {stamp}: HDFC={len(hdfc_rows)} rows, ICICI={len(icici_rows)} rows")


if __name__ == "__main__":
    app()

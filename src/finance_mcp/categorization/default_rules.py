"""Default categorization rules seeded at first DB init (PRD §8.2).

Each entry is ``(pattern, match_type, category_leaf_name, priority)``.
Patterns are matched case-insensitively against `clean_merchant` first
and fall back to `raw_description`. Lower ``priority`` means matched
earlier; ties broken by user-defined-first.

Keep patterns short and specific to the merchant's core brand token.
"""

from __future__ import annotations

# (pattern, match_type, category_leaf, priority)
DEFAULT_RULES: tuple[tuple[str, str, str, int], ...] = (
    # --- Food & Dining > Food Delivery --------------------------------------
    ("SWIGGY INSTAMART", "contains", "Groceries", 30),  # more specific wins
    ("SWIGGY", "contains", "Food Delivery", 50),
    ("ZOMATO", "contains", "Food Delivery", 50),
    ("DUNZO", "contains", "Food Delivery", 50),
    # --- Food & Dining > Groceries ------------------------------------------
    ("BLINKIT", "contains", "Groceries", 50),
    ("BIGBASKET", "contains", "Groceries", 50),
    ("BIG BASKET", "contains", "Groceries", 50),
    ("DMART", "contains", "Groceries", 50),
    ("RELIANCE FRESH", "contains", "Groceries", 50),
    # --- Food & Dining > Restaurants / Cafes -------------------------------
    ("STARBUCKS", "contains", "Cafes", 50),
    ("BLUE TOKAI", "contains", "Cafes", 50),
    # --- Transport > Ride-hailing -------------------------------------------
    ("UBER", "contains", "Ride-hailing", 50),
    ("OLA", "contains", "Ride-hailing", 50),
    ("RAPIDO", "contains", "Ride-hailing", 50),
    # --- Transport > Fuel ---------------------------------------------------
    ("INDIAN OIL", "contains", "Fuel", 50),
    ("BHARAT PETROLEUM", "contains", "Fuel", 50),
    ("HP PETROL", "contains", "Fuel", 50),
    # --- Transport > Public Transit ----------------------------------------
    ("IRCTC", "contains", "Public Transit", 50),
    ("BMRCL", "contains", "Public Transit", 50),
    # --- Utilities ----------------------------------------------------------
    ("BESCOM", "contains", "Electricity", 50),
    ("TNEB", "contains", "Electricity", 50),
    ("ACT FIBERNET", "contains", "Internet", 50),
    ("AIRTEL XSTREAM", "contains", "Internet", 40),
    ("JIO FIBER", "contains", "Internet", 40),
    ("AIRTEL", "contains", "Mobile", 60),
    ("VODAFONE", "contains", "Mobile", 60),
    ("JIO", "contains", "Mobile", 60),
    # --- Housing ------------------------------------------------------------
    ("LANDLORD RENT", "contains", "Rent", 40),
    ("RENT PAYMENT", "contains", "Rent", 45),
    # --- Entertainment > Streaming -----------------------------------------
    ("NETFLIX", "contains", "Streaming", 50),
    ("SPOTIFY", "contains", "Streaming", 50),
    ("PRIME VIDEO", "contains", "Streaming", 50),
    ("HOTSTAR", "contains", "Streaming", 50),
    # --- Shopping -----------------------------------------------------------
    ("AMAZON", "contains", "General", 70),
    ("FLIPKART", "contains", "General", 70),
    ("MYNTRA", "contains", "Clothing", 50),
    ("CROMA", "contains", "Electronics", 50),
    ("IKEA", "contains", "Home Supplies", 50),
    # --- Health -------------------------------------------------------------
    ("APOLLO PHARMACY", "contains", "Pharmacy", 50),
    ("1MG", "contains", "Pharmacy", 50),
    ("PHARMEASY", "contains", "Pharmacy", 50),
    ("CULT FIT", "contains", "Gym", 50),
    # --- Income -------------------------------------------------------------
    ("SALARY", "contains", "Salary", 30),
    ("INTEREST CREDIT", "contains", "Interest", 30),
    ("REFUND", "contains", "Refunds", 35),
    # --- Financial ----------------------------------------------------------
    ("CREDIT CARD PAYMENT", "contains", "Credit Card Payment", 20),
    ("PAYMENT THANK YOU", "contains", "Credit Card Payment", 20),
    # --- Travel -------------------------------------------------------------
    ("INDIGO", "contains", "Flights", 50),
    ("VISTARA", "contains", "Flights", 50),
    ("MAKEMYTRIP", "contains", "Flights", 60),
    ("OYO", "contains", "Hotels", 50),
)

__all__ = ["DEFAULT_RULES"]

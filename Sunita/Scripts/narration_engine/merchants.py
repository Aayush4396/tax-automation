# -*- coding: utf-8 -*-
"""
merchants.py
============
Maps UPI merchant VPA keywords to narration labels, account heads, and
confidence scores.

Usage:
    from narration_engine.merchants import detect_merchant

    result = detect_merchant("UPIOUT/413856144623/zomato-orders@icici")
    # → ("UPI - Zomato", "Food & Dining", 0.68)  or None
"""

from __future__ import annotations
import re

# ---------------------------------------------------------------------------
# MERCHANT_MAP
# (keyword, (label, account_head, confidence))
# Keywords are matched case-insensitively against the full particulars string.
# Order matters only for disambiguation — most specific first.
# ---------------------------------------------------------------------------
MERCHANT_MAP: list[tuple[str, tuple[str, str, float]]] = [

    # ── Food & Dining ──────────────────────────────────────────────────────
    ("zomato",         ("UPI - Zomato",       "Food & Dining",   0.68)),
    ("swiggy",         ("UPI - Swiggy",       "Food & Dining",   0.68)),
    ("eatsure",        ("UPI - EatSure",      "Food & Dining",   0.68)),
    ("dominos",        ("UPI - Dominos",      "Food & Dining",   0.68)),
    ("dominospizza",   ("UPI - Dominos",      "Food & Dining",   0.68)),
    ("mcdonalds",      ("UPI - McDonald's",   "Food & Dining",   0.68)),
    ("kfc",            ("UPI - KFC",          "Food & Dining",   0.68)),
    ("pizzahut",       ("UPI - Pizza Hut",    "Food & Dining",   0.68)),
    ("burgerking",     ("UPI - Burger King",  "Food & Dining",   0.68)),
    ("starbucks",      ("UPI - Starbucks",    "Food & Dining",   0.68)),

    # ── Groceries ──────────────────────────────────────────────────────────
    ("bigbasket",      ("UPI - BigBasket",    "Groceries",       0.68)),
    ("blinkit",        ("UPI - Blinkit",      "Groceries",       0.68)),
    ("zepto",          ("UPI - Zepto",        "Groceries",       0.68)),
    ("dunzo",          ("UPI - Dunzo",        "Groceries",       0.68)),
    ("jiomart",        ("UPI - JioMart",      "Groceries",       0.68)),
    ("grofers",        ("UPI - Blinkit",      "Groceries",       0.68)),   # Grofers rebranded to Blinkit
    ("milkbasket",     ("UPI - MilkBasket",   "Groceries",       0.68)),

    # ── Transport ──────────────────────────────────────────────────────────
    ("olacabs",        ("UPI - Ola",          "Transport",       0.68)),
    ("olaelectric",    ("UPI - Ola",          "Transport",       0.68)),
    ("uber",           ("UPI - Uber",         "Transport",       0.68)),
    ("rapido",         ("UPI - Rapido",       "Transport",       0.68)),
    ("yulu",           ("UPI - Yulu",         "Transport",       0.68)),
    ("blusmartmobili", ("UPI - BluSmart",     "Transport",       0.68)),
    ("nammayatri",     ("UPI - Namma Yatri",  "Transport",       0.68)),

    # ── Shopping ───────────────────────────────────────────────────────────
    ("amazon",         ("UPI - Amazon",       "Shopping",        0.68)),
    ("flipkart",       ("UPI - Flipkart",     "Shopping",        0.68)),
    ("myntra",         ("UPI - Myntra",       "Shopping",        0.68)),
    ("meesho",         ("UPI - Meesho",       "Shopping",        0.68)),
    ("ajio",           ("UPI - Ajio",         "Shopping",        0.68)),
    ("nykaa",          ("UPI - Nykaa",        "Shopping",        0.68)),
    ("tatacliq",       ("UPI - Tata CLiQ",    "Shopping",        0.68)),
    ("shopsy",         ("UPI - Shopsy",       "Shopping",        0.68)),
    ("snapdeal",       ("UPI - Snapdeal",     "Shopping",        0.68)),
    ("indiamart",      ("UPI - IndiaMart",    "Shopping",        0.68)),

    # ── Subscriptions ──────────────────────────────────────────────────────
    ("netflix",        ("UPI - Netflix",      "Subscriptions",   0.68)),
    ("spotify",        ("UPI - Spotify",      "Subscriptions",   0.68)),
    ("hotstar",        ("UPI - Hotstar",      "Subscriptions",   0.68)),
    ("jiocinema",      ("UPI - JioCinema",    "Subscriptions",   0.68)),
    ("primevideo",     ("UPI - Prime Video",  "Subscriptions",   0.68)),
    ("youtube",        ("UPI - YouTube",      "Subscriptions",   0.68)),
    ("appletv",        ("UPI - Apple TV",     "Subscriptions",   0.68)),
    ("sonyliv",        ("UPI - SonyLIV",      "Subscriptions",   0.68)),
    ("mxplayer",       ("UPI - MX Player",    "Subscriptions",   0.68)),
    ("zee5",           ("UPI - Zee5",         "Subscriptions",   0.68)),
    ("lenskart",       ("UPI - Lenskart",     "Shopping",        0.68)),

    # ── Credit Card / CRED Payments ────────────────────────────────────────
    # Order matters: most-specific patterns first (detect_merchant stops at first hit)
    ("cred.rent",      ("Rent Payment (via CRED)",           "Rent",         0.85)),
    ("CRED RENT",      ("Rent Payment (via CRED)",           "Rent",         0.85)),
    ("cred.club",      ("Credit Card Bill Payment (CRED)",   "Credit Card",  0.85)),
    ("CRED Club",      ("Credit Card Bill Payment (CRED)",   "Credit Card",  0.85)),
    ("CredClub",       ("Credit Card Bill Payment (CRED)",   "Credit Card",  0.85)),
    ("payment on CRED",("Credit Card Bill Payment (CRED)",   "Credit Card",  0.85)),
    ("cred.wallet",    ("UPI - CRED Wallet",                 "Personal",     0.75)),
    ("CRED WALLET",    ("UPI - CRED Wallet",                 "Personal",     0.75)),
    ("cred",           ("UPI - CRED",                        "Credit Card",  0.68)),

    # ── Wallets / Payment Apps ─────────────────────────────────────────────
    ("phonepe",        ("UPI - PhonePe",      "Personal",        0.65)),
    ("paytm",          ("UPI - Paytm",        "Personal",        0.65)),
    ("bharatpe",       ("UPI - BharatPe",     "Personal",        0.65)),
    ("navi",           ("UPI - Navi",         "Personal",        0.65)),
    ("gpay",           ("UPI - Google Pay",   "Personal",        0.65)),
    ("googlepay",      ("UPI - Google Pay",   "Personal",        0.65)),

    # ── Healthcare ─────────────────────────────────────────────────────────
    ("practo",         ("UPI - Practo",          "Healthcare",      0.68)),
    ("pharmeasy",      ("UPI - PharmEasy",        "Healthcare",      0.68)),
    ("apollopharm",    ("UPI - Apollo",            "Healthcare",      0.68)),
    ("netmeds",        ("UPI - Netmeds",           "Healthcare",      0.68)),
    ("1mg",            ("UPI - 1mg",               "Healthcare",      0.68)),
    ("medplus",        ("UPI - MedPlus",           "Healthcare",      0.68)),
    ("wellness forever",("UPI - Wellness Forever", "Healthcare",      0.68)),
    ("apollomedics",   ("UPI - Apollo Medics",     "Healthcare",      0.68)),

    # ── Utilities / Bills ──────────────────────────────────────────────────
    ("electricity",    ("UPI - Electricity",  "Utilities",       0.65)),
    ("bescom",         ("UPI - BESCOM",       "Utilities",       0.68)),
    ("tatapower",      ("UPI - Tata Power",   "Utilities",       0.68)),

    # ── Fuel & Petrol ─────────────────────────────────────────────────────
    ("HPCL",           ("UPI - Fuel (HPCL)",  "Fuel & Petrol",   0.80)),
    ("BPCL",           ("UPI - Fuel (BPCL)",  "Fuel & Petrol",   0.80)),
    ("IOCL",           ("UPI - Fuel (IOCL)",  "Fuel & Petrol",   0.80)),
    ("petromines",     ("UPI - Fuel",          "Fuel & Petrol",   0.75)),
    ("MATS FUEL",      ("UPI - Fuel",          "Fuel & Petrol",   0.75)),
    ("fuel park",      ("UPI - Fuel",          "Fuel & Petrol",   0.75)),

    # ── Tax Payments ─────────────────────────────────────────────────────
    ("CBDT",           ("Income Tax Payment",  "Tax",             0.85)),

    # ── Travel ─────────────────────────────────────────────────────────────
    ("irctc",          ("UPI - IRCTC",        "Travel",          0.68)),
    ("makemytrip",     ("UPI - MakeMyTrip",   "Travel",          0.68)),
    ("goibibo",        ("UPI - Goibibo",      "Travel",          0.68)),
    ("easemytrip",     ("UPI - EaseMyTrip",   "Travel",          0.68)),
    ("cleartrip",      ("UPI - Cleartrip",    "Travel",          0.68)),
    ("indigo",         ("UPI - IndiGo",       "Travel",          0.68)),
    ("airindia",       ("UPI - Air India",    "Travel",          0.68)),

    # ── Groceries (additional) ─────────────────────────────────────────────
    ("star bazaar",    ("UPI - Star Bazaar",  "Groceries",       0.70)),

    # ── Rewards / Cashback Apps ──────────────────────────────────────────
    ("supermoney",     ("SuperMoney (Rewards)", "Personal",       0.70)),

    # ── Investments ─────────────────────────────────────────────────────
    ("finzoomers",     ("Finzoomers Invest",   "Investments",     0.70)),
]

# Pre-compile for fast lookup
_COMPILED: list[tuple[re.Pattern, tuple[str, str, float]]] = [
    (re.compile(re.escape(kw), re.IGNORECASE), val)
    for kw, val in MERCHANT_MAP
]


def detect_merchant(particulars: str) -> tuple[str, str, float] | None:
    """
    Scan the particulars text for a known merchant keyword.

    Returns (label, account_head, confidence) on first match, else None.
    """
    p = str(particulars)
    for pattern, val in _COMPILED:
        if pattern.search(p):
            return val
    return None

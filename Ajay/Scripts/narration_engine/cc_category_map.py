# -*- coding: utf-8 -*-
"""
cc_category_map.py
==================
Maps Kotak CC statement SpendsArea categories → (Auto_Narration, Account_Head)
used in the CC Transactions sheet and Monthly Pivot CC SPENDS section.
"""

CC_NARRATION_MAP: dict[str, tuple[str, str]] = {
    "Grocery"           : ("CC - Groceries",    "Groceries"),
    "Restaurants"       : ("CC - Restaurants",   "Food & Dining"),
    "Entertainment"     : ("CC - Entertainment", "Entertainment"),
    "Telecom"           : ("CC - Telecom",        "Utilities"),
    "CC - Wifi"         : ("CC - Wifi",           "Utilities"),
    "DepartmentalStore" : ("CC - Shopping",       "Shopping"),
    "Automotive"        : ("CC - Automotive",     "Transport"),
    "Recreation"        : ("CC - Recreation",     "Entertainment"),
    "Services"          : ("CC - Services",       "Miscellaneous"),
    "OtherMerchants"    : ("CC - Other",          "Personal"),
    "Fuel"              : ("CC - Fuel",           "Transport"),
    "Insurance"         : ("CC - Insurance",      "Insurance"),
    "Healthcare"        : ("CC - Healthcare",     "Healthcare"),
    "Travel"            : ("CC - Travel",         "Travel"),
    "Education"         : ("CC - Education",      "Education"),
    "Utilities"         : ("CC - Utilities",      "Utilities"),
    # New categories found in statements
    "Jewelry"           : ("CC - Shopping",       "Shopping"),
    "Apparels"          : ("CC - Shopping",       "Shopping"),
    "Stationery"        : ("CC - Shopping",       "Shopping"),
    "ConsumerDurable"   : ("CC - Shopping",       "Shopping"),
    "Hardware"          : ("CC - Shopping",       "Shopping"),
    "Hotels"            : ("CC - Travel",         "Travel"),
    "Airline"           : ("CC - Travel",         "Travel"),
    "Railroads"         : ("CC - Travel",         "Travel"),
    "TravelAgencies"    : ("CC - Travel",         "Travel"),
    "Medical"           : ("CC - Healthcare",     "Healthcare"),
    "Computer"          : ("CC - Other",          "Personal"),
    "Commercial"        : ("CC - Other",          "Personal"),
    "DirectMarketing"   : ("CC - Other",          "Personal"),
}

# Colour map entries for exporter.py (hex fill, no #)
CC_COLOUR_MAP: dict[str, str] = {
    "CC - Groceries"    : "D5F5CC",
    "CC - Restaurants"  : "FFD5CC",
    "CC - Entertainment": "F5D0F5",
    "CC - Telecom"      : "D0F0E8",
    "CC - Wifi"         : "D5F0E8",
    "CC - Shopping"     : "F5E6CC",
    "CC - Automotive"   : "CCE8FF",
    "CC - Recreation"   : "EDD5F5",
    "CC - Services"     : "E8E8E8",
    "CC - Other"        : "F5F5DC",
    "CC - Fuel"         : "FFE8B3",
    "CC - Insurance"    : "D5E8F5",
    "CC - Healthcare"   : "CCFFE0",
    "CC - Travel"       : "D0E8FF",
    "CC - Education"    : "FFF0D0",
    "CC - Utilities"    : "D5F0E8",
}


def map_category(cc_category: str) -> tuple[str, str]:
    """Return (Auto_Narration, Account_Head) for a CC SpendsArea string."""
    return CC_NARRATION_MAP.get(
        cc_category,
        (f"CC - {cc_category}", "Miscellaneous")
    )

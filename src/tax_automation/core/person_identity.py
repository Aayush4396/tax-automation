"""Resolve person-name mentions without confusing embedded relatives' names."""

from functools import lru_cache
import re


@lru_cache(maxsize=512)
def _patterns(names, patterns, literals):
    compiled = []
    connectors = "TO|FROM|AND|FOR|BY|PAID|PAYMENT|RETURN|TRANSFER"
    for name in names:
        words = re.findall(r"[A-Z]+", name.upper())
        if len(words) < 2:
            continue
        if len(words) == 2:
            # Allow bounded middle names, but never cross payment grammar or
            # punctuation delimiting different counterparties.
            middle = rf"(?:\s+(?!(?:{connectors})\b)[A-Z]+){{0,2}}"
            expression = re.escape(words[0]) + middle + r"\s+" + re.escape(words[-1])
        else:
            expression = r"\s+".join(map(re.escape, words))
        compiled.append(re.compile(r"\b" + expression + r"\b", re.I))
    compiled.extend(re.compile(p, re.I) for p in patterns)
    compiled.extend(
        re.compile(r"(?<![\w.@-])" + re.escape(v) + r"(?![\w.@-])", re.I)
        for v in literals
    )
    return tuple(compiled)


def identity_matches(text, identities):
    """Suppress only strictly contained spans; distinct names and ties survive.

    identities maps stable keys to names, regex patterns and literal VPAs.
    No person names are hardcoded. Longer name spans dominate embedded names,
    regardless of profile order. Two aliases for the same full name stay ambiguous.
    """
    found = []
    for key, spec in identities.items():
        patterns = _patterns(
            tuple(spec.get("names", [])),
            tuple(spec.get("patterns", [])),
            tuple(spec.get("literals", [])),
        )
        for pattern in patterns:
            found.extend((key, m.start(), m.end()) for m in pattern.finditer(text))
    return {
        key
        for key, start, end in found
        if not any(
            other != key
            and left <= start
            and end <= right
            and right - left > end - start
            for other, left, right in found
        )
    }


def entity_identities(profile):
    """Include self and all declared relatives for shared family/contra logic."""
    identities = {
        "self": {
            "names": [
                profile.get("display_name", ""),
                *profile.get("identity_aliases", []),
            ],
            "patterns": profile.get("self_patterns", []),
            "literals": profile.get("self_vpas", []),
        }
    }
    for i, member in enumerate(profile.get("family_members", [])):
        identities[f"family:{i}"] = {
            "names": [member.get("name", ""), *member.get("identity_aliases", [])],
            "patterns": member.get("patterns", []),
            "literals": member.get("vpas", []),
        }
    return identities

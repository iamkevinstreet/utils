"""Deterministic made-up people and companies, plus near-duplicate variants for testing fuzzy matching.

Everything is seeded, so a test set regenerates identically. Nothing here is drawn from real records.
"""

from __future__ import annotations

import random
import re

_FIRST = (
    "Avery Jordan Morgan Riley Casey Quinn Taylor Reese Dakota Emerson Harper Rowan Sawyer Finley Skyler "
    "Blake Cameron Drew Elliot Hayden Jesse Kendall Logan Marlow Parker Peyton Sage Tatum Wren Zion Nico Luca "
    "Imani Aaliyah Priya Mateo Santiago Kenji Yuki Amara Zara Idris Omar Leila Noor Rafael Ines Bodhi Esme"
).split()
_LAST = (
    "Alvarez Bennett Castillo Dawson Ellison Foster Gallagher Hartley Iverson Jenkins Kowalski Lindqvist Moreno "
    "Nakamura Okafor Patel Quintero Rasmussen Sorensen Thornton Underwood Vasquez Whitaker Xiong Yamada Zielinski "
    "Abernathy Beaumont Calloway Delacroix Fairbanks Goldsmith Holloway Kingsley Lancaster Montgomery Pemberton"
).split()
_CO_WORDS = (
    "Acme Apex Beacon Cedar Cobalt Crestline Delta Evergreen Falcon Granite Harbor Ironwood Juniper Keystone "
    "Lakeside Meridian Northgate Oakridge Pinnacle Quarry Ridgeway Summit Timberline Union Vantage Westbrook"
).split()
_CO_KIND = "Logistics Holdings Partners Industries Medical Dental Builders Roofing Electric Plumbing Consulting Legal Staffing Foods Transport Analytics".split()
_SUFFIX = ["LLC", "Inc.", "Inc", "Corp.", "Co.", "LLP", "Group", ""]


class NameGen:
    def __init__(self, seed: int = 7):
        self.rng = random.Random(seed)

    def person(self) -> str:
        return f"{self.rng.choice(_FIRST)} {self.rng.choice(_LAST)}"

    def company(self) -> str:
        parts = [self.rng.choice(_CO_WORDS), self.rng.choice(_CO_KIND)]
        suffix = self.rng.choice(_SUFFIX)
        return " ".join(p for p in parts + [suffix] if p)

    def city_state(self) -> str:
        cities = [
            "Atlanta, GA",
            "Chicago, IL",
            "Dallas, TX",
            "Denver, CO",
            "Phoenix, AZ",
            "Columbus, OH",
            "Tampa, FL",
        ]
        return self.rng.choice(cities)


def near_duplicates(name: str, rng: random.Random | None = None) -> list[str]:
    """Variants a careless intake would produce: suffix swaps, dropped letters, punctuation and spacing changes."""
    rng = rng or random.Random(name)
    out: list[str] = []
    base = re.sub(r",?\s*(LLC|Inc\.?|Corp\.?|Co\.|LLP|Group)$", "", name).strip()
    for suffix in ("LLC", "Inc.", "Inc", "Corp", "Co."):
        if not name.endswith(suffix):
            out.append(f"{base} {suffix}")
    if base.endswith("s"):
        out.append(f"{base[:-1]} {rng.choice(['LLC', 'Inc.'])}")  # "Logistics" -> "Logistic"
    out.append(base.upper())
    out.append(base.replace(" ", ""))
    out.append(base.replace(" ", "-"))
    if len(base) > 6:
        i = rng.randrange(1, len(base) - 1)
        out.append(base[:i] + base[i + 1 :])  # one dropped character
    return list(dict.fromkeys(v for v in out if v and v != name))

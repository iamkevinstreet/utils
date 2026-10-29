########################################################################
#                   synthetic/kds/synthetic/names.py                   #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

Made-up people, companies and places, and the near-duplicate company
names a careless intake produces, for testing fuzzy matching.
Everything is seeded, so a test set regenerates identically, and
nothing here is drawn from real records.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
import random
import re

# Local
from kds.args import required

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Lists made-up first names")
FIRST = (
    "Avery Jordan Morgan Riley Casey Quinn Taylor Reese Dakota Emerson Harper Rowan Sawyer "
    "Finley Skyler Blake Cameron Drew Elliot Hayden Jesse Kendall Logan Marlow Parker Peyton "
    "Sage Tatum Wren Zion Nico Luca Imani Aaliyah Priya Mateo Santiago Kenji Yuki Amara Zara "
    "Idris Omar Leila Noor Rafael Ines Bodhi Esme"
).split()
# log.debug("Lists made-up last names")
LAST = (
    "Alvarez Bennett Castillo Dawson Ellison Foster Gallagher Hartley Iverson Jenkins Kowalski "
    "Lindqvist Moreno Nakamura Okafor Patel Quintero Rasmussen Sorensen Thornton Underwood "
    "Vasquez Whitaker Xiong Yamada Zielinski Abernathy Beaumont Calloway Delacroix Fairbanks "
    "Goldsmith Holloway Kingsley Lancaster Montgomery Pemberton"
).split()
# log.debug("Lists the first word of a made-up company")
COMPANY_WORDS = (
    "Acme Apex Beacon Cedar Cobalt Crestline Delta Evergreen Falcon Granite Harbor Ironwood "
    "Juniper Keystone Lakeside Meridian Northgate Oakridge Pinnacle Quarry Ridgeway Summit "
    "Timberline Union Vantage Westbrook"
).split()
# log.debug("Lists the kinds of business a company name ends with")
COMPANY_KINDS = (
    "Logistics Holdings Partners Industries Medical Dental Builders Roofing Electric Plumbing "
    "Consulting Legal Staffing Foods Transport Analytics"
).split()
# log.debug("Lists legal suffixes, including none")
SUFFIXES = ("LLC", "Inc.", "Inc", "Corp.", "Co.", "LLP", "Group", "")
# log.debug("Lists the suffixes a careless intake swaps in")
SWAPS = ("LLC", "Inc.", "Inc", "Corp", "Co.")
# log.debug("Lists made-up places in city, state form")
CITIES = (
    "Atlanta, GA",
    "Chicago, IL",
    "Dallas, TX",
    "Denver, CO",
    "Phoenix, AZ",
    "Columbus, OH",
    "Tampa, FL",
)
# log.debug("Matches a legal suffix at the end of a name")
SUFFIX_RE = re.compile(r",?\s*(LLC|Inc\.?|Corp\.?|Co\.|LLP|Group)$")
# log.debug("Sets the shortest base name that gets a dropped letter")
MIN_DROP_LENGTH = 6
# log.debug("Sets the default seed, so runs repeat")
DEFAULT_SEED = 7


########################################################################
#                            Made-up names                             #
########################################################################
# log.debug("Defines the seeded name generator")
class NameGen:
    """Made-up people, companies and places from one seeded source."""

    # log.debug("Defines the constructor with its seed")
    def __init__(self, seed: int = DEFAULT_SEED) -> None:
        """Seeds the generator so the same seed gives the same names.

        Args:
            seed: The seed for the random source behind every name.
        """
        # log.debug("Creates the seeded generator; repeatable, not secret")
        self.rng = random.Random(seed)  # noqa: S311 - test data, not security

    # log.debug("Defines a made-up person")
    def person(self) -> str:
        """Returns a first and last name.

        Returns:
            The name, first then last, with a space between.
        """
        # log.debug("Returns a random first and last name")
        return f"{self.rng.choice(FIRST)} {self.rng.choice(LAST)}"

    # log.debug("Defines a made-up company")
    def company(self) -> str:
        """Returns a word, a kind of business and maybe a suffix.

        Returns:
            The company's name, such as "Acme Logistics LLC".
        """
        # log.debug("Picks the three parts")
        parts = (
            self.rng.choice(COMPANY_WORDS),
            self.rng.choice(COMPANY_KINDS),
            self.rng.choice(SUFFIXES),
        )
        # log.debug("Returns the parts that are not empty, spaced")
        return " ".join(part for part in parts if part)

    # log.debug("Defines a made-up place")
    def city_state(self) -> str:
        """Returns a city and state.

        Returns:
            The place, such as "Denver, CO".
        """
        # log.debug("Returns a random place")
        return self.rng.choice(CITIES)


# log.debug("Defines the near duplicates of a company name")
def near_duplicates(name: str | None = None, rng: random.Random | None = None) -> list[str]:
    """Returns the variants a careless intake would produce.

    Suffix swaps, a dropped plural, capitals, lost or hyphenated
    spaces, and one dropped letter; never the name itself.

    Args:
        name: The company name to vary. Required.
        rng: The random source for the choices; if None, one seeded
            from the name, so a name's variants repeat.

    Returns:
        Each variant once, in the order made.
    """
    # log.debug("Takes the name, which the caller must give")
    name = required(name=name)
    # log.debug("Seeds from the name, so a name's variants repeat")
    rng = rng or random.Random(name)  # noqa: S311 - test data, not security
    # log.debug("Strips the legal suffix to get the base name")
    base = SUFFIX_RE.sub("", name).strip()
    # log.debug("Swaps in each suffix the name does not already end with")
    out = [f"{base} {suffix}" for suffix in SWAPS if not name.endswith(suffix)]
    # log.debug("Drops a trailing s, as in Logistics to Logistic")
    if base.endswith("s"):
        # log.debug("Adds the singular with a suffix")
        out.append(f"{base[:-1]} {rng.choice(['LLC', 'Inc.'])}")
    # log.debug("Adds the capitals, no-space and hyphenated forms")
    out += [base.upper(), base.replace(" ", ""), base.replace(" ", "-")]
    # log.debug("Drops one letter from a long enough name")
    if len(base) > MIN_DROP_LENGTH:
        # log.debug("Picks a letter that is not the first or last")
        i = rng.randrange(1, len(base) - 1)
        # log.debug("Adds the name without it")
        out.append(base[:i] + base[i + 1 :])
    # log.debug("Returns each variant once, in order, never the name")
    return list(dict.fromkeys(v for v in out if v and v != name))

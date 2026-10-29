########################################################################
#                  synthetic/tests/test_synthetic.py                   #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Tests repeatable names, the classic near-        #
#                     duplicate traps, and a PDF's text round trip.    #
########################################################################
"""Tests for kds.synthetic."""

from __future__ import annotations

import logging
from pathlib import Path

from kds.synthetic.names import NameGen, near_duplicates
from kds.synthetic.pdf import PdfDoc
from kds.synthetic.pdftext import pages_text, span_in_page

# Module constants
log = logging.getLogger(__name__)
# log.debug("Sets the charge line the PDF test places on page one")
CHARGE = "Charge No. 510-2026-01234"


# log.debug("Defines the test that a seed repeats its names")
def test_namegen_is_deterministic() -> None:
    """Two generators with one seed give the same names."""
    # log.debug("Builds two generators from the same seed")
    a, b = NameGen(seed=3), NameGen(seed=3)
    # log.debug("Checks five people match")
    assert [a.person() for _ in range(5)] == [b.person() for _ in range(5)]
    # log.debug("Checks the next company matches")
    assert a.company() == b.company()


# log.debug("Defines the test of the near-duplicate traps")
def test_near_duplicates_cover_the_classic_traps() -> None:
    """Suffix swap, dropped plural, capitals; never the name itself."""
    # log.debug("Makes the variants of one company name")
    variants = near_duplicates("Acme Logistics LLC")
    # log.debug("Checks a suffix swap")
    assert "Acme Logistics Inc." in variants
    # log.debug("Checks the dropped trailing s")
    assert any(v.startswith("Acme Logistic ") for v in variants)
    # log.debug("Checks the capitals form")
    assert "ACME LOGISTICS" in variants
    # log.debug("Checks the original is not among them")
    assert "Acme Logistics LLC" not in variants


# log.debug("Defines the test of a PDF's text round trip")
def test_pdf_roundtrip_and_span_check(tmp_path: Path) -> None:
    """Text written to a page is found on it, and only on it."""
    # log.debug("Starts a document")
    doc = PdfDoc(tmp_path / "charge.pdf")
    # log.debug("Adds the charge line to page one")
    doc.line(CHARGE)
    # log.debug("Ends page one")
    doc.page_break()
    # log.debug("Adds a paragraph to page two")
    doc.para("The particulars continue on this second page and describe the conduct.")
    # log.debug("Writes the PDF with page two rotated")
    doc.write(rotate_pages={2})
    # log.debug("Reads the pages back")
    pages = pages_text(doc.path)
    # log.debug("Checks there are two pages")
    assert len(pages) == 2
    # log.debug("Checks the charge line is on page one and not page two")
    assert span_in_page(CHARGE, pages[0]) and not span_in_page(CHARGE, pages[1])
    # log.debug("Checks spacing differences do not matter")
    assert span_in_page("second   page", pages[1])
    # log.debug("Checks a blank span is never found")
    assert not span_in_page("   ", pages[0])

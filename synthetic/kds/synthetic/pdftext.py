########################################################################
#                  synthetic/kds/synthetic/pdftext.py                  #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Reads a PDF back into page text, and checks a    #
#                     quoted span really appears on its cited page.    #
########################################################################
"""Page text from a PDF, the input every extraction prototype reads."""

from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader

# Module constants
log = logging.getLogger(__name__)


# log.debug("Defines reading a PDF's text page by page")
def pages_text(path: Path | str) -> list[str]:
    """Return each page's extracted text; an empty page gives ""."""
    # log.debug("Opens the PDF")
    reader = PdfReader(str(path))
    # log.debug("Returns each page's text")
    return [page.extract_text() or "" for page in reader.pages]


# log.debug("Defines the normal form spans are compared in")
def _flat(text: str) -> str:
    """Collapse all whitespace to single spaces and fold case."""
    # log.debug("Returns the folded, single-spaced text")
    return " ".join(text.split()).casefold()


# log.debug("Defines the check that a span is on its page")
def span_in_page(span: str, page: str) -> bool:
    """Return True if `span` is in `page`, ignoring spacing and case.

    An empty or blank span never counts as found.
    """
    # log.debug("Returns whether the non-blank span is in the page")
    return bool(span.strip()) and _flat(span) in _flat(page)

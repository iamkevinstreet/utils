########################################################################
#                  synthetic/kds/synthetic/pdftext.py                  #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

Reads a PDF back into page text, and checks a quoted span really appears
on its cited page.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging
from pathlib import Path

# Third-party
from pypdf import PdfReader

# Local
from kds.args import missing, required

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)


########################################################################
#                               PDF text                               #
########################################################################
# log.debug("Defines reading a PDF's text page by page")
def pages_text(path: Path | str | None = None) -> list[str]:
    """Returns each page's extracted text; an empty page gives "".

    Args:
        path: The PDF to read. Required.

    Returns:
        Each page's text, in page order.
    """
    # log.debug("Stops when the caller left out the path")
    if path is None:
        # log.debug("Raises the missing-argument error")
        raise missing(path=path)
    # log.debug("Opens the PDF")
    reader = PdfReader(str(path))
    # log.debug("Returns each page's text")
    return [page.extract_text() or "" for page in reader.pages]


# log.debug("Defines the normal form spans are compared in")
def _flat(text: str | None = None) -> str:
    """Collapses all whitespace to single spaces and folds case.

    Args:
        text: The text to flatten. Required.

    Returns:
        The text, single-spaced and case-folded.
    """
    # log.debug("Takes the text, which the caller must give")
    text = required(text=text)
    # log.debug("Returns the folded, single-spaced text")
    return " ".join(text.split()).casefold()


# log.debug("Defines the check that a span is on its page")
def span_in_page(span: str | None = None, page: str | None = None) -> bool:
    """Returns True if `span` is in `page`, ignoring spacing and case.

    An empty or blank span never counts as found.

    Args:
        span: The quoted span to look for. Required.
        page: The text of the page it cites. Required.

    Returns:
        True when the span is on the page.
    """
    # log.debug("Takes the span, which the caller must give")
    span = required(span=span)
    # log.debug("Takes the page, which the caller must give")
    page = required(page=page)
    # log.debug("Returns whether the non-blank span is in the page")
    return bool(span.strip()) and _flat(span) in _flat(page)

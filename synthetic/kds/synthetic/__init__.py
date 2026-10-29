########################################################################
#                 synthetic/kds/synthetic/__init__.py                  #
########################################################################
#  Author:            Kevin Street                                     #
#  Created on:        2026-10-14                                       #
#  Last modified on:  2026-10-29                                       #
#  Purpose:           Made-up names, near duplicates and PDFs that     #
#                     record their own page text.                      #
########################################################################
"""kds.synthetic: test data that is made up, repeatable, checkable."""

from __future__ import annotations

import logging

from kds.synthetic.names import NameGen, near_duplicates
from kds.synthetic.pdf import PdfDoc

# Module constants
log = logging.getLogger(__name__)
# log.debug("Lists what the package exports")
__all__ = ["NameGen", "PdfDoc", "near_duplicates"]

########################################################################
#                 synthetic/kds/synthetic/__init__.py                  #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-14
Last modified on:  2026-10-29

Made-up names, near duplicates and PDFs that record their own page text.
"""

########################################################################
#                               Imports                                #
########################################################################
# Standard library
from __future__ import annotations

import logging

# Local
from kds.synthetic.names import NameGen, near_duplicates
from kds.synthetic.pdf import PdfDoc

########################################################################
#                           Global constants                           #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                           Local constants                            #
########################################################################
# log.debug("Lists what the package exports")
__all__ = ["NameGen", "PdfDoc", "near_duplicates"]

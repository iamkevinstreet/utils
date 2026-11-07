########################################################################
#                                                                      #
#                      evals/kds/evals/config.py                       #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-11-07

The values the evaluation modules share, each named once. A library
cannot read a project's config files, so the values two of its modules
use live here.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging
from typing import Final

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = logging.getLogger(__name__)

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Sets the decimals a cost in dollars is rounded to")
COST_PLACES = 6
# log.debug("Names the event an evaluation result is recorded as")
GEN_AI_EVALUATION: Final = "gen_ai.evaluation.result"
# log.debug("Names the attribute that holds what was scored")
GEN_AI_EVALUATION_NAME: Final = "gen_ai.evaluation.name"
# log.debug("Names the attribute that holds a score as a number")
GEN_AI_SCORE_VALUE: Final = "gen_ai.evaluation.score.value"
# log.debug("Names the attribute that holds a score as a word")
GEN_AI_SCORE_LABEL: Final = "gen_ai.evaluation.score.label"

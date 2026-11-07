########################################################################
#                                                                      #
#                       evals/kds/evals/spans.py                       #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-07
Last modified on:  2026-11-07

Spans for evaluation runs. Each case runs as one span that records the
run and case, whether the case ran, and each score, both as attributes
and as an evaluation result in the OpenTelemetry GenAI conventions.

In Langfuse each case is then one trace, holding the case's model
calls, tools and searches, and a run's cases share one session.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

# Third-party
from opentelemetry.trace import Span, Status, StatusCode
from opentelemetry.util.types import AttributeValue

# Local
from kds.args import required
from kds.evals import config
from kds.evals.case import EvalCase
from kds.logs import set_values, step
from kds.logs.config import ERROR_TYPE

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
# log.debug("Names the code evaluation spans are recorded under")
SCOPE = "kds.evals"
# log.debug("Starts the name of every attribute an evaluation adds")
PREFIX = "kds.eval."


########################################################################
#                                                                      #
#                              Case spans                              #
#                                                                      #
########################################################################
# log.debug("Defines the span one case runs in")
@contextmanager
def case_span(run: str = "", case: EvalCase | None = None) -> Iterator[Span]:
    """Runs the block as one case's span, named for the case.

    Args:
        run: The run's name.
        case: The case being run. Required.

    Yields:
        The span, for scored() to record the outcome on.
    """
    # log.debug("Takes the case, which the caller must give")
    case = required(case=case)
    # log.debug("Names the run, the case and its tags")
    named = {f"{PREFIX}run": run, f"{PREFIX}case": case.id, f"{PREFIX}tags": case.tags}
    # log.debug("Opens the span; a case is its own trace")
    with step(f"eval {case.id}", named, scope=SCOPE) as span:
        # log.debug("Hands the span to the block")
        yield span


# log.debug("Defines how a case's span records its outcome")
def scored(
    span: Span | None = None, scores: Mapping[str, Any] | None = None, failure: str | None = None
) -> None:
    """Records whether the case ran, its scores, and any failure.

    Args:
        span: The case's span. Required.
        scores: The case's scores, a flat dict of numbers and booleans.
            Required.
        failure: The type of the error that stopped the case, if any.
    """
    # log.debug("Takes the span, which the caller must give")
    span = required(span=span)
    # log.debug("Takes the scores, which the caller must give")
    scores = required(scores=scores)
    # log.debug("Names each score as an attribute, beside whether it ran")
    named = {f"{PREFIX}score.{key}": value for key, value in scores.items()}
    # log.debug("Sets them on the span")
    set_values(span, {f"{PREFIX}ok": failure is None, **named})
    # log.debug("Adds each score as an evaluation result")
    for key, value in scores.items():
        # log.debug("Adds the result, unless the score is empty")
        if value is not None:
            # log.debug("Adds the event")
            span.add_event(config.GEN_AI_EVALUATION, result(key, value))
    # log.debug("Marks the case as failed when it did not run")
    if failure is not None:
        # log.debug("Records the error's type")
        span.set_attribute(ERROR_TYPE, failure)
        # log.debug("Marks the span as failed")
        span.set_status(Status(StatusCode.ERROR, failure))


# log.debug("Defines one score as an evaluation result")
def result(name: str | None = None, value: Any = None) -> dict[str, AttributeValue]:
    """Returns a score as the conventions record an evaluation result.

    Args:
        name: What was scored. Required.
        value: The score: a number, a yes or no, or a word. Required.

    Returns:
        The score's name, its value as a number when it is one or a
        yes or no, and its label when it is a word or a yes or no.
    """
    # log.debug("Takes the name, which the caller must give")
    name = required(name=name)
    # log.debug("Takes the value, which the caller must give")
    value = required(value=value)
    # log.debug("Starts with what was scored")
    found: dict[str, AttributeValue] = {config.GEN_AI_EVALUATION_NAME: name}
    # log.debug("Records a yes or no as 1 or 0, and as a word")
    if isinstance(value, bool):
        # log.debug("Adds both forms")
        found |= {
            config.GEN_AI_SCORE_VALUE: float(value),
            config.GEN_AI_SCORE_LABEL: str(value).lower(),
        }
    elif isinstance(value, int | float):
        # log.debug("Adds a number as it is")
        found[config.GEN_AI_SCORE_VALUE] = float(value)
    else:
        # log.debug("Adds anything else as a word")
        found[config.GEN_AI_SCORE_LABEL] = str(value)
    # log.debug("Returns the result")
    return found

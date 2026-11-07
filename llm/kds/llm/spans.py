########################################################################
#                                                                      #
#                         llm/kds/llm/spans.py                         #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-11-07
Last modified on:  2026-11-07

Spans for model calls, agents, tools and searches, named as the
OpenTelemetry GenAI conventions name them, so Langfuse and other
tracing tools show a model call as a generation, a tool call as a tool
and an agent's run as an agent.

The adapter opens a chat span around every model call, retries
included, and an embeddings span around every embedding call, so a
project gets those without writing anything. A project opens the rest
around its own work: agent() around an agent's run, tool() around each
tool call, retrieval() around a search.

Prompts, answers, tool arguments and results, and search queries can
hold personal data, so they are recorded only when spans_content is on.
"""

########################################################################
#                                                                      #
#                               Imports                                #
#                                                                      #
########################################################################
# Standard library
from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any, Final

# Third-party
from opentelemetry import trace
from opentelemetry.trace import Span, SpanKind

# Local
from kds.args import required
from kds.llm import config
from kds.llm.types import Completion, Message
from kds.logs import set_values, step
from kds.logs.config import ERROR_TYPE
from kds.settings import get_settings

########################################################################
#                                                                      #
#                           Global constants                           #
#                                                                      #
########################################################################
log = logging.getLogger(__name__)
# log.debug("Takes the key that holds what a message or block says")
CONTENT: Final = config.CONTENT
# log.debug("Takes the key that says what kind a content block is")
TYPE: Final = config.TYPE
# log.debug("Takes the key that holds a tool's name")
NAME: Final = config.NAME
# log.debug("Takes the part type that holds text")
TEXT: Final = config.TEXT
# log.debug("Takes the kind of tool a function call is")
FUNCTION: Final = config.FUNCTION

########################################################################
#                                                                      #
#                           Local constants                            #
#                                                                      #
########################################################################
# log.debug("Names the code these spans are recorded under")
SCOPE = "kds.llm"
# log.debug("Maps the adapter's provider names to the conventions' names")
PROVIDERS = {"azure": "azure.ai.openai"}
# log.debug("Names the key that holds a message's parts")
PARTS = "parts"
# log.debug("Names the key that holds a tool call's id")
ID = "id"
# log.debug("Names the event a retry is recorded as")
RETRY = "retry"
# log.debug("Names the kind Langfuse shows a search as")
RETRIEVER = "retriever"


########################################################################
#                                                                      #
#                             GenAI spans                              #
#                                                                      #
########################################################################
# log.debug("Defines the span around one model call")
@contextmanager
def chat(provider: str | None = None, request: Mapping[str, Any] | None = None) -> Iterator[Span]:
    """Runs the block as a chat span for one model call.

    Args:
        provider: The provider's name, as the adapter knows it.
            Required.
        request: The call's keyword arguments, as the adapter sends
            them to the provider. Required.

    Yields:
        The span, for record() to complete once the answer is back.
    """
    # log.debug("Takes the provider, which the caller must give")
    provider = required(provider=provider)
    # log.debug("Takes the request, which the caller must give")
    request = required(request=request)
    # log.debug("Names the model asked for")
    model = request["model"]
    # log.debug("Collects the call's settings as the conventions name them")
    attributes: dict[str, Any] = {
        config.GEN_AI_OPERATION: config.CHAT,
        config.GEN_AI_PROVIDER: PROVIDERS.get(provider, provider),
        config.GEN_AI_REQUEST_MODEL: model,
        config.GEN_AI_MAX_TOKENS: request.get("max_tokens"),
        config.GEN_AI_TEMPERATURE: request.get("temperature"),
    }
    # log.debug("Adds the prompt and the conversation when content is on")
    if get_settings().spans_content:
        # log.debug("Adds the system prompt as text parts")
        attributes[config.GEN_AI_SYSTEM] = _system(request.get("system"))
        # log.debug("Adds the conversation as role and parts")
        attributes[config.GEN_AI_INPUT] = [_message(m) for m in request["messages"]]
    # log.debug("Opens the span as a call to another service")
    with step(f"{config.CHAT} {model}", attributes, kind=SpanKind.CLIENT, scope=SCOPE) as span:
        # log.debug("Hands the span to the block")
        yield span


# log.debug("Defines how a model call's span records the answer")
def record(span: Span | None = None, completion: Completion | None = None) -> None:
    """Records the answer's model, tokens, cost and stop reason.

    Args:
        span: The chat span the call ran in. Required.
        completion: The priced completion. Required.
    """
    # log.debug("Takes the span, which the caller must give")
    span = required(span=span)
    # log.debug("Takes the completion, which the caller must give")
    completion = required(completion=completion)
    # log.debug("Collects what came back, as the conventions name it")
    found: dict[str, Any] = {
        config.GEN_AI_RESPONSE_MODEL: completion.model,
        config.GEN_AI_INPUT_TOKENS: completion.usage.input_tokens,
        config.GEN_AI_OUTPUT_TOKENS: completion.usage.output_tokens,
        config.GEN_AI_COST: completion.cost_usd,
        config.GEN_AI_FINISH_REASONS: [completion.stop_reason] if completion.stop_reason else None,
    }
    # log.debug("Adds the answer itself when content is on")
    if get_settings().spans_content:
        # log.debug("Adds the answer as one assistant message")
        found[config.GEN_AI_OUTPUT] = [_answer(completion)]
    # log.debug("Sets it all on the span")
    set_values(span, found)


# log.debug("Defines how a retry is recorded on the call's span")
def retried(attempt: int | None = None, delay_s: float = 0.0, error: str = "") -> None:
    """Adds a retry event to the model call's span.

    Args:
        attempt: The attempt that failed, counted from one. Required.
        delay_s: How long the adapter waits before the next attempt.
        error: The type of the error that failed the attempt.
    """
    # log.debug("Takes the attempt, which the caller must give")
    attempt = required(attempt=attempt)
    # log.debug("Adds the event to the span the call runs in")
    trace.get_current_span().add_event(
        RETRY, {"attempt": attempt, "delay_s": round(delay_s, 2), ERROR_TYPE: error}
    )


# log.debug("Defines the span around one embedding call")
@contextmanager
def embeddings(
    provider: str | None = None, model: str | None = None, texts: int = 0
) -> Iterator[Span]:
    """Runs the block as an embeddings span.

    Args:
        provider: The provider's name, as the adapter knows it.
            Required.
        model: The embedding model. Required.
        texts: How many texts are embedded.

    Yields:
        The span.
    """
    # log.debug("Takes the provider, which the caller must give")
    provider = required(provider=provider)
    # log.debug("Takes the model, which the caller must give")
    model = required(model=model)
    # log.debug("Collects the call's settings as the conventions name them")
    attributes = {
        config.GEN_AI_OPERATION: config.EMBEDDINGS,
        config.GEN_AI_PROVIDER: PROVIDERS.get(provider, provider),
        config.GEN_AI_REQUEST_MODEL: model,
    }
    # log.debug("Opens the span as a call to another service")
    with step(
        f"{config.EMBEDDINGS} {model}", attributes, kind=SpanKind.CLIENT, scope=SCOPE, texts=texts
    ) as span:
        # log.debug("Hands the span to the block")
        yield span


# log.debug("Defines the span around an agent's run")
@contextmanager
def agent(name: str | None = None, *, model: str | None = None) -> Iterator[Span]:
    """Runs the block as an agent's run: its model calls and tools.

    Args:
        name: The agent's name, such as "intake". Required.
        model: The model the agent calls.

    Yields:
        The span.
    """
    # log.debug("Takes the name, which the caller must give")
    name = required(name=name)
    # log.debug("Names the operation, the agent and its model")
    attributes = {
        config.GEN_AI_OPERATION: config.INVOKE_AGENT,
        config.GEN_AI_AGENT_NAME: name,
        config.GEN_AI_REQUEST_MODEL: model,
    }
    # log.debug("Opens the span; the agent runs in this process")
    with step(f"{config.INVOKE_AGENT} {name}", attributes, scope=SCOPE) as span:
        # log.debug("Hands the span to the block")
        yield span


# log.debug("Defines the span around one tool call")
@contextmanager
def tool(
    name: str | None = None, *, call_id: str | None = None, arguments: Any = None
) -> Iterator[Span]:
    """Runs the block as one tool call.

    Args:
        name: The tool's name. Required.
        call_id: The model's id for the call, when the model made it.
        arguments: The call's arguments; recorded when content is on.

    Yields:
        The span, for tool_result() to record what the tool returned.
    """
    # log.debug("Takes the name, which the caller must give")
    name = required(name=name)
    # log.debug("Names the operation, the tool and the call")
    attributes = {
        config.GEN_AI_OPERATION: config.EXECUTE_TOOL,
        config.GEN_AI_TOOL_NAME: name,
        config.GEN_AI_TOOL_TYPE: FUNCTION,
        config.GEN_AI_TOOL_CALL_ID: call_id,
        config.GEN_AI_TOOL_ARGUMENTS: arguments if get_settings().spans_content else None,
    }
    # log.debug("Opens the span")
    with step(f"{config.EXECUTE_TOOL} {name}", attributes, scope=SCOPE) as span:
        # log.debug("Hands the span to the block")
        yield span


# log.debug("Defines how a tool call's span records what came back")
def tool_result(span: Span | None = None, result: Any = None) -> None:
    """Records what the tool returned, when content is on.

    Args:
        span: The tool's span. Required.
        result: What the tool returned.
    """
    # log.debug("Takes the span, which the caller must give")
    span = required(span=span)
    # log.debug("Records the result only when content is on")
    if get_settings().spans_content:
        # log.debug("Sets it on the span")
        set_values(span, {config.GEN_AI_TOOL_RESULT: result})


# log.debug("Defines the span around a search")
@contextmanager
def retrieval(
    query: str | None = None, *, top_k: int | None = None, source: str | None = None
) -> Iterator[Span]:
    """Runs the block as a search for passages.

    Args:
        query: The text searched for; recorded when content is on.
            Required.
        top_k: How many results the search asks for.
        source: What is searched, such as "approved-sources".

    Yields:
        The span, for documents() to record what was found.
    """
    # log.debug("Takes the query, which the caller must give")
    query = required(query=query)
    # log.debug("Names the operation, the limit and what is searched")
    attributes = {
        config.GEN_AI_OPERATION: config.RETRIEVAL,
        config.GEN_AI_TOP_K: top_k,
        config.GEN_AI_DATA_SOURCE: source,
        config.GEN_AI_QUERY: query if get_settings().spans_content else None,
        config.LANGFUSE_TYPE: RETRIEVER,
    }
    # log.debug("Opens the span")
    with step(config.RETRIEVAL, attributes, scope=SCOPE) as span:
        # log.debug("Hands the span to the block")
        yield span


# log.debug("Defines how a search's span records what it found")
def documents(span: Span | None = None, found: Sequence[tuple[str, float]] | None = None) -> None:
    """Records each passage found, by id and score, best first.

    Args:
        span: The search's span. Required.
        found: Each passage's id and score, best first. Required.
    """
    # log.debug("Takes the span, which the caller must give")
    span = required(span=span)
    # log.debug("Takes the passages, which the caller must give")
    found = required(found=found)
    # log.debug("Sets them as the conventions list them")
    set_values(span, {config.GEN_AI_DOCUMENTS: [{ID: i, "score": s} for i, s in found]})


# log.debug("Defines how a system prompt is shown")
def _system(text: str | None = None) -> list[dict[str, Any]] | None:
    """Returns the system prompt as text parts, or None without one.

    Args:
        text: The system prompt.

    Returns:
        One text part holding the prompt, or None.
    """
    # log.debug("Returns one text part, or None without a prompt")
    return [{TYPE: TEXT, CONTENT: text}] if text else None


# log.debug("Defines how one turn is shown")
def _message(message: Message | None = None) -> dict[str, Any]:
    """Returns a turn as its role and parts, as the conventions show it.

    Args:
        message: The turn. Required.

    Returns:
        The role, and the turn's text, tool calls or tool result as
        parts.
    """
    # log.debug("Takes the turn, which the caller must give")
    message = required(message=message)
    # log.debug("Shows a tool's result as a response to its call")
    if message.tool_call_id is not None:
        # log.debug("Returns the result as one part")
        return {
            config.ROLE: message.role,
            PARTS: [
                {TYPE: "tool_call_response", ID: message.tool_call_id, "response": message.content}
            ],
        }
    # log.debug("Shows the text, then any tool calls the turn made")
    return {config.ROLE: message.role, PARTS: _parts(message.content, message.tool_calls)}


# log.debug("Defines how an answer is shown")
def _answer(completion: Completion | None = None) -> dict[str, Any]:
    """Returns the answer as one assistant message.

    Args:
        completion: The completion. Required.

    Returns:
        The role, the text and tool calls as parts, and why it stopped.
    """
    # log.debug("Takes the completion, which the caller must give")
    completion = required(completion=completion)
    # log.debug("Returns the answer as the conventions show it")
    return {
        config.ROLE: config.ASSISTANT,
        PARTS: _parts(completion.text, completion.tool_calls),
        "finish_reason": completion.stop_reason,
    }


# log.debug("Defines the parts of a turn")
def _parts(text: str = "", calls: Sequence[Any] = ()) -> list[dict[str, Any]]:
    """Returns the text as a part, then each tool call as a part.

    Args:
        text: What the turn says; left out when empty.
        calls: The tool calls the turn makes.

    Returns:
        The parts, in order.
    """
    # log.debug("Starts with the text, when there is any")
    parts: list[dict[str, Any]] = [{TYPE: TEXT, CONTENT: text}] if text else []
    # log.debug("Adds each tool call with its id, name and arguments")
    return parts + [
        {TYPE: "tool_call", ID: call.id, NAME: call.name, "arguments": call.arguments}
        for call in calls
    ]

########################################################################
#                                                                      #
#                        llm/kds/llm/config.py                         #
#                                                                      #
########################################################################
"""
Author:            Kevin Street
Created on:        2026-10-29
Last modified on:  2026-11-10

The values the model adapter's modules share, each named once. A library
cannot read a project's config files, so the values two of its modules
use live here.

The span attribute names follow the OpenTelemetry GenAI conventions,
which are still at Development stability and now live in their own
repository, open-telemetry/semantic-conventions-genai. These follow its
commit e6658f1 of Nov 6, 2026. Keeping them here makes a rename one
edit.
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
# log.debug("Sets the milliseconds in a second, for timing each call")
MS: Final = 1000
# log.debug("Names the key that says who speaks in a message")
ROLE: Final = "role"
# log.debug("Names the key that holds what a message or block says")
CONTENT: Final = "content"
# log.debug("Names the key that says what kind a content block is")
TYPE: Final = "type"
# log.debug("Names the key that holds a tool's name")
NAME: Final = "name"
# log.debug("Names the role of the person or program asking")
USER: Final = "user"
# log.debug("Names the role of the model answering")
ASSISTANT: Final = "assistant"
# log.debug("Names the content block type that holds text")
TEXT: Final = "text"
# log.debug("Names the kind of tool a function is, and the key its details sit under")
FUNCTION: Final = "function"
# log.debug("Names the attribute that says what kind of GenAI operation ran")
GEN_AI_OPERATION: Final = "gen_ai.operation.name"
# log.debug("Names the attribute that holds the provider's name")
GEN_AI_PROVIDER: Final = "gen_ai.provider.name"
# log.debug("Names the attribute that holds the model asked for")
GEN_AI_REQUEST_MODEL: Final = "gen_ai.request.model"
# log.debug("Names the attribute that holds the model that answered")
GEN_AI_RESPONSE_MODEL: Final = "gen_ai.response.model"
# log.debug("Names the attribute that holds the most tokens an answer may use")
GEN_AI_MAX_TOKENS: Final = "gen_ai.request.max_tokens"
# log.debug("Names the attribute that holds the sampling temperature")
GEN_AI_TEMPERATURE: Final = "gen_ai.request.temperature"
# log.debug("Names the attribute that holds the tokens read")
GEN_AI_INPUT_TOKENS: Final = "gen_ai.usage.input_tokens"
# log.debug("Names the attribute that holds the tokens written")
GEN_AI_OUTPUT_TOKENS: Final = "gen_ai.usage.output_tokens"
# log.debug("Names the cost attribute Langfuse reads; not in the conventions")
GEN_AI_COST: Final = "gen_ai.usage.cost"
# log.debug("Names the attribute that holds why the answer stopped")
GEN_AI_FINISH_REASONS: Final = "gen_ai.response.finish_reasons"
# log.debug("Names the attribute that holds the system prompt")
GEN_AI_SYSTEM: Final = "gen_ai.system_instructions"
# log.debug("Names the attribute that holds the conversation sent")
GEN_AI_INPUT: Final = "gen_ai.input.messages"
# log.debug("Names the attribute that holds the answer received")
GEN_AI_OUTPUT: Final = "gen_ai.output.messages"
# log.debug("Names the attribute that holds a tool's name")
GEN_AI_TOOL_NAME: Final = "gen_ai.tool.name"
# log.debug("Names the attribute that says what kind of tool ran")
GEN_AI_TOOL_TYPE: Final = "gen_ai.tool.type"
# log.debug("Names the attribute that holds the model's id for a tool call")
GEN_AI_TOOL_CALL_ID: Final = "gen_ai.tool.call.id"
# log.debug("Names the attribute that holds a tool call's arguments")
GEN_AI_TOOL_ARGUMENTS: Final = "gen_ai.tool.call.arguments"
# log.debug("Names the attribute that holds what a tool returned")
GEN_AI_TOOL_RESULT: Final = "gen_ai.tool.call.result"
# log.debug("Names the attribute that holds an agent's name")
GEN_AI_AGENT_NAME: Final = "gen_ai.agent.name"
# log.debug("Names the attribute that holds a search's query")
GEN_AI_QUERY: Final = "gen_ai.retrieval.query.text"
# log.debug("Names the attribute that holds how many results a search asks for")
GEN_AI_TOP_K: Final = "gen_ai.retrieval.top_k"
# log.debug("Names the attribute that holds what a search found")
GEN_AI_DOCUMENTS: Final = "gen_ai.retrieval.documents"
# log.debug("Names the attribute that holds what a search looked in")
GEN_AI_DATA_SOURCE: Final = "gen_ai.data_source.id"
# log.debug("Names the attribute Langfuse reads a span's kind from")
LANGFUSE_TYPE: Final = "langfuse.observation.type"
# log.debug("Names the attribute that says what a model call is for, where it is not the answer")
PURPOSE: Final = "kds.llm.purpose"
# log.debug("Names the purpose of a model call made to grade an answer")
JUDGE: Final = "judge"
# log.debug("Names the operation of a model call")
CHAT: Final = "chat"
# log.debug("Names the operation of an embedding call")
EMBEDDINGS: Final = "embeddings"
# log.debug("Names the operation of a tool call")
EXECUTE_TOOL: Final = "execute_tool"
# log.debug("Names the operation of an agent's run")
INVOKE_AGENT: Final = "invoke_agent"
# log.debug("Names the operation of a search")
RETRIEVAL: Final = "retrieval"

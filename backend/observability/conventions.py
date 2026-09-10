"""
OpenInference semantic-convention attribute keys used by this project.

These mirror the OpenInference conventions
(``openinference-semantic-conventions``) for span kinds and LLM I/O so that
traces exported to Phoenix render with the standard LLM/AGENT/CHAIN/TOOL
hierarchy. Keys are defined locally (instead of depending on the
conventions package) to keep the runtime dependency surface minimal; values
match the upstream convention strings exactly.
"""

from __future__ import annotations

# OpenInference span kinds (``openinference.span.kind``).
SPAN_KIND_LLM = "LLM"
SPAN_KIND_CHAIN = "CHAIN"
SPAN_KIND_AGENT = "AGENT"
SPAN_KIND_TOOL = "TOOL"
SPAN_KIND_RETRIEVER = "RETRIEVER"
SPAN_KIND_EMBEDDING = "EMBEDDING"
SPAN_KIND_RERANKER = "RERANKER"

OPENINFERENCE_SPAN_KIND = "openinference.span.kind"

# LLM I/O (input/output values are rendered by Phoenix trace views).
INPUT_VALUE = "input.value"
INPUT_MIME_TYPE = "input.mime_type"
OUTPUT_VALUE = "output.value"
OUTPUT_MIME_TYPE = "output.mime_type"
MIME_TEXT = "text/plain"
MIME_JSON = "application/json"

# Common LLM / metadata attributes.
LLM_MODEL_NAME = "llm.model_name"
LLM_PROVIDER = "llm.provider"
METADATA_PREFIX = "metadata."

# Project namespacing: every span/flow this codebase emits carries these so
# Phoenix filters and the DB bridge can attribute spans to a layer.
ATTR_LAYER = "careerintel.layer"
ATTR_FLOW = "careerintel.flow"
ATTR_PLATFORM = "careerintel.platform"

# Layers mirror the architecture diagram, top to bottom.
LAYER_CAREER = "career_intelligence"
LAYER_HERMES = "hermes_engine"
LAYER_MEMORY = "hermes_memory"
LAYER_SKILLS = "hermes_skills"
LAYER_AUTOMATION = "hermes_automation"
LAYER_CONTENT = "content_engine"
LAYER_SOCIAL = "social_apis"
LAYER_OBSERVABILITY = "observability"

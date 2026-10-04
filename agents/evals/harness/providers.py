"""Models behind one interface (ADR 0020): `provider:model`, each provider through its own official SDK.

    anthropic:<model>   the Anthropic SDK; ANTHROPIC_API_KEY (or an `ant auth login` profile)
    openai:<model>      the OpenAI SDK; OPENAI_API_KEY
    replay:<folder>     saved answers, <folder>/<paper>.json, for tests and re-scoring without a model

Every provider asks for an `Extraction` as structured output, so answers are schema-valid or recorded as failures.
None falls back to another model on a refusal: an eval must score the model it names.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from evals.harness.models import Extraction

MAX_TOKENS = 64_000  # streamed, so a long extraction isn't cut off by an HTTP timeout


@dataclass
class Answer:
    extraction: Extraction | None
    stop: str  # end_turn, refusal, max_tokens, invalid, error, …
    usage: dict[str, int] = field(default_factory=dict)
    detail: str | None = None


class Provider(Protocol):
    name: str

    def extract(self, paper: str, system: str, text: str) -> Answer: ...


class AnthropicProvider:
    def __init__(self, model: str, effort: str | None = "high", client=None):
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self.name, self.model, self.effort, self.client = f"anthropic:{model}", model, effort, client

    def extract(self, paper: str, system: str, text: str) -> Answer:
        options = {"output_config": {"effort": self.effort}} if self.effort else {}
        try:
            with self.client.messages.stream(model=self.model, max_tokens=MAX_TOKENS, system=system,
                                             messages=[{"role": "user", "content": text}], output_format=Extraction,
                                             **options) as stream:
                message = stream.get_final_message()
        except (ValidationError, ValueError) as error:  # output that isn't a valid Extraction (such as cut off)
            return Answer(None, "invalid", detail=str(error)[:500])
        usage = {"input_tokens": message.usage.input_tokens, "output_tokens": message.usage.output_tokens}
        if message.stop_reason == "refusal":
            details = getattr(message, "stop_details", None)
            return Answer(None, "refusal", usage, getattr(details, "category", None))
        if message.stop_reason == "max_tokens" or message.parsed_output is None:
            return Answer(None, message.stop_reason or "invalid", usage)
        return Answer(message.parsed_output, message.stop_reason, usage)


class OpenAIProvider:
    def __init__(self, model: str, effort: str | None = "high", client=None):
        if client is None:
            import openai

            client = openai.OpenAI()
        self.name, self.model, self.effort, self.client = f"openai:{model}", model, effort, client

    def extract(self, paper: str, system: str, text: str) -> Answer:
        options = {"reasoning": {"effort": self.effort}} if self.effort else {}
        try:
            response = self.client.responses.parse(model=self.model, instructions=system, input=text,
                                                   text_format=Extraction, **options)
        except (ValidationError, ValueError) as error:
            return Answer(None, "invalid", detail=str(error)[:500])
        usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
        if response.output_parsed is None:
            return Answer(None, getattr(response, "status", None) or "invalid", usage)
        return Answer(response.output_parsed, "end_turn", usage)


class ReplayProvider:
    def __init__(self, folder: str):
        self.name, self.folder = f"replay:{folder}", Path(folder)

    def extract(self, paper: str, system: str, text: str) -> Answer:
        saved = self.folder / f"{paper}.json"
        if not saved.exists():
            return Answer(None, "error", detail=f"no saved answer {saved}")
        try:
            return Answer(Extraction.model_validate(json.loads(saved.read_text(encoding="utf-8"))), "end_turn")
        except (ValidationError, ValueError) as error:
            return Answer(None, "invalid", detail=str(error)[:500])


def provider(spec: str, effort: str | None = "high") -> Provider:
    """A provider from `provider:model`."""
    kind, _, rest = spec.partition(":")
    if not rest:
        raise ValueError(f"{spec!r}: use provider:model, such as anthropic:claude-opus-5-5")
    if kind == "anthropic":
        return AnthropicProvider(rest, effort)
    if kind == "openai":
        return OpenAIProvider(rest, effort)
    if kind == "replay":
        return ReplayProvider(rest)
    raise ValueError(f"{spec!r}: unknown provider {kind!r} (anthropic, openai or replay)")

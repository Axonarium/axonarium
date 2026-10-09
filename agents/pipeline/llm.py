"""Model calls for the pipeline: many requests, each answered as a Pydantic model, on the Batch API or live.

The Batch API halves the price of every token and answers within a day, most batches within an hour (ADR 0028).
Live calls (`--now`) cost full price and suit small trials. A model's safety classifiers can refuse a request; the
Batch API takes no server-side fallbacks, so FallbackRunner sends refused requests to a second model itself, in the
same run. Each result names the model that answered it, and a claim records that model.
"""

import hashlib
import json
import re
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, TypeAdapter, ValidationError

from pipeline.corpus import UNANSWERED

# List prices in dollars per million tokens (input, output, cache read, cache write), from Anthropic's model table of
# 25 September 2026. Batches cost half. Reports only; the Console's spend limit is the real cap.
PRICES = {
    "claude-fable-5-1": (10.0, 50.0, 0.25, 12.5),
    "claude-opus-5-5": (4.0, 20.0, 0.20, 5.0),
    "claude-opus-5": (5.0, 25.0, 0.50, 6.25),
    "claude-sonnet-5-5": (2.0, 10.0, 0.20, 2.5),
    "claude-haiku-4-5": (1.0, 5.0, 0.10, 1.25),
}
USAGE = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def request_id(key: str) -> str:
    """A paper's request ID, the same in every run, so a batch's results can be matched to papers later. The key's
    letters and digits keep it readable; a hash of the whole key keeps it unique (the Batch API's custom_id: at most
    64 letters, digits, _ and -)."""
    readable = re.sub(r"[^A-Za-z0-9]+", "_", key).strip("_")[:48]
    return f"{readable}-{hashlib.sha256(key.encode()).hexdigest()[:12]}"


def choose(papers: list, run, limit: int, key: Callable = lambda paper: paper["key"]) -> list:
    """The papers to send: up to `limit`; or, when the runner collects an earlier batch, every one it holds."""
    known = getattr(run, "known", lambda: None)()
    if known is None:
        return papers[:limit]
    return [paper for paper in papers if request_id(key(paper)) in known]


@dataclass(frozen=True)
class Request:
    id: str  # request_id(paper key): unique within a run, stable across runs
    system: str
    text: str


@dataclass
class Result:
    parsed: BaseModel | None
    stop: str  # end_turn, refusal, max_tokens, invalid, errored, expired, canceled
    usage: dict[str, int] = field(default_factory=dict)
    detail: str | None = None
    model: str | None = None  # the model the request went to; None: the runner's own
    earlier: list["Result"] = field(default_factory=list)  # refused answers from other models before this one


def spend(results: Iterable[Result], model: str, batch: bool) -> tuple[dict[str, int], float | None]:
    """The tokens and dollars of these results and the refused answers before them, each at its own model's price;
    dollars are None when any model's price is unknown."""
    tries = [answer for result in results for answer in (*result.earlier, result)]
    usage = {kind: sum(answer.usage.get(kind, 0) for answer in tries) for kind in USAGE}
    if not tries:
        return usage, cost(model, usage, batch)
    dollars = [cost(answer.model or model, answer.usage, batch) for answer in tries]
    return usage, None if None in dollars else sum(dollars)


def cost(model: str, usage: dict[str, int], batch: bool) -> float | None:
    """Dollars for this usage at list price (half for a batch), or None for a model without a known price."""
    price = PRICES.get(model)
    if price is None:
        return None
    dollars = sum(usage.get(kind, 0) * rate for kind, rate in zip(USAGE, price, strict=True)) / 1_000_000
    return dollars / 2 if batch else dollars


def _usage(message) -> dict[str, int]:
    return {kind: getattr(message.usage, kind, 0) or 0 for kind in USAGE}


def parse(message, schema: type[BaseModel]) -> Result:
    """A finished message as a Result: its text validated against the schema, or why it can't be."""
    usage = _usage(message)
    if message.stop_reason == "refusal":
        details = getattr(message, "stop_details", None)
        return Result(None, "refusal", usage, getattr(details, "category", None))
    if message.stop_reason == "max_tokens":
        return Result(None, "max_tokens", usage)
    text = next((block.text for block in message.content if block.type == "text"), "")
    try:
        return Result(schema.model_validate_json(text), message.stop_reason or "end_turn", usage)
    except ValidationError as error:
        return Result(None, "invalid", usage, str(error)[:500])


class BatchPending(Exception):
    """A batch still running when the wait ran out. Its results can be collected later by its ID."""

    def __init__(self, batch_id: str):
        super().__init__(batch_id)
        self.batch_id = batch_id


class AnthropicRunner:
    """Requests to one Claude model with structured output, as one batch or as live calls."""

    def __init__(self, model: str, schema: type[BaseModel], effort: str | None, max_tokens: int, batch: bool = True,
                 client=None, poll_seconds: float = 60, wait_seconds: float = 5 * 3600, sleep: Callable = time.sleep,
                 collect_batch: str | None = None, clock: Callable[[], float] = time.monotonic):
        if client is None:
            import anthropic

            client = anthropic.Anthropic()
        self.model, self.schema, self.effort, self.max_tokens, self.batch = model, schema, effort, max_tokens, batch
        self.client, self.poll_seconds, self.sleep, self.clock = client, poll_seconds, sleep, clock
        # The wait counts from now, not from each batch, so a step's batches (its own and a fallback's) share it and a
        # run can be fitted into a time limit, such as a CI job's.
        self.deadline = clock() + wait_seconds
        # An earlier batch to collect instead of submitting a new one: its tokens are paid for already.
        self.collect_batch, self._collected = collect_batch, None

    @property
    def name(self) -> str:
        return f"anthropic:{self.model}"

    def params(self, request: Request) -> dict:
        from anthropic import transform_schema

        output_config = {"format": {"type": "json_schema", "schema": transform_schema(TypeAdapter(self.schema).json_schema())}}
        if self.effort:
            output_config["effort"] = self.effort
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            # The role prompt (and, for extraction, the region lexicon) is the same in every request, so it is cached.
            "system": [{"type": "text", "text": request.system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": request.text}],
            "output_config": output_config,
        }

    def latest(self) -> str:
        """The ID of the batch this workspace sent last, for when a run's log, and the ID in it, is lost."""
        batches = sorted(self.client.messages.batches.list(limit=20).data, key=lambda b: b.created_at, reverse=True)
        if not batches:
            raise ValueError("this workspace has no batches to collect")
        print(f"latest batch: {batches[0].id}, sent {batches[0].created_at:%Y-%m-%d %H:%M} UTC, "
              f"{batches[0].processing_status}", flush=True)
        return batches[0].id

    def collected(self) -> dict[str, Result]:
        """The results of the batch being collected, once; a batch none of whose answers fit this step's schema is
        another step's, and is refused before anything is written."""
        if self._collected is None:
            if self.collect_batch == "latest":
                self.collect_batch = self.latest()
            found = self.collect(self.collect_batch)
            answered = [r for r in found.values() if r.stop not in UNANSWERED]
            if answered and all(r.stop == "invalid" for r in answered):
                raise ValueError(f"batch {self.collect_batch} holds no answers this step can read: is it another step's?")
            self._collected = found
        return self._collected

    def known(self) -> set[str] | None:
        """The request IDs of the batch being collected (once it has ended), or None when a new batch is to be sent.
        Steps send only these papers' requests, so the results land on the papers they were asked about."""
        if self.collect_batch is None:
            return None
        return set(self.collected())

    def run(self, requests: list[Request]) -> dict[str, Result]:
        if not requests:
            return {}
        if self.collect_batch is not None:
            collected = self.collected()
            found = sum(r.id in collected for r in requests)
            print(f"batch {self.collect_batch}: {found} of its {len(collected)} result(s) collected", flush=True)
            return {r.id: collected.get(r.id) or Result(None, "errored", detail=f"not in batch {self.collect_batch}",
                                                        model=self.model) for r in requests}
        if not self.batch:
            results = {}
            for request in requests:
                with self.client.messages.stream(**self.params(request)) as stream:
                    results[request.id] = parse(stream.get_final_message(), self.schema)
                results[request.id].model = self.model
            return results
        batch = self.client.messages.batches.create(
            requests=[{"custom_id": request.id, "params": self.params(request)} for request in requests])
        print(f"batch {batch.id}: {len(requests)} request(s) submitted to {self.model}", flush=True)
        return self.collect(batch.id)

    def collect(self, batch_id: str) -> dict[str, Result]:
        """Wait for a batch (until the wait runs out), then its results. Raises BatchPending if it is still running."""
        while self.client.messages.batches.retrieve(batch_id).processing_status != "ended":
            if self.clock() >= self.deadline:
                raise BatchPending(batch_id)
            self.sleep(self.poll_seconds)
        results = {}
        for entry in self.client.messages.batches.results(batch_id):
            outcome = entry.result
            if outcome.type == "succeeded":
                results[entry.custom_id] = parse(outcome.message, self.schema)
            elif outcome.type == "errored":
                error = getattr(outcome, "error", None)
                results[entry.custom_id] = Result(None, "errored", detail=str(getattr(error, "error", error))[:500])
            else:  # canceled or expired
                results[entry.custom_id] = Result(None, outcome.type)
            results[entry.custom_id].model = self.model
        return results


class FallbackRunner:
    """A runner whose refused requests go to a second runner in the same run (ADR 0028). Claude Opus 5.5's bio
    classifier refuses some papers on viral tracers and drugs; the Batch API takes no server-side fallbacks. A request
    the fallback answers takes its answer, which keeps the refusal before it (its tokens are paid for too); one the
    fallback doesn't answer stays refused. If the fallback's batch is still running when the wait runs out, the
    refusals stand, and `pending` holds the batch's ID to collect later."""

    def __init__(self, primary, fallback):
        self.primary, self.fallback = primary, fallback
        self.model, self.batch = primary.model, getattr(primary, "batch", False)
        self.retried, self.pending = 0, None

    @property
    def name(self) -> str:
        return f"{self.primary.name}, refusals to {self.fallback.name}"

    def known(self) -> set[str] | None:
        return getattr(self.primary, "known", lambda: None)()

    def run(self, requests: list[Request]) -> dict[str, Result]:
        results = self.primary.run(requests)
        refused = [request for request in requests if results[request.id].stop == "refusal"]
        if not refused:
            return results
        print(f"{len(refused)} refusal(s) sent to {self.fallback.name}", flush=True)
        self.retried += len(refused)
        try:
            answers = self.fallback.run(refused)
        except BatchPending as pending:
            self.pending = pending.batch_id
            return results
        for request in refused:
            answer = answers[request.id]
            if answer.stop in UNANSWERED:  # no model answered: the refusal is the last answer
                continue
            refusal = results[request.id]
            answer.earlier = [*refusal.earlier, refusal]
            results[request.id] = answer
        return results


class ReplayRunner:
    """Saved answers, `<folder>/<request id>.json`, for tests and for re-running a step without a model. A saved
    `{"refusal": "<category>"}` stands for a refused request."""

    def __init__(self, folder: Path, schema: type[BaseModel], model: str = "replay"):
        self.folder, self.schema, self.model, self.batch = Path(folder), schema, model, False

    @property
    def name(self) -> str:
        return f"replay:{self.folder}"

    def run(self, requests: Iterable[Request]) -> dict[str, Result]:
        results = {}
        for request in requests:
            saved = self.folder / f"{request.id}.json"
            if not saved.exists():
                results[request.id] = Result(None, "errored", detail=f"no saved answer {saved}")
                continue
            try:
                answer = json.loads(saved.read_text(encoding="utf-8"))
                results[request.id] = Result(None, "refusal", detail=answer["refusal"]) if set(answer) == {"refusal"} \
                    else Result(self.schema.model_validate(answer), "end_turn")
            except (ValidationError, ValueError) as error:
                results[request.id] = Result(None, "invalid", detail=str(error)[:500])
            results[request.id].model = self.model
        return results


def runner(spec: str, schema: type[BaseModel], effort: str | None, max_tokens: int, batch: bool,
           collect_batch: str | None = None, wait_seconds: float = 5 * 3600):
    """A runner from `anthropic:<model>` or `replay:<folder>`; `collect_batch` collects an earlier batch instead, and
    batches are waited for until `wait_seconds` from now."""
    kind, _, rest = spec.partition(":")
    if collect_batch is not None and not (kind == "anthropic" and batch and re.fullmatch(r"msgbatch_\w+|latest", collect_batch)):
        raise ValueError("--collect takes a batch ID such as msgbatch_01ABC, or `latest`, with an anthropic: model and "
                         "without --now")
    if kind == "anthropic" and rest:
        return AnthropicRunner(rest, schema, effort, max_tokens, batch, collect_batch=collect_batch, wait_seconds=wait_seconds)
    if kind == "replay" and rest:
        return ReplayRunner(Path(rest), schema)
    raise ValueError(f"{spec!r}: use anthropic:<model>, such as anthropic:claude-opus-5-5, or replay:<folder>")

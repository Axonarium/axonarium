"""Paragraphs that read as instructions to a model, scored by Protect AI's prompt-injection classifier (ADR 0023).

The model is protectai/deberta-v3-base-prompt-injection-v2 (Apache-2.0): the default of LLM Guard's PromptInjection
scanner, which PhantomLint uses to find hidden prompts. It runs here through ONNX Runtime, from a pinned revision with
each file's SHA-256 checked, so it needs no PyTorch and a changed upload can't slip in. To move to a newer revision,
run `python -m screen.injection --pin` and copy what it prints.
"""

import hashlib
import json
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np
import onnxruntime
from huggingface_hub import HfApi, hf_hub_download
from tokenizers import Tokenizer

REPO = "protectai/deberta-v3-base-prompt-injection-v2"
REVISION = ""
FILES = {"onnx/config.json": "", "onnx/tokenizer.json": "", "onnx/model.onnx": ""}
THRESHOLD = 0.92  # LLM Guard's default for this model
WINDOW, STRIDE = 512, 128  # tokens: the model's limit, and how much a long paragraph's windows overlap

Classifier = Callable[[list[str]], list[float]]


def _sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def fetch(name: str, cache: Path | None = None) -> Path:
    """One of the model's files at the pinned revision, downloaded once and checked against its pinned hash."""
    path = Path(hf_hub_download(REPO, name, revision=REVISION, cache_dir=cache))
    if _sha256(path) != FILES[name]:
        raise ValueError(f"{REPO}/{name} at {REVISION} doesn't match its pinned SHA-256")
    return path


class ProtectAI:
    """Each paragraph's probability of being a prompt injection: the highest over its 512-token windows."""

    def __init__(self, cache: Path | None = None):
        if not REVISION or not all(FILES.values()):
            raise ValueError(f"{REPO} isn't pinned; run python -m screen.injection --pin")
        paths = {name: fetch(name, cache) for name in FILES}
        labels = json.loads(paths["onnx/config.json"].read_text(encoding="utf-8"))["id2label"]
        self.injection = next(int(i) for i, label in labels.items() if label.upper() == "INJECTION")
        self.tokenizer = Tokenizer.from_file(str(paths["onnx/tokenizer.json"]))
        self.tokenizer.no_padding()
        self.tokenizer.enable_truncation(WINDOW, stride=STRIDE)
        self.pad = self.tokenizer.token_to_id("[PAD]") or 0
        self.session = onnxruntime.InferenceSession(str(paths["onnx/model.onnx"]), providers=["CPUExecutionProvider"])
        self.inputs = [i.name for i in self.session.get_inputs()]

    def __call__(self, paragraphs: list[str]) -> list[float]:
        return [self._score(p) for p in paragraphs]

    def _score(self, paragraph: str) -> float:
        encoding = self.tokenizer.encode(paragraph)
        windows = [encoding, *encoding.overflowing]
        width = max(len(w.ids) for w in windows)
        ids = np.full((len(windows), width), self.pad, dtype=np.int64)
        mask = np.zeros((len(windows), width), dtype=np.int64)
        for row, window in enumerate(windows):
            ids[row, :len(window.ids)] = window.ids
            mask[row, :len(window.ids)] = 1
        feed = {"input_ids": ids, "attention_mask": mask, "token_type_ids": np.zeros_like(ids)}
        logits = self.session.run(None, {name: feed[name] for name in self.inputs})[0]
        exp = np.exp(logits - logits.max(axis=1, keepdims=True))
        return float((exp[:, self.injection] / exp.sum(axis=1)).max())


def pin() -> str:
    """The repository's current revision and its files' hashes, as the constants above."""
    api = HfApi()
    revision = api.model_info(REPO).sha
    names = api.list_repo_files(REPO, revision=revision)
    lines = [f"files at {revision}: {', '.join(sorted(names))}", f'REVISION = "{revision}"', "FILES = {"]
    for name in FILES:
        lines.append(f'    "{name}": "{_sha256(Path(hf_hub_download(REPO, name, revision=revision)))}",')
    return "\n".join([*lines, "}"])


if __name__ == "__main__":
    if sys.argv[1:] != ["--pin"]:
        sys.exit("usage: python -m screen.injection --pin")
    print(pin())

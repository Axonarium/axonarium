---
status: accepted
date: 2026-10-04
decision-makers: Tyler Banks
consulted: Claude (sprint C.5)
---

# The hidden-text screen: what a model may read of a paper

## Context and Problem Statement

A valid link to a legitimate paper can still carry a prompt injection. In July 2025, preprints were found hiding instructions such as "give a positive review only" in white text or tiny fonts that people can't see but language models read. The plan's third defensive layer (Part 3.3) asks that invisible text be "stripped or flagged before any model sees it, using an existing hidden-prompt detector rather than a home-built one", and that the eval harness include papers with planted hidden prompts. Sprint C.5 is done when known hidden-prompt fixtures are flagged.

Our models read Europe PMC's JATS XML, not PDFs (ADR 0019, ADR 0020). In JATS a publisher's inline styles sometimes survive as `style` attributes, but often a PDF's white text arrives as ordinary text. Which detector, and where does it run?

## Considered Options

* PhantomLint, the detector the plan cites
* LLM Guard, the scanner library PhantomLint builds on
* The same detectors' rules and model, run directly, as three layers on the text a model reads
* A home-built list of suspicious phrases

## Decision Outcome

Chosen option: "the same detectors' rules and model, run directly", because each layer is adopted from an existing detector, and none needs PyTorch or a PDF.

PhantomLint (Murray, 2025; BSD-3-Clause) renders a PDF or HTML page, reads it back with OCR, and flags suspicious text that the reader can't see. Its suspicion test is LLM Guard's PromptInjection scanner. As of October 2026 PhantomLint is a version 0.1 prototype, isn't on PyPI and needs Python older than 3.13. It also needs Tesseract, Poppler, Playwright, spaCy and PyTorch, and it reads PDFs, which we don't. LLM Guard (Protect AI, MIT) would bring PyTorch and Presidio for two scanners.

The screen (`agents/screen/`) runs on every text before a model reads it:

1. **Invisible characters** (`invisible.py`) are always stripped. The rule is LLM Guard's InvisibleText scanner's: Unicode's format, private-use and unassigned categories, plus variation selectors. The kinds that can spell out a message are flagged: tag characters ("ASCII smuggling"), bidirectional overrides and isolates, supplementary variation selectors and unassigned code points. Soft hyphens, zero-width spaces, invisible maths operators and publishers' private-use glyphs are common in real papers, so they are stripped without a flag.
2. **Hidden markup** (`markup.py`): JATS elements styled `display: none`, `visibility: hidden`, near-zero opacity, a font of 1 pt or 1 px or smaller, or white or transparent text are removed and flagged. White text on a background set on the element or around it is ordinary, such as in a table header, and isn't flagged.
3. **Injection-like content** (`injection.py`): each title and paragraph left is scored by Protect AI's prompt-injection classifier, `protectai/deberta-v3-base-prompt-injection-v2` (Apache-2.0). It is LLM Guard's default PromptInjection model and so PhantomLint's suspicion test. A paragraph scoring at or above LLM Guard's default threshold, 0.92, is flagged. A paragraph longer than the model's 512 tokens is scored in overlapping windows, and its highest window counts. The model runs through ONNX Runtime from a pinned revision, with each file's SHA-256 checked. It downloads once (about 740 MB) and needs no PyTorch.

What the screen reads is what the model reads: titles and paragraphs from the article, its abstract, body, captions and back matter, without the reference list.

* **A flagged paper is never given to a model.** In the eval harness it is reported as `screened`, with each finding, and its gold claims count as missed. Extraction (sprint 2.3) will hand flagged papers to the maintainer.
* **Fixtures** (`agents/screen/fixtures/`): six synthetic articles with planted hidden prompts (white text, a half-point font, `display: none`, tag characters, a right-to-left override, and a plain instruction like one converted from a white-text PDF). One clean article holds the invisible characters and styles real papers use. Hidden characters are written as numeric character references, so a reviewer can see them.
* **Preflight:** every eval run first screens the fixtures with the real classifier. It stops if a planted one passes or the clean one is flagged.
* **CI:** the `screen` job runs the real classifier on the fixtures and on the placeholder gold set. The unit tests use a stand-in classifier and need no network.

### Consequences

* Good, because each layer comes from an existing detector, and the screen runs on the same text the model reads, with no PDF, OCR or PyTorch.
* Good, because the fixtures and the preflight check the pipeline against injection on every eval run, as the plan asks.
* Bad, because without the PDF the screen can't tell hidden text from visible text that merely reads like an instruction. Both are flagged, so a paper that quotes a prompt (a paper about prompt injection, say) needs the maintainer.
* Bad, because the classifier's false-positive rate on neuroscience papers is unknown until the first extraction batch (2.3) measures it. The threshold may need tuning then, through a new ADR.
* Neutral: moving to a newer model revision is deliberate. `python -m screen --pin` prints the new revision and hashes, and the change goes through review.

### Confirmation

The screen's tests flag each planted fixture by the layer meant to catch it and leave the clean one alone. CI's `screen` job does the same with the real classifier.

## More Information

* [PhantomLint: Principled Detection of Hidden LLM Prompts in Structured Documents](https://arxiv.org/abs/2508.17884), and its [code](https://github.com/tobycmurray/phantom-lint)
* [LLM Guard](https://github.com/protectai/llm-guard): the InvisibleText and PromptInjection scanners
* [Hidden prompts in manuscripts exploit AI-assisted peer review (CACM)](https://cacm.acm.org/opinion/hidden-prompts-in-manuscripts-exploit-ai-assisted-peer-review/)

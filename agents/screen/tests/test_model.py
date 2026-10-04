"""The real classifier on the screen's fixtures and the placeholder gold set. It downloads the pinned model (about
740 MB, cached), so it runs only with AXONARIUM_SCREEN_MODEL=1: in CI's screen job, or locally on demand."""

import os

import pytest

from evals.harness import gold as goldsets
from evals.harness.run import AGENTS
from screen import preflight
from screen.injection import ProtectAI

pytestmark = pytest.mark.skipif(not os.environ.get("AXONARIUM_SCREEN_MODEL"), reason="needs AXONARIUM_SCREEN_MODEL=1")


@pytest.fixture(scope="module")
def classify():
    return ProtectAI()


def test_the_real_classifier_flags_every_planted_fixture_and_no_clean_one(classify):
    assert preflight(classify) == []


def test_the_placeholder_gold_set_is_not_flagged(classify):
    gold = goldsets.load(AGENTS / "evals" / "fixtures" / "placeholder")
    assert [p.name for p in gold.papers if goldsets.text(gold, p, classify).flagged] == []

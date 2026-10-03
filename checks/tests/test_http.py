"""The fetcher: polite, cached, retried GETs of JSON."""

import hashlib
import json

import pytest

from checks.http import USER_AGENT, Fetcher, LookupFailed

URL = "https://api.example.org/item/1"
NCBI = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id="


def ok(body=None):
    return 200, {}, json.dumps({"ok": True} if body is None else body).encode()


class Script:
    """A fake opener: each URL answers from its own list of responses or exceptions, in order."""

    def __init__(self, responses):
        self.responses = {url: list(answers) for url, answers in responses.items()}
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append((url, headers, timeout))
        answer = self.responses[url].pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


class Clock:
    """A fake monotonic clock that only moves when the fetcher sleeps, and a settable wall clock."""

    def __init__(self):
        self.t, self.wall_t, self.slept = 1000.0, 1_800_000_000.0, []

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.t += seconds

    def fetcher(self, opener, cache_dir=None):
        return Fetcher(cache_dir, opener, sleep=self.sleep, clock=lambda: self.t, wall=lambda: self.wall_t)


def test_returns_json_and_sends_user_agent():
    script, clock = Script({URL: [ok({"a": 1})]}), Clock()
    assert clock.fetcher(script).get_json(URL) == {"a": 1}
    _, headers, timeout = script.calls[0]
    assert headers["User-Agent"] == USER_AGENT == (
        "axonarium-checks (https://github.com/axonarium/axonarium; mailto:admin@axonarium.com)")
    assert headers["Accept"] == "application/json" and timeout == 30


@pytest.mark.parametrize("status", [404, 410])
def test_not_found_is_none(status):
    assert Clock().fetcher(Script({URL: [(status, {}, b"gone")]})).get_json(URL) is None


def test_unexpected_status_fails():
    with pytest.raises(LookupFailed, match="HTTP 400"):
        Clock().fetcher(Script({URL: [(400, {}, b"bad")]})).get_json(URL)


def test_bad_json_fails():
    with pytest.raises(LookupFailed, match="JSON"):
        Clock().fetcher(Script({URL: [(200, {}, b"<html>")]})).get_json(URL)


def test_retries_then_succeeds():
    script, clock = Script({URL: [(503, {}, b""), OSError("reset"), ok()]}), Clock()
    assert clock.fetcher(script).get_json(URL) == {"ok": True}
    assert clock.slept == [1, 2]


def test_gives_up_after_four_attempts():
    script, clock = Script({URL: [(500, {}, b"")] * 4}), Clock()
    fetcher = clock.fetcher(script)
    with pytest.raises(LookupFailed, match="HTTP 500") as error:
        fetcher.get_json(URL)
    assert error.value.url == URL and len(script.calls) == 4 and fetcher.requested == [URL] * 4


def test_retry_after_honoured():
    clock = Clock()
    clock.fetcher(Script({URL: [(429, {"Retry-After": "5"}, b""), ok()]})).get_json(URL)
    assert clock.slept == [5]


def test_retry_after_capped():
    clock = Clock()
    clock.fetcher(Script({URL: [(429, {"retry-after": "3600"}, b""), ok()]})).get_json(URL)
    assert clock.slept == [30]


def test_rate_limit_per_host():
    clock = Clock()
    fetcher = clock.fetcher(Script({NCBI + "1": [ok()], NCBI + "2": [ok()], URL: [ok()]}))
    fetcher.get_json(NCBI + "1")
    fetcher.get_json(URL)
    assert clock.slept == []  # another host doesn't wait
    fetcher.get_json(NCBI + "2")
    assert sum(clock.slept) == pytest.approx(0.4)


def test_cache_hit_skips_network(tmp_path):
    clock = Clock()
    clock.fetcher(Script({URL: [ok({"a": 1})]}), tmp_path).get_json(URL)
    entry = json.loads((tmp_path / f"{hashlib.sha256(URL.encode()).hexdigest()}.json").read_text())
    assert entry["url"] == URL and entry["body"] == {"a": 1} and entry["fetched_at"] == clock.wall_t
    second = Script({})
    assert clock.fetcher(second, tmp_path).get_json(URL) == {"a": 1}
    assert second.calls == []


def test_cache_expires_after_seven_days(tmp_path):
    clock = Clock()
    clock.fetcher(Script({URL: [ok({"a": 1})]}), tmp_path).get_json(URL)
    clock.wall_t += 7 * 24 * 3600 + 1
    assert clock.fetcher(Script({URL: [ok({"a": 2})]}), tmp_path).get_json(URL) == {"a": 2}


def test_not_found_not_cached(tmp_path):
    clock = Clock()
    clock.fetcher(Script({URL: [(404, {}, b"")]}), tmp_path).get_json(URL)
    assert list(tmp_path.iterdir()) == []


def test_corrupt_cache_entry_refetched(tmp_path):
    (tmp_path / f"{hashlib.sha256(URL.encode()).hexdigest()}.json").write_text("{not json")
    assert Clock().fetcher(Script({URL: [ok({"a": 3})]}), tmp_path).get_json(URL) == {"a": 3}

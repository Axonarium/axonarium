"""The fetcher: polite, cached, retried GETs of JSON, against a local server so the packages really run."""

import time
from datetime import timedelta

import pytest
import urllib3.util.retry
from werkzeug import Response

from checks.http import USER_AGENT, Fetcher, LookupFailed


class Sleeps:
    """Stands in for the time module inside urllib3's Retry: records its waits instead of waiting."""

    def __init__(self):
        self.slept = []

    def sleep(self, seconds):
        self.slept.append(seconds)

    def time(self):
        return time.time()


@pytest.fixture
def sleeps(monkeypatch):
    fake = Sleeps()
    monkeypatch.setattr(urllib3.util.retry, "time", fake)
    return fake


@pytest.fixture
def url(httpserver):
    return httpserver.url_for("/item/1")


def answer(httpserver, *responses, path="/item/1"):
    for response in responses:
        httpserver.expect_ordered_request(path).respond_with_response(response)


def json_response(body='{"ok": true}', status=200, headers=None):
    return Response(body, status=status, headers=headers, content_type="application/json")


def test_returns_json_and_sends_user_agent(httpserver, url):
    httpserver.expect_request("/item/1", headers={"User-Agent": USER_AGENT, "Accept": "application/json"}).respond_with_json({"a": 1})
    assert USER_AGENT == "axonarium-checks (https://github.com/axonarium/axonarium; mailto:admin@axonarium.com)"
    assert Fetcher().get_json(url) == {"a": 1}


@pytest.mark.parametrize("status", [404, 410])
def test_not_found_is_none(httpserver, url, status):
    answer(httpserver, json_response("gone", status))
    assert Fetcher().get_json(url) is None


def test_unexpected_status_fails_without_retrying(httpserver, url, sleeps):
    answer(httpserver, json_response("bad", 400))
    with pytest.raises(LookupFailed, match="HTTP 400"):
        Fetcher().get_json(url)
    assert len(httpserver.log) == 1 and sleeps.slept == []


def test_bad_json_fails(httpserver, url):
    answer(httpserver, Response("<html>", content_type="text/html"))
    with pytest.raises(LookupFailed, match="JSON"):
        Fetcher().get_json(url)


def test_retries_then_succeeds(httpserver, url, sleeps):
    answer(httpserver, json_response("", 503), json_response("", 502), json_response())
    assert Fetcher().get_json(url) == {"ok": True}
    assert len(httpserver.log) == 3 and sleeps.slept == sorted(sleeps.slept) and sleeps.slept[-1] > 0


def test_gives_up_after_four_attempts(httpserver, url, sleeps):
    answer(httpserver, *[json_response("", 500)] * 4)
    with pytest.raises(LookupFailed, match="HTTP 500 after 4 attempts") as error:
        Fetcher().get_json(url)
    assert error.value.url == url and len(httpserver.log) == 4


def test_retry_after_honoured(httpserver, url, sleeps):
    answer(httpserver, json_response("", 429, {"Retry-After": "5"}), json_response())
    Fetcher().get_json(url)
    assert sleeps.slept == [5]


def test_retry_after_capped(httpserver, url, sleeps):
    answer(httpserver, json_response("", 429, {"Retry-After": "3600"}), json_response())
    Fetcher().get_json(url)
    assert sleeps.slept == [30]


def test_rate_limit_per_host(httpserver):
    httpserver.expect_request("/item/1").respond_with_json({"ok": True})
    httpserver.expect_request("/item/2").respond_with_json({"ok": True})
    httpserver.expect_request("/item/3").respond_with_json({"ok": True})
    limited, other = f"http://localhost:{httpserver.port}", f"http://127.0.0.1:{httpserver.port}"
    fetcher = Fetcher(intervals={f"localhost:{httpserver.port}": 0.4})  # a host as URLs name it
    start = time.monotonic()
    fetcher.get_json(f"{limited}/item/1")
    fetcher.get_json(f"{other}/item/2")
    assert time.monotonic() - start < 0.3  # another host doesn't wait
    fetcher.get_json(f"{limited}/item/3")
    assert time.monotonic() - start >= 0.4


def test_cache_hit_skips_network(httpserver, url, tmp_path):
    answer(httpserver, json_response('{"a": 1}'))
    assert Fetcher(tmp_path).get_json(url) == {"a": 1}
    second = Fetcher(tmp_path)
    assert second.get_json(url) == {"a": 1} and second.requested == [] and len(httpserver.log) == 1


def test_cache_keeps_successes_for_seven_days(tmp_path):
    settings = Fetcher(tmp_path).session.settings
    assert settings.expire_after == timedelta(days=7) and settings.allowable_codes == (200,)
    assert settings.cache_control is False and settings.stale_if_error is False


def test_not_found_not_cached(httpserver, url, tmp_path):
    answer(httpserver, json_response("", 404), json_response("", 404))
    Fetcher(tmp_path).get_json(url)
    Fetcher(tmp_path).get_json(url)
    assert len(httpserver.log) == 2


def test_cache_not_read_when_disabled(httpserver, url, tmp_path):
    answer(httpserver, json_response('{"a": 1}'), json_response('{"a": 2}'))
    Fetcher(tmp_path).get_json(url)
    assert Fetcher(tmp_path, read_cache=False).get_json(url) == {"a": 2}
    assert Fetcher(tmp_path).get_json(url) == {"a": 2} and len(httpserver.log) == 2  # still written


def test_same_url_fetched_once_per_run(httpserver, url):
    answer(httpserver, json_response('{"a": 1}'))
    answer(httpserver, json_response("", 404), path="/item/2")
    fetcher = Fetcher()
    other = url.replace("/1", "/2")
    assert [fetcher.get_json(url), fetcher.get_json(url)] == [{"a": 1}, {"a": 1}]
    assert [fetcher.get_json(other), fetcher.get_json(other)] == [None, None]
    assert fetcher.requested == [url, other] and len(httpserver.log) == 2


def test_failure_remembered_per_url(httpserver, url, sleeps):
    answer(httpserver, *[json_response("", 500)] * 4)
    fetcher = Fetcher()
    for _ in range(2):
        with pytest.raises(LookupFailed):
            fetcher.get_json(url)
    assert len(httpserver.log) == 4


def test_host_given_up_after_an_outage(httpserver, sleeps):
    down = "http://127.0.0.1:9"  # nothing listens on the discard port: every attempt is refused
    httpserver.expect_request("/item/1").respond_with_json({"ok": True})
    fetcher = Fetcher()
    with pytest.raises(LookupFailed, match="after 4 attempts"):
        fetcher.get_json(f"{down}/a")
    assert sleeps.slept == [2, 4]  # urllib3 retries at once, then after 2 and 4 seconds: four attempts
    with pytest.raises(LookupFailed, match="unavailable"):
        fetcher.get_json(f"{down}/b")
    assert fetcher.get_json(f"http://localhost:{httpserver.port}/item/1") == {"ok": True}  # other hosts still asked


def test_client_errors_do_not_mark_a_host_down(httpserver, url):
    answer(httpserver, json_response("", 400))
    httpserver.expect_request("/item/2").respond_with_json({"ok": True})
    fetcher = Fetcher()
    with pytest.raises(LookupFailed):
        fetcher.get_json(url)
    assert fetcher.get_json(url.replace("/1", "/2")) == {"ok": True}


def test_invalid_url_not_retried(sleeps):
    with pytest.raises(LookupFailed, match="InvalidURL"):
        Fetcher().get_json("http:///item/1")  # no host
    assert sleeps.slept == []

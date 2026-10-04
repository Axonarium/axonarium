"""Polite, cached, retried GETs of JSON from the registries the online checks ask (ADR 0012).

The HTTP work is done by maintained packages: requests-cache keeps successful answers for seven days, urllib3's
Retry retries server errors and dropped connections (honouring Retry-After, capped), and requests-ratelimiter
spaces the requests to each host. This module only decides what an answer means, and fails closed.
"""

from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests
from requests.adapters import BaseAdapter
from requests_cache import CachedSession
from requests_ratelimiter import LimiterAdapter
from urllib3.util.retry import Retry

USER_AGENT = "axonarium-checks (https://github.com/axonarium/axonarium; mailto:admin@axonarium.com)"
TIMEOUT = 30  # seconds per request
TTL = timedelta(days=7)  # how long a cached answer is trusted
ATTEMPTS = 4
MAX_RETRY_AFTER = 30
INTERVALS = {"eutils.ncbi.nlm.nih.gov": 0.4}  # NCBI allows three requests a second without a key
DEFAULT_INTERVAL = 0.15
RETRY = Retry(total=ATTEMPTS - 1, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504), allowed_methods={"GET"},
              raise_on_status=False, respect_retry_after_header=True, retry_after_max=MAX_RETRY_AFTER)


class LookupFailed(Exception):
    """A registry couldn't be asked, or answered in a way the checks don't understand."""

    def __init__(self, url: str, reason: str):
        super().__init__(f"{url}: {reason}")
        self.url, self.reason = url, reason


def _spaced(interval: float, per_host: bool) -> LimiterAdapter:
    # One request per interval (a burst of one), with urllib3's retries underneath.
    return LimiterAdapter(per_second=1 / interval, burst=interval, per_host=per_host, max_retries=RETRY)


def session(cache_dir: Path | None, transport: BaseAdapter | None = None,
            intervals: dict[str, float] = INTERVALS) -> requests.Session:
    """A session that caches successful answers (with a cache folder), retries and rate-limits per host. A
    transport, such as recorded answers in tests, replaces the network."""
    s = (CachedSession(str(cache_dir / "http"), backend="filesystem", expire_after=TTL, allowable_codes=(200,),
                       allowable_methods=("GET",), cache_control=False, stale_if_error=False)
         if cache_dir else requests.Session())
    for scheme in ("https://", "http://"):
        s.mount(scheme, transport or _spaced(DEFAULT_INTERVAL, per_host=True))
        if transport is None:
            for host, interval in intervals.items():
                s.mount(f"{scheme}{host}/", _spaced(interval, per_host=False))
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return s


class Fetcher:
    """Fetches JSON once per URL per run, and stops asking a host after it fails every attempt."""

    def __init__(self, cache_dir: Path | None = None, transport: BaseAdapter | None = None, read_cache: bool = True,
                 intervals: dict[str, float] = INTERVALS):
        self.session = session(cache_dir, transport, intervals)
        self.read_cache = read_cache
        self.requested: list[str] = []  # URLs asked of the network (not answered from the cache), in order
        self._answers: dict[str, Any] = {}  # This run's answers and failures, so each URL is fetched once.
        self._down: dict[str, LookupFailed] = {}  # Hosts that failed every attempt; not asked again this run.

    def get_json(self, url: str) -> Any | None:
        """The parsed JSON of a 200 answer; None for 404 or 410; LookupFailed for anything else."""
        if url not in self._answers:
            try:
                self._answers[url] = self._get(url)
            except LookupFailed as error:
                self._answers[url] = error
        if isinstance(self._answers[url], LookupFailed):
            raise self._answers[url]
        return self._answers[url]

    def _get(self, url: str) -> Any | None:
        host = urlsplit(url).hostname or ""
        if host in self._down:
            raise LookupFailed(url, f"{host} was unavailable earlier in this run ({self._down[host].reason})")
        refresh = {"force_refresh": True} if isinstance(self.session, CachedSession) and not self.read_cache else {}
        try:
            response = self.session.get(url, timeout=TIMEOUT, **refresh)
        except (requests.exceptions.InvalidURL, requests.exceptions.InvalidHeader, ValueError) as error:
            raise LookupFailed(url, f"{type(error).__name__}: {error}") from None  # Retrying won't help.
        except requests.RequestException as error:
            self._down[host] = LookupFailed(url, f"{type(error).__name__} after {ATTEMPTS} attempts")
            raise self._down[host] from None
        if not getattr(response, "from_cache", False):
            self.requested.append(url)
        status = response.status_code
        if status == 200:
            try:
                return response.json()
            except ValueError:
                raise LookupFailed(url, "the response isn't JSON") from None
        if status in (404, 410):
            return None
        if status in RETRY.status_forcelist:
            self._down[host] = LookupFailed(url, f"HTTP {status} after {ATTEMPTS} attempts")
            raise self._down[host]
        raise LookupFailed(url, f"HTTP {status}")

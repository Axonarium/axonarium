"""Polite, cached, retried GETs of JSON from the registries the online checks ask."""

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

USER_AGENT = "axonarium-checks (https://github.com/axonarium/axonarium; mailto:admin@axonarium.com)"
TIMEOUT = 30  # seconds per request
TTL = 7 * 24 * 3600  # how long a cached answer is trusted
ATTEMPTS = 4
BACKOFF = (1, 2, 4)  # seconds to wait before the second, third and fourth attempts
MAX_RETRY_AFTER = 30
INTERVALS = {"eutils.ncbi.nlm.nih.gov": 0.4}  # NCBI allows three requests a second without a key
DEFAULT_INTERVAL = 0.15

Opener = Callable[[str, dict[str, str], float], tuple[int, dict[str, str], bytes]]
_MISSING = object()


class LookupFailed(Exception):
    """A registry couldn't be asked, or answered in a way the checks don't understand."""

    def __init__(self, url: str, reason: str):
        super().__init__(f"{url}: {reason}")
        self.url, self.reason = url, reason


def default_opener(url: str, headers: dict[str, str], timeout: float) -> tuple[int, dict[str, str], bytes]:
    """GET over the network; HTTP error statuses are returned, network failures raise OSError."""
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers or {}), error.read()


def _retry_after(headers: dict[str, str]) -> float | None:
    value = next((v for k, v in headers.items() if k.lower() == "retry-after"), None)
    try:
        return max(0.0, float(value)) if value is not None else None
    except ValueError:  # An HTTP date: fall back to the usual backoff.
        return None


class Fetcher:
    """Fetches JSON with a per-host rate limit, retries, and an optional on-disk cache of successful answers."""

    def __init__(self, cache_dir: Path | None = None, opener: Opener = default_opener,
                 sleep=time.sleep, clock=time.monotonic, wall=time.time):
        self.cache_dir, self.opener = cache_dir, opener
        self.sleep, self.clock, self.wall = sleep, clock, wall
        self.requested: list[str] = []
        self._last: dict[str, float] = {}

    def get_json(self, url: str) -> Any | None:
        """The parsed JSON of a 200 answer; None for 404 or 410; LookupFailed for anything else."""
        cached = self._cached(url)
        if cached is not _MISSING:
            return cached
        host = urlsplit(url).hostname or ""
        reason = ""
        for attempt in range(ATTEMPTS):
            self._wait_for(host)
            self.requested.append(url)
            delay = None
            try:
                status, headers, body = self.opener(url, {"User-Agent": USER_AGENT, "Accept": "application/json"}, TIMEOUT)
            except (OSError, HTTPException) as error:
                reason = f"{type(error).__name__}: {error}"
            else:
                if status == 200:
                    try:
                        data = json.loads(body)
                    except ValueError:
                        raise LookupFailed(url, "the response isn't JSON") from None
                    self._store(url, data)
                    return data
                if status in (404, 410):
                    return None
                if status != 429 and status < 500:
                    raise LookupFailed(url, f"HTTP {status}")
                reason, delay = f"HTTP {status}", _retry_after(headers)
            if attempt + 1 < ATTEMPTS:
                self.sleep(min(delay, MAX_RETRY_AFTER) if delay is not None else BACKOFF[attempt])
        raise LookupFailed(url, f"{reason} after {ATTEMPTS} attempts")

    def _wait_for(self, host: str) -> None:
        if host in self._last:
            wait = self._last[host] + INTERVALS.get(host, DEFAULT_INTERVAL) - self.clock()
            if wait > 0:
                self.sleep(wait)
        self._last[host] = self.clock()

    def _cache_path(self, url: str) -> Path | None:
        return self.cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.json" if self.cache_dir else None

    def _cached(self, url: str):
        path = self._cache_path(url)
        if path is None or not path.exists():
            return _MISSING
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            if entry["url"] == url and self.wall() - float(entry["fetched_at"]) < TTL:
                return entry["body"]
        except (OSError, ValueError, KeyError, TypeError):
            pass  # A damaged entry is simply fetched again.
        return _MISSING

    def _store(self, url: str, data) -> None:
        path = self._cache_path(url)
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(".tmp")
        partial.write_text(json.dumps({"url": url, "fetched_at": self.wall(), "body": data}), encoding="utf-8")
        os.replace(partial, path)

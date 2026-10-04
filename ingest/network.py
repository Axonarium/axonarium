"""The build's HTTP: one session for OLS, UBERON's bridges and the Allen API, retried, rate-limited per host and,
with a cache folder, cached for seven days. It is the online checks' session (checks/http.py, ADR 0012)."""

from collections.abc import Callable
from functools import partial
from pathlib import Path

from requests.adapters import BaseAdapter

from checks.http import session
from ingest.allen_connectivity import PAGE, _get, load_claims
from ingest.atlases import amygdala_terms, load_atlas


def loaders(cache_dir: Path | None = None, transport: BaseAdapter | None = None) -> tuple[Callable, Callable, Callable]:
    """The amygdala-term, atlas and Allen-connectivity loaders the build uses, sharing one session."""
    http = session(cache_dir, transport)

    def fetch(url: str, timeout: int = 120):
        response = http.get(url, timeout=timeout)
        response.raise_for_status()
        return response

    def allen(criteria: str, num_rows: int = PAGE, start_row: int = 0) -> list[dict]:
        return _get(criteria, num_rows, http, start_row)

    return (partial(amygdala_terms, lambda url: fetch(url, 60).json()),
            lambda atlas, terms: load_atlas(atlas, terms, fetch=lambda url: fetch(url).content),
            lambda atlas, structure_ids, acronyms: load_claims(atlas, structure_ids, acronyms, get=allen))

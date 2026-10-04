"""Rules that ask registries: terms and structures exist and aren't obsolete, citations exist and agree, sources are current."""

from collections.abc import Callable
from datetime import date
from pathlib import Path

from checks.findings import Finding, Record
from checks.http import Fetcher, LookupFailed
from checks.identifiers import canonical, canonical_source_id, citation_of, curies_in, source_key
from checks.lookups import ATLAS_GRAPHS, arxiv_doi, atlas_structure, doi_agency, ncbi_summary, ontology_term
from checks.sources import fetch_source, pubmed_says_retracted

CLAIMS = ("ConnectivityClaim", "HomologyClaim")
ATLAS_NAMES = {"MBA": "mouse", "HBA": "human", "DHBA": "human (Ding et al. 2016)"}
KINDS = {"doi": "DOI", "pmid": "PubMed ID", "pmcid": "PubMed Central ID", "arxiv": "arXiv ID"}
ODD_ANSWER = (TypeError, AttributeError, KeyError, ValueError, IndexError)  # A registry answer of an unexpected shape


def article_id(summary: dict, idtype: str) -> str | None:
    """The ID of type `idtype` (such as "doi" or "pmid") an NCBI summary gives, if any."""
    ids = summary.get("articleids") if isinstance(summary.get("articleids"), list) else []
    other = next((a.get("value") for a in ids if isinstance(a, dict) and a.get("idtype") == idtype), None)
    return other if isinstance(other, str) and other else None


def mismatched(cited: str, summary: dict, idtype: str) -> str | None:
    """The ID of type `idtype` an NCBI summary gives, if it differs (ignoring case) from the cited one."""
    other = article_id(summary, idtype)
    return other if other is not None and other.lower() != cited.lower() else None


def _show(value) -> str:
    return "(none)" if value is None else str(value).lower() if isinstance(value, bool) else str(value)


class _Asker:
    """Asks each question once per run and turns the answers into findings for the file that raised them."""

    def __init__(self, fetch: Fetcher, today: date):
        self.fetch, self.today = fetch, today
        self.answers: dict[tuple, object] = {}

    def _ask(self, key: tuple, question: Callable[[], object]):
        if key not in self.answers:
            try:
                self.answers[key] = question()
            except LookupFailed as error:
                self.answers[key] = error
            except ODD_ANSWER as error:
                self.answers[key] = LookupFailed(" ".join(key), f"unexpected answer from the registry ({type(error).__name__}: {error})")
        return self.answers[key]

    def _exists(self, path: str, key: tuple, question, missing: str) -> tuple[list[Finding], object]:
        """Findings for a lookup that failed or found nothing, and the answer."""
        answer = self._ask(key, question)
        if isinstance(answer, LookupFailed):
            return [Finding(path, "lookup-failed", f"lookup failed: {answer}")], None
        if answer is None:
            return [Finding(path, "unknown-citation", missing)], None
        return [], answer

    def term(self, path: str, curie: str) -> list[Finding]:
        if not canonical("curie", curie):
            return [Finding(path, "unknown-term", f"{curie!r} is not a canonical ID (ASCII digits only, nothing around them)")]
        prefix = curie.split(":")[0]
        if prefix in ATLAS_GRAPHS:
            answer = self._ask(("structure", curie), lambda: atlas_structure(self.fetch, curie))
        else:
            answer = self._ask(("term", curie), lambda: ontology_term(self.fetch, curie))
        if isinstance(answer, LookupFailed):
            return [Finding(path, "lookup-failed", f"lookup failed: {answer}")]
        if not answer.exists:
            where = f"a structure in the {ATLAS_NAMES[prefix]} atlas (Allen)" if prefix in ATLAS_GRAPHS else f"a term in {prefix} (OLS)"
            return [Finding(path, "unknown-term", f"{curie} is not {where}")]
        if answer.obsolete:
            replaced = f"; replaced by {answer.replaced_by}" if answer.replaced_by else ""
            return [Finding(path, "obsolete-term", f"{curie} is obsolete in {prefix}{replaced}")]
        return []

    def doi(self, path: str, doi: str, missing: str | None = None) -> list[Finding]:
        findings, _ = self._exists(path, ("doi", doi.lower()), lambda: doi_agency(self.fetch, doi),
                                   missing or f"DOI {doi} does not exist (doi.org)")
        return findings

    def pubmed(self, path: str, pmid: str) -> tuple[list[Finding], dict | None]:
        return self._exists(path, ("pubmed", pmid), lambda: ncbi_summary(self.fetch, "pubmed", pmid),
                            f"PubMed ID {pmid} does not exist (NCBI)")

    def pmc(self, path: str, pmcid: str) -> tuple[list[Finding], dict | None]:
        return self._exists(path, ("pmc", pmcid), lambda: ncbi_summary(self.fetch, "pmc", pmcid.removeprefix("PMC")),
                            f"PubMed Central ID {pmcid} does not exist (NCBI)")

    def arxiv(self, path: str, arxiv: str) -> list[Finding]:
        return self.doi(path, arxiv_doi(arxiv), f"arXiv ID {arxiv} does not exist (doi.org has no {arxiv_doi(arxiv)})")

    def citation(self, path: str, cited: dict[str, str], status=None) -> list[Finding]:
        findings, given, cited = [], set(cited), dict(cited)
        for kind, label in KINDS.items():
            if kind in cited and not canonical(kind, cited[kind]):
                findings.append(Finding(path, "unknown-citation", f"{label} {cited.pop(kind)!r} is not in canonical form"))
        doi, pmid, pmcid = cited.get("doi"), cited.get("pmid"), cited.get("pmcid")
        findings += self.doi(path, doi) if doi else []
        if pmid:
            found, summary = self.pubmed(path, pmid)
            findings += found
            if summary and doi and (other := mismatched(doi, summary, "doi")):
                findings.append(Finding(path, "citation-mismatch", f"PubMed {pmid} is {other}, not {doi}"))
            if summary and "doi" not in given and (other := article_id(summary, "doi")):
                findings.append(Finding(path, "citation-incomplete", f"PubMed {pmid} names DOI {other}; cite it too"))
            if summary and status != "retracted":
                findings += self._retracted_pmid(path, pmid, summary)
        if pmcid:
            found, summary = self.pmc(path, pmcid)
            findings += found
            if summary and doi and (other := mismatched(doi, summary, "doi")):
                findings.append(Finding(path, "citation-mismatch", f"PubMed Central {pmcid} is {other}, not {doi}"))
            if summary and pmid and (other := mismatched(pmid, summary, "pmid")):
                findings.append(Finding(path, "citation-mismatch", f"PubMed Central {pmcid} is PubMed {other}, not {pmid}"))
            if summary and "doi" not in given and (other := article_id(summary, "doi")):
                findings.append(Finding(path, "citation-incomplete", f"PubMed Central {pmcid} names DOI {other}; cite it too"))
            if summary and "pmid" not in given and (other := article_id(summary, "pmid")):
                findings.append(Finding(path, "citation-incomplete", f"PubMed Central {pmcid} names PubMed ID {other}; cite it too"))
        if cited.get("arxiv"):
            findings += self.arxiv(path, cited["arxiv"])
        return findings

    @staticmethod
    def _retracted_pmid(path: str, pmid: str, summary: dict) -> list[Finding]:
        """A cited PubMed ID that PubMed lists as retracted, whatever the claim's source record says."""
        try:
            retracted = pubmed_says_retracted(summary)
        except (TypeError, KeyError) as error:
            return [Finding(path, "lookup-failed", f"lookup failed: unexpected answer from NCBI for PubMed {pmid} ({error})")]
        if retracted:
            return [Finding(path, "cites-retracted", f"PubMed {pmid} is a retracted publication; set status: retracted and log it in retractions.yaml")]
        return []

    def source(self, path: str, data: dict) -> list[Finding]:
        source_id = data["id"]
        if not canonical_source_id(source_id):
            return [Finding(path, "unknown-citation", f"source ID {source_id!r} is not in canonical form")]
        findings, fresh = self._exists(path, ("source", source_id.lower()), lambda: fetch_source(self.fetch, source_id, self.today),
                                       f"{source_id} does not exist")
        for field in ("kind", "journal", "license", "retracted") if fresh else ():  # what the allowlist and rules trust
            if data.get(field) != fresh.get(field):
                findings.append(Finding(path, "source-outdated",
                                        f"source record says {field}: {_show(data.get(field))}, but its registry now gives "
                                        f"{_show(fresh.get(field))}; run python -m checks sources --refresh"))
        return findings


def check_online(records: list[Record], fetch: Fetcher, today: date, scope: set[Path] | None = None) -> list[Finding]:
    """Online findings for the records in scope (all if None), plus the source records their claims cite."""
    selected = [r for r in records if scope is None or r.path.resolve() in scope]
    if scope is not None:
        cited = {k.lower() for r in selected if r.cls in CLAIMS and (k := source_key(citation_of(r.data)))}
        chosen = {r.path for r in selected}
        selected += [r for r in records if r.cls == "Source" and r.path not in chosen
                     and isinstance(r.data.get("id"), str) and r.data["id"].lower() in cited]
    asker, findings = _Asker(fetch, today), []
    for record in selected:
        path = str(record.path)
        for curie in sorted(curies_in(record.data)):
            findings += asker.term(path, curie)
        if record.cls in CLAIMS:
            findings += asker.citation(path, citation_of(record.data), record.data.get("status"))
        if record.cls == "Source" and isinstance(record.data.get("id"), str) and ":" in record.data["id"]:
            findings += asker.source(path, record.data)
    return sorted(set(findings))

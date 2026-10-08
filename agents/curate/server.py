"""The curation tool's local server: the page, the paper, region search, and saving drafts in the gold format."""

import json
import re
import xml.etree.ElementTree as ET
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml
from pydantic import ValidationError

from evals.harness.models import Entity, GoldClaim, values
from pipeline import europepmc
from pipeline.corpus import read_manifest
from pipeline.extract import EVIDENCE, SPECIES, Lexicon
from screen.jats import blocks, local

PAGE = Path(__file__).with_name("page.html")
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
PMCID = re.compile(r"^PMC\d+$")
MATCHES = 25
ENUMS = {"predicate": "ConnectivityPredicate", "evidence_class": "EvidenceClass", "result": "Result", "sign": "Sign"}
EVIDENCE_FOR = {predicate: sorted(kinds) for predicate, kinds in EVIDENCE.items()}


class Curation:
    """What the server works with: the lexicon, the corpus manifest and the folder drafts are saved to."""

    def __init__(self, lexicon: Lexicon | None, out: Path, manifest: list[dict], fetch=europepmc.full_text):
        self.lexicon, self.out, self.fetch = lexicon, out, fetch
        self.by_pmcid = {p["pmcid"]: p for p in manifest if p.get("pmcid")}

    def paper(self, pmcid: str) -> dict:
        """The paper's titles and paragraphs, each marked as a heading or not, and its identifiers from the corpus."""
        if not PMCID.match(pmcid):
            raise ValueError(f"{pmcid!r} is not a PMC ID such as PMC8129205")
        root = ET.fromstring(self.fetch(pmcid))
        titles = {"".join(e.itertext()) for e in root.iter() if local(e.tag) in {"title", "article-title"}}
        found = [{"text": " ".join(b.split()), "heading": b in titles} for b in blocks(root) if b.strip()]
        known = self.by_pmcid.get(pmcid, {})
        source = {k: known[k] for k in ("doi", "pmid") if known.get(k)} | {"pmcid": pmcid}
        return {"pmcid": pmcid, "source": source, "title": known.get("title", ""), "blocks": found}

    def regions(self, query: str, species: str) -> list[dict]:
        """Regions and neuron types matching a query, for a species: exact acronyms first, then names."""
        if self.lexicon is None or not query.strip():
            return []
        words = query.lower().split()
        found = []
        for atlas, entry in self.lexicon.atlases.items():
            for region in entry["regions"]:
                text = f"{region['acronym']} {region['name']}".lower()
                if all(w in text for w in words):
                    use = region["id"] if entry["species"] == species else region.get("uberon")
                    if use and (entry["species"] == species or species != SPECIES["mouse"]):
                        found.append({"id": use, "type": "region", "label": f"{region['acronym']} · {region['name']}",
                                      "exact": region["acronym"].lower() == query.strip().lower(), "atlas": atlas})
        for neuron in self.lexicon.neuron_types:
            if neuron["species"] == species and all(w in neuron["name"].lower() for w in words):
                found.append({"id": neuron["id"], "type": "neuron_type", "label": neuron["name"], "exact": False, "atlas": None})
        unique = {(f["id"], f["type"]): f for f in sorted(found, key=lambda f: (not f["exact"], len(f["label"])))}
        return list(unique.values())[:MATCHES]

    def save(self, draft: dict) -> Path:
        """A paper's draft as `<out>/papers/<name>.yaml`, after checking every claim; ValueError says what's wrong."""
        name = str(draft.get("name", ""))
        if not NAME.match(name):
            raise ValueError("name: lowercase letters, digits and hyphens, such as hintiryan-2021")
        source = {k: str(v) for k, v in (draft.get("source") or {}).items() if k in ("doi", "pmid", "pmcid") and v}
        if not source:
            raise ValueError("source: give the paper's DOI, PubMed ID or PMC ID")
        claims, problems = [], []
        for number, raw in enumerate(draft.get("claims") or [], start=1):
            try:
                claim = GoldClaim.model_validate(raw)
            except ValidationError as error:
                problems.append(f"claim {number}: {error.errors()[0]['loc']}: {error.errors()[0]['msg']}")
                continue
            if self.lexicon is not None:
                for side in (claim.subject, claim.object):
                    _, problem = self.lexicon.entity(Entity(type=side.type, id=side.id, name_in_paper=""), claim.species)
                    if problem:
                        problems.append(f"claim {number}: {problem}")
            claims.append(claim.model_dump())
        if problems:
            raise ValueError("; ".join(problems))
        text = {"europe_pmc": source["pmcid"]} if "pmcid" in source else {"file": f"texts/{name}.txt"}
        path = self.out / "papers" / f"{name}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump({"source": source, "text": text, "claims": claims}, sort_keys=False,
                                       allow_unicode=True, width=120), encoding="utf-8")
        return path

    def load(self, name: str) -> dict:
        if not NAME.match(name):
            raise ValueError("not a draft name")
        path = self.out / "papers" / f"{name}.yaml"
        if not path.exists():
            raise ValueError(f"no draft {name}")
        return {"name": name, **yaml.safe_load(path.read_text(encoding="utf-8"))}

    def drafts(self) -> list[str]:
        return sorted(p.stem for p in (self.out / "papers").glob("*.yaml"))


def handler(curation: Curation):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, kind: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                             "script-src 'self' 'unsafe-inline'; connect-src 'self'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, value, status: int = HTTPStatus.OK) -> None:
            self._send(status, json.dumps(value).encode(), "application/json")

        def do_GET(self):  # noqa: N802 (the standard library's name)
            url = urlparse(self.path)
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            try:
                if url.path == "/":
                    self._send(HTTPStatus.OK, PAGE.read_bytes(), "text/html; charset=utf-8")
                elif url.path == "/favicon.ico":
                    self._send(HTTPStatus.NO_CONTENT, b"", "image/x-icon")
                elif url.path == "/api/paper":
                    self._json(curation.paper(query.get("pmcid", "")))
                elif url.path == "/api/regions":
                    self._json(curation.regions(query.get("q", ""), query.get("species", SPECIES["mouse"])))
                elif url.path == "/api/enums":
                    self._json({name: list(values(enum)) for name, enum in ENUMS.items()} | {"species": SPECIES,
                                                                                            "evidence_for": EVIDENCE_FOR})
                elif url.path == "/api/drafts":
                    self._json({"drafts": curation.drafts(), "out": str(curation.out), "lexicon": curation.lexicon is not None})
                elif url.path == "/api/draft":
                    self._json(curation.load(query.get("name", "")))
                else:
                    self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            except (ValueError, OSError, ET.ParseError) as error:
                self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def do_POST(self):  # noqa: N802
            # JSON only: a page elsewhere can't send it here without the browser asking first (CORS), so it can't
            # write drafts on the curator's behalf.
            if urlparse(self.path).path != "/api/save" or self.headers.get("Content-Type") != "application/json":
                self._json({"error": "POST JSON to /api/save"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                draft = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                path = curation.save(draft)
                self._json({"saved": str(path)})
            except (ValueError, TypeError, AttributeError) as error:
                self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def log_message(self, format, *args):  # noqa: A002 (the standard library's name)
            pass

    return Handler


def serve(curation: Curation, port: int) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), handler(curation))
    print(f"Curating at http://127.0.0.1:{port}; drafts go to {curation.out}. Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main(argv: list[str] | None = None) -> int:
    import argparse

    from pipeline.corpus import ROOT

    parser = argparse.ArgumentParser(prog="python -m curate", description="The gold curation tool (sprint 0.5a).")
    parser.add_argument("--lexicon", type=Path, default=ROOT / ".cache" / "lexicon.json", help="from `python -m ingest.lexicon`")
    parser.add_argument("--out", type=Path, default=ROOT / ".cache" / "gold-drafts", help="where drafts are saved")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    lexicon = Lexicon.load(args.lexicon) if args.lexicon.exists() else None
    if lexicon is None:
        print(f"No lexicon at {args.lexicon}: region search is off. Write one with "
              "`uv run --directory .. python -m ingest.lexicon --out .cache/lexicon.json`.")
    serve(Curation(lexicon, args.out, read_manifest()), args.port)
    return 0

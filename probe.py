"""Temporary: print the structure of WhiteText's and MouseLight's files, to design sprints 1.8 and 1.9."""

import collections
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "axonarium-probe (https://github.com/axonarium/axonarium)"}


def get(url, data=None, headers=None):
    request = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def section(title):
    print(f"\n===== {title} =====", flush=True)


def whitetext():
    section("WhiteText article")
    article = json.loads(get("https://api.figshare.com/v2/articles/1400541"))
    print("title:", article.get("title"))
    print("license:", article.get("license"))
    print("doi:", article.get("doi"), "version:", article.get("version"))
    print("description:", (article.get("description") or "")[:3000])
    for f in article.get("files", []):
        print("file:", f.get("name"), f.get("size"), f.get("download_url"), f.get("mimetype"))
    for f in article.get("files", []):
        if not f["name"].lower().endswith(".xml"):
            continue
        section(f"WhiteText file {f['name']}")
        body = get(f["download_url"])
        print("bytes:", len(body))
        print(body[:4000].decode("utf-8", "replace"))
        root = ET.fromstring(body)
        tags = collections.Counter()
        attributes = collections.defaultdict(collections.Counter)
        for element in root.iter():
            tags[element.tag] += 1
            for key in element.attrib:
                attributes[element.tag][key] += 1
        print("tags:", dict(tags))
        for tag, keys in attributes.items():
            print("attributes of", tag, dict(keys))
        for name in ("interaction", "type", "directed", "direction"):
            values = collections.Counter(e.get(name) for e in root.iter() if name in e.attrib)
            if values:
                print("values of", name, values.most_common(20))
        documents = list(root.iter("document"))
        print("documents:", len(documents))
        shown = 0
        for document in documents:
            entities = {e.get("id"): e for e in document.iter("entity")}
            for pair in document.iter("pair"):
                if pair.get("interaction") in ("True", "true") and shown < 25:
                    e1, e2 = entities.get(pair.get("e1")), entities.get(pair.get("e2"))
                    print("pair:", document.attrib, dict(pair.attrib),
                          "|", e1 is not None and dict(e1.attrib), "|", e2 is not None and dict(e2.attrib))
                    shown += 1
        names = collections.Counter(e.get("text", "").lower() for e in root.iter("entity"))
        print("distinct entity texts:", len(names))
        print("top entity texts:", names.most_common(80))
        amygdala = {n: c for n, c in names.items() if "amygd" in n or "basolateral" in n or "central nucleus" in n}
        print("amygdala-like entity texts:", sorted(amygdala.items(), key=lambda kv: -kv[1])[:80])


GRAPHQL = """query QueryData($filters: [FilterInput!]) { queryData(filters: $filters) { totalCount error { name message }
 neurons { id idString DOI consensus brainArea { id acronym name structureId }
 sample { id idNumber animalId tag sampleDate } tracings { id tracingStructure { name value } } } } }"""


def mouselight():
    section("MouseLight GraphQL")
    filters = [{"tracingIdsOrDOIs": ["AA"], "tracingIdsOrDOIsExactMatch": False, "tracingStructureIds": [],
                "nodeStructureIds": [], "operatorId": None, "amount": None, "brainAreaIds": [],
                "arbCenter": {"x": None, "y": None, "z": None}, "arbSize": None, "invert": False,
                "composition": None, "nonce": ""}]
    body = json.dumps({"query": GRAPHQL, "variables": {"filters": filters}, "operationName": "QueryData"}).encode()
    try:
        answer = json.loads(get("https://ml-neuronbrowser.janelia.org/graphql", body,
                                {"Content-Type": "application/json"}))
    except Exception as error:  # noqa: BLE001
        print("graphql failed:", repr(error), getattr(error, "read", lambda: b"")()[:2000])
        answer = {}
    data = (answer.get("data") or {}).get("queryData") or {}
    print("errors:", answer.get("errors"), data.get("error"))
    neurons = data.get("neurons") or []
    print("totalCount:", data.get("totalCount"), "returned:", len(neurons))
    for neuron in neurons[:3]:
        print(json.dumps(neuron)[:1500])
    areas = collections.Counter((n.get("brainArea") or {}).get("acronym") for n in neurons)
    print("soma areas:", areas.most_common(300))
    dois = collections.Counter(bool(n.get("DOI")) for n in neurons)
    print("has DOI:", dois)
    amygdala = [n for n in neurons if (n.get("brainArea") or {}).get("acronym") in
                {"LA", "BLA", "BLAa", "BLAp", "BLAv", "BMA", "BMAa", "BMAp", "CEA", "CEAc", "CEAl", "CEAm", "MEA",
                 "COA", "COAa", "COAp", "PA", "IA", "AAA", "BA", "CLA", "EP", "EPd", "EPv", "sAMY", "PAA", "TR"}]
    print("amygdala-ish somas:", [(n["idString"], n["brainArea"]["acronym"], n.get("DOI")) for n in amygdala])

    section("MouseLight export")
    for ids in (["AA0001"], [n["idString"] for n in amygdala[:2]] or ["AA0100"]):
        body = json.dumps({"ids": ids, "ccfVersion": 1, "format": 1}).encode()
        try:
            raw = get("https://ml-neuronbrowser.janelia.org/export", body, {"Content-Type": "application/json"})
        except Exception as error:  # noqa: BLE001
            print("export failed:", repr(error))
            continue
        print("bytes:", len(raw))
        answer = json.loads(raw)
        print("top keys:", list(answer))
        contents = answer.get("contents", answer)
        if isinstance(contents, str):
            print("contents is a string:", contents[:500])
            continue
        print("contents keys:", list(contents))
        print("comment:", str(contents.get("comment"))[:1000])
        for neuron in contents.get("neurons", [])[:2]:
            print("neuron keys:", list(neuron))
            print("scalars:", {k: v for k, v in neuron.items() if not isinstance(v, (list, dict))})
            print("sample:", neuron.get("sample"), "label:", neuron.get("label"),
                  "annotationSpace:", neuron.get("annotationSpace"))
            print("soma:", neuron.get("soma"))
            for part in ("axon", "dendrite"):
                nodes = neuron.get(part) or []
                print(part, "nodes:", len(nodes), "first:", nodes[:2])
                print(part, "allenIds:", collections.Counter(n.get("allenId") for n in nodes).most_common(15))
                print(part, "structureIdentifier:", collections.Counter(n.get("structureIdentifier") for n in nodes))
            info = neuron.get("allenInformation") or []
            print("allenInformation:", len(info), info[:3])

    section("MouseLight figshare licences")
    collection = json.loads(get("https://api.figshare.com/v2/collections/3924067/articles?page_size=1000"))
    print("collection articles (first page):", len(collection))
    for article in collection[:2]:
        print(article)
    picks = collection[:: max(1, len(collection) // 25)][:30]
    for article in picks:
        detail = json.loads(get(f"https://api.figshare.com/v2/articles/{article['id']}"))
        print(article["id"], detail.get("title"), detail.get("doi"), (detail.get("license") or {}).get("name"),
              detail.get("published_date"), [f["name"] for f in detail.get("files", [])][:4])


if __name__ == "__main__":
    for step in sys.argv[1:]:
        try:
            {"whitetext": whitetext, "mouselight": mouselight}[step]()
        except Exception as error:  # noqa: BLE001
            print(step, "failed:", repr(error))

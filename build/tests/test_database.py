"""Loading Postgres: run against AXONARIUM_TEST_DATABASE_URL (a Postgres service in CI); skipped without it."""

import copy
import os

import psycopg
import pytest

from build.database import LoadFailed, load
from build.tables import TABLES, rows
from checks.loading import load_tree

URL = os.environ.get("AXONARIUM_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="needs AXONARIUM_TEST_DATABASE_URL")


def query(sql: str, *params):
    with psycopg.connect(URL) as conn:
        return conn.execute(sql, params).fetchall()


def counts() -> dict[str, int]:
    return {name: query(f"select count(*) from {name}")[0][0] for name in TABLES}


@pytest.fixture
def tables(valid_tree):
    records, findings = load_tree(valid_tree)
    assert findings == []
    return rows(records)


def test_load_into_empty_database(tables):
    load(URL, tables)
    assert counts() == {name: len(table) for name, table in tables.items()}
    subject, measurements, curation = query(
        "select subject_id, measurements, curation from connectivity_claims where id = %s", "clm-pq22bk4dtz")[0]
    assert subject == "MBA:295" and measurements[0]["value"] == 0.12 and curation["by"] == "agent"
    basis = query("select basis from homology_claims order by id limit 1")[0][0]
    assert isinstance(basis, list) and basis


def test_reload_replaces(tables):
    load(URL, tables)
    fewer = copy.deepcopy(tables)
    fewer["connectivity_claims"] = [r for r in fewer["connectivity_claims"] if r["id"] != "clm-pq22bk4dtz"]
    load(URL, fewer)
    assert counts()["connectivity_claims"] == len(tables["connectivity_claims"]) - 1
    assert query("select count(*) from connectivity_claims where id = %s", "clm-pq22bk4dtz")[0][0] == 0


def test_failed_load_keeps_previous_data(tables):
    load(URL, tables)
    before = counts()
    broken = copy.deepcopy(tables)
    broken["sources"].append(dict(broken["sources"][0]))  # a duplicate key, found only part-way through the load
    with pytest.raises(LoadFailed):
        load(URL, broken)
    assert counts() == before


def test_other_tables_untouched(tables):
    with psycopg.connect(URL) as conn:
        conn.execute("drop table if exists unrelated")
        conn.execute("create table unrelated (x integer)")
        conn.execute("insert into unrelated values (1)")
    load(URL, tables)
    assert query("select x from unrelated") == [(1,)]
    with psycopg.connect(URL) as conn:
        conn.execute("drop table unrelated")


def test_awkward_text_loads(tables):
    awkward = "it's a \"quote\"; drop table sources; -- é\n\\x"
    tables["connectivity_claims"][0]["paraphrase"] = awkward
    load(URL, tables)
    assert query("select paraphrase from connectivity_claims where id = %s", tables["connectivity_claims"][0]["id"]) == [(awkward,)]
    assert counts()["sources"] == len(tables["sources"])


def test_read_policies_when_anon_exists(tables):
    with psycopg.connect(URL) as conn:
        for role in ("anon", "authenticated"):
            if not conn.execute("select 1 from pg_roles where rolname = %s", (role,)).fetchall():
                conn.execute(f"create role {role} nologin")
    load(URL, tables)
    policies = {row[0] for row in query("select tablename from pg_policies where cmd = 'SELECT' and 'anon' = any(roles)")}
    assert policies == set(TABLES)
    assert query("select has_table_privilege('anon', 'connectivity_claims', 'INSERT')") == [(False,)]
    assert query("select has_table_privilege('anon', 'connectivity_claims', 'SELECT')") == [(True,)]
    assert all(query("select relrowsecurity from pg_class where relname = %s", name) == [(True,)] for name in TABLES)


def test_failure_message_hides_password():
    with pytest.raises(LoadFailed) as error:
        load("postgresql://axonarium:hunter2-secret@127.0.0.1:1/nowhere?connect_timeout=2", {name: [] for name in TABLES})
    assert "hunter2-secret" not in str(error.value)


def test_asks_rest_api_to_reload_schema(tables):
    # Supabase's REST API caches table definitions; without this, rebuilt tables 404 for a while.
    if "PGlite" in query("select version()")[0][0]:
        pytest.skip("PGlite runs every connection in one session, so it can't deliver NOTIFY between them")
    with psycopg.connect(URL, autocommit=True) as listener:
        listener.execute("listen pgrst")
        load(URL, tables)
        payloads = [n.payload for n in listener.notifies(timeout=5, stop_after=1)]
    assert payloads == ["reload schema"]

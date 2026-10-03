"""Loading Postgres: run against AXONARIUM_TEST_DATABASE_URL (a Postgres service in CI); skipped without it.

The schema comes from supabase/migrations, applied by the Supabase CLI before these tests run
(`npx supabase db push --db-url "$AXONARIUM_TEST_DATABASE_URL"`). The build only fills the tables.
"""

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


def execute(*statements: str) -> None:
    with psycopg.connect(URL, autocommit=True) as conn:
        for statement in statements:
            conn.execute(statement)


def counts() -> dict[str, int]:
    return {name: query(f"select count(*) from {name}")[0][0] for name in TABLES}


@pytest.fixture
def tables(valid_tree):
    records, findings = load_tree(valid_tree)
    assert findings == []
    return rows(records)


def test_load_fills_the_tables(tables):
    load(URL, tables)
    assert counts() == {name: len(table) for name, table in tables.items()}
    subject, measurements, curation = query(
        "select subject_id, measurements, curation from connectivity_claims where id = %s", "clm-pq22bk4dtz")[0]
    assert subject == "MBA:295" and measurements[0]["value"] == 0.12 and curation["by"] == "agent"
    basis = query("select basis from homology_claims order by id limit 1")[0][0]
    assert isinstance(basis, list) and basis


def test_load_never_changes_the_schema(tables):
    identities = "select relname, oid from pg_class where relname = any(%s) order by relname"
    before = query(identities, list(TABLES))
    load(URL, tables)
    assert query(identities, list(TABLES)) == before


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
    execute("drop table if exists unrelated", "create table unrelated (x integer)", "insert into unrelated values (1)")
    try:
        load(URL, tables)
        assert query("select x from unrelated") == [(1,)]
    finally:
        execute("drop table unrelated")


def test_view_survives_load(tables):
    execute("create or replace view strong_edges as select id from edges where strength = 'strong'")
    try:
        load(URL, tables)
        assert query("select count(*) from pg_views where viewname = 'strong_edges'") == [(1,)]
    finally:
        execute("drop view strong_edges")


def test_outside_foreign_key_fails_safely(tables):
    load(URL, tables)
    before = counts()
    execute("create table curated_notes (claim text references connectivity_claims (id))")
    try:
        with pytest.raises(LoadFailed):
            load(URL, tables)
        assert counts() == before
        assert query("select count(*) from pg_constraint where conrelid = 'curated_notes'::regclass and contype = 'f'") == [(1,)]
    finally:
        execute("drop table curated_notes")


def test_missing_migration_fails_clearly(tables):
    execute("alter table edges rename column signs to signs_renamed")
    try:
        with pytest.raises(LoadFailed, match="alembic upgrade head"):
            load(URL, tables)
    finally:
        execute("alter table edges rename column signs_renamed to signs")


def test_awkward_text_loads(tables):
    awkward = "it's a \"quote\"; drop table sources; -- é\n\\x"
    tables["connectivity_claims"][0]["paraphrase"] = awkward
    load(URL, tables)
    assert query("select paraphrase from connectivity_claims where id = %s", tables["connectivity_claims"][0]["id"]) == [(awkward,)]
    assert counts()["sources"] == len(tables["sources"])


def test_migration_gives_read_only_access(tables):
    policies = {row[0] for row in query("select tablename from pg_policies where cmd = 'SELECT' and 'anon' = any(roles)")}
    assert policies == set(TABLES)
    for privilege, expected in (("SELECT", True), ("INSERT", False), ("UPDATE", False), ("DELETE", False),
                                ("TRUNCATE", False), ("REFERENCES", False), ("TRIGGER", False)):
        assert query("select has_table_privilege('anon', 'connectivity_claims', %s)", privilege) == [(expected,)], privilege
    assert all(query("select relrowsecurity from pg_class where relname = %s", name) == [(True,)] for name in TABLES)


def test_migrations_match_tables(monkeypatch):
    # Alembic compares build/tables.py with the migrated database; any difference means a missing migration.
    from alembic import command
    from alembic.config import Config

    monkeypatch.setenv("AXONARIUM_DATABASE_URL", URL)
    command.check(Config("alembic.ini"))

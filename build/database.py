"""Loading the serving tables into Postgres (Supabase in production) in one transaction."""

from urllib.parse import unquote, urlsplit

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from build.tables import TABLES

READERS = ("anon", "authenticated")  # Supabase's roles for the public REST API


class LoadFailed(Exception):
    """The database load failed and was rolled back. The message never contains the database password."""


def _redact(message: str, url: str) -> str:
    password = urlsplit(url).password
    for secret in {password, unquote(password)} if password else ():
        message = message.replace(secret, "***")
    return message


def _value(value, sql_type: str):
    return Jsonb(value) if value is not None and sql_type.startswith("jsonb") else value


def load(url: str, rows: dict[str, list[dict]]) -> None:
    """Replace the project's tables with these rows: drop, create, insert and grant read access, all or nothing."""
    try:
        # No server-side prepared statements, so Supabase's connection poolers work too.
        with psycopg.connect(url, prepare_threshold=None) as conn, conn.cursor() as cur:
            for name in reversed(TABLES):  # Only the project's own tables; anything else in the database is left alone.
                cur.execute(sql.SQL("drop table if exists {} cascade").format(sql.Identifier(name)))
            for name, columns in TABLES.items():
                definition = sql.SQL(", ").join(sql.SQL("{} {}").format(sql.Identifier(c), sql.SQL(t)) for c, t in columns)
                cur.execute(sql.SQL("create table {} ({})").format(sql.Identifier(name), definition))
                if rows[name]:
                    insert = sql.SQL("insert into {} ({}) values ({})").format(
                        sql.Identifier(name), sql.SQL(", ").join(sql.Identifier(c) for c, _ in columns),
                        sql.SQL(", ").join(sql.Placeholder() for _ in columns))
                    cur.executemany(insert, [[_value(row[c], t) for c, t in columns] for row in rows[name]])
            readers = [r for (r,) in cur.execute("select rolname from pg_roles where rolname = any(%s)", (list(READERS),))]
            if readers:
                to = sql.SQL(", ").join(sql.Identifier(r) for r in sorted(readers))
                for name in TABLES:
                    table = sql.Identifier(name)
                    cur.execute(sql.SQL("alter table {} enable row level security").format(table))
                    cur.execute(sql.SQL("create policy public_read on {} for select to {} using (true)").format(table, to))
                    cur.execute(sql.SQL("revoke insert, update, delete, truncate on {} from {}").format(table, to))
                    cur.execute(sql.SQL("grant select on {} to {}").format(table, to))
            cur.execute("notify pgrst, 'reload schema'")  # Supabase's REST API caches table definitions; refresh it on commit.
    except psycopg.Error as error:
        raise LoadFailed(_redact(f"database load failed and was rolled back: {type(error).__name__}: {error}", url)) from None

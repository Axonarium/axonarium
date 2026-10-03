"""Filling the serving tables in Postgres (Supabase in production) in one transaction, with SQLAlchemy.

The tables come from the Alembic migrations in build/migrations (`alembic upgrade head`); this module never
creates, alters or drops anything.
"""

import re
from urllib.parse import unquote, urlsplit

from psycopg import errors
from psycopg.conninfo import conninfo_to_dict
from sqlalchemy import create_engine, insert, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from build.tables import TABLES


class LoadFailed(Exception):
    """The load failed and was rolled back. The message never contains the database password."""


def engine(url: str) -> Engine:
    """An engine for a postgresql:// URL, through psycopg 3. Error messages never include row values."""
    # No server-side prepared statements, so Supabase's connection poolers work too.
    return create_engine(make_url(url).set(drivername="postgresql+psycopg"), poolclass=NullPool, hide_parameters=True,
                         connect_args={"prepare_threshold": None, "connect_timeout": 30})


def _secrets(url: str) -> set[str]:
    """Everything in a database URL that could be or contain the password, however it is written."""
    found = {url}
    userinfo = url.split("://", 1)[-1].rpartition("@")[0]  # libpq and Python split an unencoded @ differently
    if ":" in userinfo:
        password = userinfo.split(":", 1)[1]
        found |= {password, unquote(password), *re.split(r"[@:/]", password)}
    for parse in (lambda: urlsplit(url).password, lambda: conninfo_to_dict(url).get("password"),
                  lambda: make_url(url).password):
        try:
            found.add(parse())
        except Exception:  # Any parser may reject a malformed URL; the others still apply.
            pass
    return {secret for secret in found if secret and len(secret) >= 3}


def _redact(message: str, url: str) -> str:
    for secret in sorted(_secrets(url), key=len, reverse=True):
        message = message.replace(secret, "***")
    return message


def load(url: str, rows: dict[str, list[dict]]) -> None:
    """Replace every row of the serving tables with these rows, all or nothing."""
    try:
        with engine(url).begin() as conn:
            conn.execute(text("set local lock_timeout = '10s'"))  # Give up rather than queue the public API behind a stuck reader.
            # No cascade: if anything outside the build refers to these rows, the load fails instead of touching it.
            quote = conn.dialect.identifier_preparer.quote
            conn.execute(text("truncate " + ", ".join(quote(name) for name in TABLES)))
            for name, table in TABLES.items():
                if rows[name]:
                    conn.execute(insert(table), rows[name])
    except SQLAlchemyError as error:
        cause = getattr(error, "orig", None)
        if isinstance(cause, (errors.UndefinedTable, errors.UndefinedColumn)):
            raise LoadFailed(_redact(f"the database schema is behind build/tables.py ({cause}); apply the migrations "
                                     "with `alembic upgrade head`, then build again", url)) from None
        detail = cause if cause is not None else error
        raise LoadFailed(_redact(f"database load failed and was rolled back: {type(detail).__name__}: {detail}", url)) from None
    except ValueError as error:
        raise LoadFailed(_redact(f"database load failed: {type(error).__name__}: {error}", url)) from None

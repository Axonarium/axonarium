"""Alembic environment: migrates the database in AXONARIUM_DATABASE_URL to the tables in build/tables.py."""

import os
from logging.config import fileConfig

from alembic import context

from build.database import engine
from build.tables import metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def database_url() -> str:
    url = os.environ.get("AXONARIUM_DATABASE_URL")
    if not url:
        raise SystemExit("set AXONARIUM_DATABASE_URL to the database to migrate")
    return url


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    """Only the project's own tables: anything else in the database (Supabase's, or a maintainer's) is left alone."""
    return type_ != "table" or name in metadata.tables


def configure(**kwargs) -> None:
    context.configure(target_metadata=metadata, include_object=include_object, compare_type=True, **kwargs)


if context.is_offline_mode():
    configure(url=database_url(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine(database_url()).connect() as connection:
        configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()

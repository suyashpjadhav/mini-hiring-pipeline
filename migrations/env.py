from logging.config import fileConfig

from alembic import context

from app.core.config import get_settings
from app.core.db import create_engine_for

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL = config.get_main_option("sqlalchemy.url") if set, otherwise get_settings().database_url
url = config.get_main_option("sqlalchemy.url") or get_settings().database_url
config.set_main_option("sqlalchemy.url", url)

target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    target_url = config.get_main_option("sqlalchemy.url") or get_settings().database_url
    context.configure(
        url=target_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    target_url = config.get_main_option("sqlalchemy.url") or get_settings().database_url
    connectable = create_engine_for(target_url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""Global pytest fixtures and isolation guards (SYSTEM_DESIGN §17)."""

import os
from collections.abc import Generator

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True, scope="session")
def guard_test_database_isolation(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[None, None, None]:
    """Autouse session fixture setting DATABASE_URL to a temp file and clearing settings cache.

    Guards against any test touching var/app.db directly.
    """
    tmp_dir = tmp_path_factory.mktemp("global_isolation")
    db_file = tmp_dir / "isolation_guard.db"

    old_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    get_settings.cache_clear()

    yield

    if old_db_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = old_db_url
    get_settings.cache_clear()

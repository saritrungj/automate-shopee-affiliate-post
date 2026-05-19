import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./generated/test.db")
os.environ.setdefault("OPENCLAW_BASE_URL", "http://127.0.0.1:1")
os.environ.setdefault("LLM_FALLBACK_MODE", "mock")


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    import shopee_affiliate.db as db_module
    from shopee_affiliate.main import app

    db_module.create_db()
    with TestClient(app) as test_client:
        yield test_client

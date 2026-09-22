from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps/api/src"))
os.environ["PESTKG_DATA_DIR"] = str(ROOT / "data/releases")
os.environ.pop("PESTKG_NEO4J_URI", None)
os.environ.pop("PESTKG_NEO4J_PASSWORD", None)

from pestkg_api.config import get_settings  # noqa: E402
get_settings.cache_clear()
from pestkg_api.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client

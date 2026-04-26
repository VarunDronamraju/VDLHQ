import asyncio
import os
import sys

import jwt
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.api.dependencies import JWT_ALGORITHM, JWT_SECRET


def create_test_token(user_id: str, role: str, client_id: str = None):
    from datetime import datetime, timedelta, timezone
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    if client_id:
        payload["client_id"] = str(client_id)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_auth_headers(role: str, client_id: str = None):
    token = create_test_token("test_user", role, client_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c

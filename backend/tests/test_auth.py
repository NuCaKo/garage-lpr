from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from garage_lpr.config.settings import BootstrapSettings
from garage_lpr.database.models import User, UserSession

ADMIN_PAYLOAD = {
    "username": "garage-admin",
    "password": "correct horse battery staple 42",
    "password_confirmation": "correct horse battery staple 42",
}


def _app(client: TestClient) -> FastAPI:
    return client.app  # type: ignore[return-value]


def _setup(client: TestClient) -> None:
    response = client.post("/api/v1/auth/setup", json=ADMIN_PAYLOAD)
    assert response.status_code == 201


def test_first_run_requires_setup_and_protects_operational_api(
    unauthenticated_client: TestClient,
) -> None:
    assert unauthenticated_client.get("/api/v1/auth/setup-status").json() == {
        "setup_required": True,
        "csrf_cookie_name": "garage_lpr_csrf",
    }
    response = unauthenticated_client.get("/api/v1/health")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Cookie"


def test_setup_hashes_password_and_session_tokens_at_rest(
    unauthenticated_client: TestClient,
    test_settings: BootstrapSettings,
) -> None:
    response = unauthenticated_client.post("/api/v1/auth/setup", json=ADMIN_PAYLOAD)
    raw_session = unauthenticated_client.cookies.get(test_settings.session_cookie_name)
    raw_csrf = unauthenticated_client.cookies.get(test_settings.csrf_cookie_name)
    session = _app(unauthenticated_client).state.session_factory()
    try:
        user = session.scalar(select(User))
        auth_session = session.scalar(select(UserSession))
    finally:
        session.close()

    assert response.status_code == 201
    assert response.json()["role"] == "ADMIN"
    assert raw_session is not None and raw_csrf is not None
    assert user is not None and user.password_hash.startswith("$argon2id$")
    assert ADMIN_PAYLOAD["password"] not in user.password_hash
    assert auth_session is not None
    assert auth_session.token_hash == sha256(raw_session.encode()).hexdigest()
    assert auth_session.csrf_token_hash == sha256(raw_csrf.encode()).hexdigest()
    assert raw_session not in auth_session.token_hash
    assert "HttpOnly" in response.headers.get_list("set-cookie")[0]


def test_setup_is_one_time_and_password_policy_is_enforced(
    unauthenticated_client: TestClient,
) -> None:
    weak = {
        "username": "admin",
        "password": "short-value",
        "password_confirmation": "short-value",
    }
    assert unauthenticated_client.post("/api/v1/auth/setup", json=weak).status_code == 422

    _setup(unauthenticated_client)

    assert unauthenticated_client.post("/api/v1/auth/setup", json=ADMIN_PAYLOAD).status_code == 409
    assert unauthenticated_client.get("/api/v1/auth/setup-status").json() == {
        "setup_required": False,
        "csrf_cookie_name": "garage_lpr_csrf",
    }


def test_csrf_is_required_for_state_changes_but_not_reads(client: TestClient) -> None:
    assert client.get("/api/v1/health").status_code == 200
    csrf = client.headers.pop("X-CSRF-Token")
    try:
        response = client.put("/api/v1/system-settings", json={})
    finally:
        client.headers["X-CSRF-Token"] = csrf

    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF validation failed"


def test_logout_revokes_server_session(client: TestClient) -> None:
    assert client.post("/api/v1/auth/logout").status_code == 204

    assert client.get("/api/v1/auth/me").status_code == 401
    session = _app(client).state.session_factory()
    try:
        assert session.scalar(select(UserSession)) is None
    finally:
        session.close()


def test_login_uses_generic_error_and_bounded_rate_limit(
    unauthenticated_client: TestClient,
) -> None:
    _setup(unauthenticated_client)
    unauthenticated_client.cookies.clear()
    payload = {"username": ADMIN_PAYLOAD["username"], "password": "wrong password value"}

    responses = [unauthenticated_client.post("/api/v1/auth/login", json=payload) for _ in range(5)]

    assert [response.status_code for response in responses] == [401, 401, 401, 401, 429]
    assert all(
        response.json()["detail"] == "Invalid username or password" for response in responses[:4]
    )
    assert int(responses[-1].headers["retry-after"]) >= 1


def test_expired_session_fails_closed(client: TestClient) -> None:
    session = _app(client).state.session_factory()
    try:
        auth_session = session.scalar(select(UserSession))
        assert auth_session is not None
        auth_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
    finally:
        session.close()

    assert client.get("/api/v1/auth/me").status_code == 401


def test_event_websocket_rejects_missing_session(
    unauthenticated_client: TestClient,
) -> None:
    with (
        pytest.raises(WebSocketDisconnect) as error,
        unauthenticated_client.websocket_connect("/api/v1/events/live"),
    ):
        pass

    assert error.value.code == 4401

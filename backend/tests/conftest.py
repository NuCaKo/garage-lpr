from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from garage_lpr.config.settings import BootstrapSettings
from garage_lpr.main import create_app


@pytest.fixture
def test_settings(tmp_path: Path) -> BootstrapSettings:
    return BootstrapSettings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        log_directory=tmp_path / "logs",
        snapshot_directory=tmp_path / "snapshots",
        secret_key_path=tmp_path / "camera-secrets.key",
        cors_origins=[],
        auto_migrate=True,
    )


@pytest.fixture
def client(test_settings: BootstrapSettings) -> Generator[TestClient, None, None]:
    with TestClient(create_app(test_settings)) as test_client:
        response = test_client.post(
            "/api/v1/auth/setup",
            json={
                "username": "test-admin",
                "password": "safe-test-password-123",
                "password_confirmation": "safe-test-password-123",
            },
        )
        assert response.status_code == 201
        csrf_token = test_client.cookies.get(test_settings.csrf_cookie_name)
        assert csrf_token is not None
        test_client.headers.update({"X-CSRF-Token": csrf_token})
        yield test_client


@pytest.fixture
def unauthenticated_client(
    test_settings: BootstrapSettings,
) -> Generator[TestClient, None, None]:
    with TestClient(create_app(test_settings)) as test_client:
        yield test_client

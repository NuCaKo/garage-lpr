import sys
from pathlib import Path

from fastapi.testclient import TestClient

from garage_lpr.config.settings import BootstrapSettings, repository_root, runtime_root
from garage_lpr.inference.factory import _model_path
from garage_lpr.main import create_app
from garage_lpr.service.windows import service_class


def _settings(tmp_path: Path, **overrides: object) -> BootstrapSettings:
    values: dict[str, object] = {
        "environment": "test",
        "database_url": f"sqlite:///{tmp_path / 'deployment.db'}",
        "log_directory": tmp_path / "logs",
        "snapshot_directory": tmp_path / "snapshots",
        "secret_key_path": tmp_path / "camera-secrets.key",
        "cors_origins": [],
    }
    values.update(overrides)
    return BootstrapSettings(**values)


def test_auth_responses_are_not_cached_and_have_security_headers(
    unauthenticated_client: TestClient,
) -> None:
    response = unauthenticated_client.get("/api/v1/auth/setup-status")

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_production_serves_built_frontend_and_disables_api_docs(tmp_path: Path) -> None:
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text("<main>Garage LPR production UI</main>", encoding="utf-8")
    settings = _settings(
        tmp_path,
        environment="production",
        frontend_dist_directory=frontend,
    )

    with TestClient(create_app(settings)) as client:
        root = client.get("/")
        docs = client.get("/docs")

    assert root.status_code == 200
    assert "Garage LPR production UI" in root.text
    assert "default-src 'self'" in root.headers["content-security-policy"]
    assert docs.status_code == 404


def test_cors_preflight_allows_only_configured_origin(tmp_path: Path) -> None:
    origin = "http://127.0.0.1:5173"
    settings = _settings(tmp_path, cors_origins=[origin])

    with TestClient(create_app(settings)) as client:
        allowed = client.options(
            "/api/v1/system-settings",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "X-CSRF-Token",
            },
        )
        denied = client.options(
            "/api/v1/system-settings",
            headers={
                "Origin": "http://untrusted.invalid",
                "Access-Control-Request-Method": "PUT",
            },
        )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == origin
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


def test_windows_service_entrypoint_is_safe_to_import() -> None:
    assert service_class().__name__ == "GarageLPRWindowsService"


def test_relative_runtime_paths_do_not_depend_on_process_working_directory() -> None:
    settings = BootstrapSettings(
        database_url="sqlite:///./runtime/data/custom.db",
        log_directory=Path("runtime/custom-logs"),
        secret_key_path=Path("runtime/data/custom.key"),
    )

    assert settings.database_url == (
        f"sqlite:///{(repository_root() / 'runtime/data/custom.db').resolve().as_posix()}"
    )
    assert settings.log_directory == (repository_root() / "runtime/custom-logs").resolve()
    assert settings.secret_key_path == (repository_root() / "runtime/data/custom.key").resolve()


def test_runtime_root_honors_explicit_override(monkeypatch, tmp_path: Path) -> None:
    configured_root = tmp_path / "field-data"
    monkeypatch.setenv("GARAGE_LPR_RUNTIME_ROOT", str(configured_root))

    assert runtime_root() == configured_root.resolve()


def test_bundled_resource_root_uses_pyinstaller_meipass(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert repository_root() == tmp_path.resolve()


def test_model_lookup_prefers_writable_runtime_payload(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GARAGE_LPR_RUNTIME_ROOT", str(tmp_path))
    model = tmp_path / "models" / "license_plate_detector.onnx"
    model.parent.mkdir()
    model.touch()

    assert _model_path("models/license_plate_detector.onnx") == model

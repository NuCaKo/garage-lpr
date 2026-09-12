import ast
from pathlib import Path

INSTALLER_ROOT = Path(__file__).resolve().parents[1]


def test_packaging_python_files_parse() -> None:
    paths = [
        INSTALLER_ROOT / "entrypoints" / "service.py",
        INSTALLER_ROOT / "entrypoints" / "soak.py",
        INSTALLER_ROOT / "garage-lpr-service.spec",
        INSTALLER_ROOT / "garage-lpr-soak.spec",
    ]

    for path in paths:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_installer_keeps_mutable_data_out_of_program_files() -> None:
    script = (INSTALLER_ROOT / "GarageLPR.iss").read_text(encoding="utf-8")

    assert "{autopf}\\Garage LPR" in script
    assert "{commonappdata}\\GarageLPR\\runtime\\data" in script
    assert "{commonappdata}\\GarageLPR\\models" in script
    assert "uninsneveruninstall" in script
    assert "--startup auto install" in script
    assert "failure {#ServiceName}" in script
    assert 'DestName: "SoakTest.ps1"' in script


def test_installer_defaults_to_local_fail_safe_configuration() -> None:
    environment = (INSTALLER_ROOT / ".env.production").read_text(encoding="utf-8")

    assert "GARAGE_LPR_ENVIRONMENT=production" in environment
    assert "GARAGE_LPR_HOST=127.0.0.1" in environment
    assert "GARAGE_LPR_PORT=8080" in environment
    assert "GARAGE_LPR_SECURE_COOKIES=false" in environment


def test_installed_soak_test_resolves_service_pid_and_program_data_report() -> None:
    script = (INSTALLER_ROOT / "soak-test.ps1").read_text(encoding="utf-8")

    assert "Get-CimInstance Win32_Service" in script
    assert 'Name=\'GarageLPR\'' in script
    assert "$Service.ProcessId" in script
    assert "$env:ProgramData" in script

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


installer_root = Path(SPECPATH).resolve()
project_root = installer_root.parent
backend_source = project_root / "backend" / "src"
frontend_dist = installer_root / "build" / "frontend-dist"
migrations = backend_source / "garage_lpr" / "database" / "migrations"

if not frontend_dist.joinpath("index.html").is_file():
    raise SystemExit("Frontend build missing. Run installer/build-installer.ps1.")

analysis = Analysis(
    [str(installer_root / "entrypoints" / "service.py")],
    pathex=[str(backend_source)],
    binaries=[],
    datas=[
        (str(frontend_dist), "frontend/dist"),
        (str(migrations), "garage_lpr/database/migrations"),
        *collect_data_files("tzdata"),
    ],
    hiddenimports=[
        "garage_lpr.main",
        "servicemanager",
        "win32event",
        "win32service",
        "win32serviceutil",
        "win32timezone",
        *collect_submodules("uvicorn"),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "mypy", "ruff"],
    noarchive=False,
    optimize=1,
)
python_archive = PYZ(analysis.pure)
executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="GarageLPRService",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
bundle = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GarageLPRService",
)

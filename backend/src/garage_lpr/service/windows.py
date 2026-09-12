import sys
from typing import Any

import uvicorn

from garage_lpr.config.settings import BootstrapSettings

if sys.platform == "win32":
    import servicemanager  # type: ignore[import-not-found]
    import win32event  # type: ignore[import-not-found]
    import win32service  # type: ignore[import-not-found]
    import win32serviceutil  # type: ignore[import-not-found]

    class GarageLPRWindowsService(win32serviceutil.ServiceFramework):  # type: ignore[misc]
        _svc_name_ = "GarageLPR"
        _svc_display_name_ = "Garage LPR Edge Access Control"
        _svc_description_ = "Local license plate recognition and garage access control service"

        def __init__(self, args: list[str]) -> None:
            super().__init__(args)
            self._stop_event = win32event.CreateEvent(None, 0, 0, None)
            self._server: uvicorn.Server | None = None

        def SvcStop(self) -> None:  # noqa: N802
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            if self._server is not None:
                self._server.should_exit = True
            win32event.SetEvent(self._stop_event)

        def SvcDoRun(self) -> None:  # noqa: N802
            settings = BootstrapSettings(environment="production")
            self._server = uvicorn.Server(
                uvicorn.Config(
                    "garage_lpr.main:create_app",
                    factory=True,
                    host=settings.host,
                    port=settings.port,
                    log_config=None,
                    access_log=False,
                )
            )
            servicemanager.LogInfoMsg("Garage LPR service started")
            try:
                self._server.run()
            finally:
                servicemanager.LogInfoMsg("Garage LPR service stopped")

else:

    class GarageLPRWindowsService:
        pass


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("garage-lpr-service is available only on Windows")
    win32serviceutil.HandleCommandLine(GarageLPRWindowsService)  # type: ignore[name-defined]


def service_class() -> type[Any]:
    """Expose the service type for a platform-neutral import smoke test."""
    return GarageLPRWindowsService

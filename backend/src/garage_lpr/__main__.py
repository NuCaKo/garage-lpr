import uvicorn

from garage_lpr.config.settings import BootstrapSettings


def main() -> None:
    settings = BootstrapSettings()
    uvicorn.run(
        "garage_lpr.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_config=None,
    )


if __name__ == "__main__":
    main()

from pathlib import Path

from alembic import command
from alembic.config import Config


def upgrade_database(database_url: str) -> None:
    migration_root = Path(__file__).resolve().parent / "migrations"
    config = Config(attributes={"configure_logger": False})
    config.set_main_option("script_location", str(migration_root))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")

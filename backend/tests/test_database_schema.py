from sqlalchemy import inspect, text

from garage_lpr.config.settings import BootstrapSettings
from garage_lpr.database.lifecycle import upgrade_database
from garage_lpr.database.session import create_database_engine


def test_initial_migration_creates_required_tables(test_settings: BootstrapSettings) -> None:
    upgrade_database(test_settings.database_url)
    engine = create_database_engine(test_settings.database_url)
    try:
        tables = set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
    finally:
        engine.dispose()

    assert {
        "users",
        "user_sessions",
        "cameras",
        "vehicles",
        "access_rules",
        "gate_controllers",
        "recognition_events",
        "access_events",
        "system_settings",
    }.issubset(tables)
    assert revision == "91c4b8e2f5a7"

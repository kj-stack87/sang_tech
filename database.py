import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def _database_path() -> str:
    if Path("/data").is_dir():
        return "/data/santech.db"
    return str(Path(__file__).resolve().with_name("santech.db"))


SQLALCHEMY_DATABASE_URL = f"sqlite:///{_database_path()}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def ensure_app_schema(engine):
    columns = {
        "santech_transactions": {
            "user_id": "INTEGER",
        },
        "cream_transactions": {
            "user_id": "INTEGER",
        },
        "mileage_carry": {
            "user_id": "INTEGER",
        },
    }
    with engine.begin() as connection:
        for table, required_columns in columns.items():
            existing_tables = connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
                (table,),
            ).fetchall()
            if not existing_tables:
                continue
            existing_columns = {
                row[1]
                for row in connection.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            }
            for column, column_type in required_columns.items():
                if column not in existing_columns:
                    connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

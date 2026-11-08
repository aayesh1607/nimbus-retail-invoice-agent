
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Locate the project directory
BASE_DIR = Path(__file__).resolve().parents[2]

# SQLite database location
DATABASE_URL = f"sqlite:///{BASE_DIR / 'data' / 'nimbus.db'}"


# Create the database engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


# Create database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Base class for database models
Base = declarative_base()

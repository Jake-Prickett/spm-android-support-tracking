"""
Database models for Swift Package support data.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from swift_package_analyzer.core.config import config

Base = declarative_base()


class Repository(Base):
    """Model for storing repository information."""

    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    url = Column(String(500), unique=True, nullable=False)
    owner = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)

    # Repository metadata
    description = Column(Text)
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    watchers = Column(Integer, default=0)
    issues_count = Column(Integer, default=0)
    open_issues_count = Column(Integer, default=0)

    # Repository activity
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    pushed_at = Column(DateTime)

    # Repository characteristics
    language = Column(String(50))
    license_name = Column(String(100))
    default_branch = Column(String(50), default="main")

    # Swift Package specific
    has_package_swift = Column(Boolean, default=False)
    package_swift_content = Column(Text)
    swift_tools_version = Column(String(20))

    # Dependency information
    dependencies_count = Column(Integer, default=0)
    dependencies_json = Column(Text)  # JSON string of dependencies

    # Support status
    linux_compatible = Column(
        Boolean, default=True
    )  # From CSV, these are linux compatible
    android_compatible = Column(
        Boolean, default=False
    )  # From CSV, these are NOT android compatible

    # Processing metadata
    last_fetched = Column(DateTime)
    fetch_error = Column(Text)
    processing_status = Column(
        String(20), default="pending"
    )  # pending, processing, completed, error

    def __repr__(self):
        return f"<Repository(name='{self.owner}/{self.name}', stars={self.stars})>"


class ProcessingLog(Base):
    """Model for tracking processing activities."""

    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, nullable=True)
    repository_url = Column(String(500))
    action = Column(
        String(50), nullable=False
    )  # fetch_metadata, parse_package_swift, etc.
    status = Column(String(20), nullable=False)  # success, error, warning
    message = Column(Text)
    duration_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database setup
engine = create_engine(config.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)

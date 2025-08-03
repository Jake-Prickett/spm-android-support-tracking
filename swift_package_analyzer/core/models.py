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

# Package state constants
PACKAGE_STATES = {
    "unknown": "State not yet determined",
    "tracking": "Currently being tracked for migration",
    "in_progress": "Migration work in progress",
    "migrated": "Successfully migrated to Android",
    "archived": "Repository archived/no longer maintained",
    "irrelevant": "Not relevant for Android migration",
    "blocked": "Migration blocked by dependencies or issues",
    "dependency": "Second-tier dependency not in original CSV",
}

DEFAULT_STATE = "tracking"


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

    # Migration state tracking
    current_state = Column(
        String(20), default=DEFAULT_STATE
    )  # tracking, migrated, in_progress, unknown, archived, irrelevant, blocked, dependency

    # Processing metadata
    last_fetched = Column(DateTime)
    fetch_error = Column(Text)
    processing_status = Column(
        String(20), default="pending"
    )  # pending, processing, completed, error

    def __repr__(self):
        return f"<Repository(name='{self.owner}/{self.name}', stars={self.stars})>"

    def transition_state(self, new_state, reason=None, session=None):
        """Transition to a new state and log the change."""
        if new_state not in PACKAGE_STATES:
            raise ValueError(
                f"Invalid state: {new_state}. Valid states: {list(PACKAGE_STATES.keys())}"
            )

        old_state = self.current_state
        self.current_state = new_state

        # Log the transition
        if session:
            transition = StateTransition(
                repository_id=self.id,
                repository_url=self.url,
                from_state=old_state,
                to_state=new_state,
                reason=reason,
            )
            session.add(transition)

        return old_state, new_state


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


class StateTransition(Base):
    """Model for tracking package state transitions."""

    __tablename__ = "state_transitions"

    id = Column(Integer, primary_key=True)
    repository_id = Column(Integer, nullable=False)
    repository_url = Column(String(500))
    from_state = Column(String(20))
    to_state = Column(String(20), nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database setup
engine = create_engine(config.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)

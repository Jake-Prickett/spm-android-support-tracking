"""
Database models for Swift Package support data.
"""

import re
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.config import config

Base = declarative_base()


class PackageState(Enum):
    """Package state enumeration with descriptions."""

    UNKNOWN = "unknown"
    TRACKING = "tracking"
    IN_PROGRESS = "in_progress"
    ANDROID_SUPPORTED = "android_supported"
    ARCHIVED = "archived"
    IRRELEVANT = "irrelevant"
    BLOCKED = "blocked"
    DEPENDENCY = "dependency"

    @classmethod
    def values(cls):
        """Return list of valid state values."""
        return [state.value for state in cls]

    @classmethod
    def descriptions(cls):
        """Return dict mapping values to descriptions."""
        return {
            "unknown": "State not yet determined",
            "tracking": "Currently being tracked for migration",
            "in_progress": "Migration work in progress",
            "android_supported": "Successfully supports Android platform",
            "archived": "Repository archived/no longer maintained",
            "irrelevant": "Not relevant for Android migration",
            "blocked": "Migration blocked by dependencies or issues",
            "dependency": "Second-tier dependency not in original CSV",
        }


# Backward compatibility
PACKAGE_STATES = PackageState.descriptions()
DEFAULT_STATE = PackageState.TRACKING.value


class ValidationError(Exception):
    """Raised when model validation fails."""

    pass


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

    def validate_url(self):
        """Validate repository URL format."""
        if not self.url:
            raise ValidationError("Repository URL is required")

        url_pattern = r"^https://github\.com/[\w\-\.]+/[\w\-\.]+/?$"
        if not re.match(url_pattern, self.url.rstrip("/")):
            raise ValidationError(f"Invalid GitHub repository URL format: {self.url}")

    def validate(self):
        """Validate all repository fields."""
        self.validate_url()

        if not self.owner or not self.owner.strip():
            raise ValidationError("Repository owner is required")

        if not self.name or not self.name.strip():
            raise ValidationError("Repository name is required")

    def transition_state(
        self, new_state, reason=None, changed_by=None, issue_number=None, session=None
    ):
        """Transition to a new state and log the change."""
        if new_state not in PackageState.values():
            raise ValidationError(
                f"Invalid state: {new_state}. Valid states: {PackageState.values()}"
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
                changed_by=changed_by,
                issue_number=issue_number,
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
    changed_by = Column(String(100))  # Who made the change (e.g., GitHub username)
    issue_number = Column(String(20))  # GitHub issue number if applicable
    created_at = Column(DateTime, default=datetime.utcnow)


# Database indexes for performance
Index("idx_repo_owner_name", Repository.owner, Repository.name)
Index("idx_repo_state", Repository.current_state)
Index("idx_repo_stars", Repository.stars)
Index("idx_repo_last_fetched", Repository.last_fetched)
Index("idx_transition_repo_id", StateTransition.repository_id)
Index("idx_transition_date", StateTransition.created_at)

# Database setup
engine = create_engine(config.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)

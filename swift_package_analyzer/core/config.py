"""
Configuration management for Swift Package support data processing.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Configuration settings for the application."""

    # Database settings
    database_url: str = "sqlite:///swift_packages.db"

    # GitHub API settings
    github_token: Optional[str] = None
    github_api_base_url: str = "https://api.github.com"

    # Rate limiting settings
    requests_per_hour: int = 5000  # GitHub API limit
    repositories_per_batch: int = 40  # ~3 requests per repo = 120 requests per batch
    batch_delay_minutes: int = 2  # 60 minutes / 29 batches = ~2.1 minutes (70% utilization)

    # Data processing settings
    csv_file_path: str = "data/linux-compatible-android-incompatible.csv"

    # Logging settings
    log_level: str = "INFO"
    log_file: str = "swift_package_processor.log"

    def __post_init__(self):
        """Load environment variables and validate configuration."""
        self.github_token = os.getenv("GITHUB_TOKEN", self.github_token)
        self.database_url = os.getenv("DATABASE_URL", self.database_url)

        # Create necessary directories
        Path("logs").mkdir(exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        Path("exports").mkdir(exist_ok=True)

        if not self.github_token:
            print("Warning: GITHUB_TOKEN not found in environment variables.")
            print("API requests will be limited to 60 per hour without authentication.")


# Global configuration instance
config = Config()

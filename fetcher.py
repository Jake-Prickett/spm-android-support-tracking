"""
Data fetcher for GitHub repository information with rate limiting.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from github import Github, RateLimitExceededException

from config import config
from models import ProcessingLog, Repository, SessionLocal

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(f"logs/{config.log_file}"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class GitHubFetcher:
    """Handles fetching repository data from GitHub API with rate limiting."""

    def __init__(self):
        self.github = Github(config.github_token) if config.github_token else Github()
        self.session = requests.Session()
        self.last_request_time = datetime.now()
        self.request_count = 0

    def _wait_for_rate_limit(self):
        """Implement rate limiting to avoid hitting GitHub API limits."""
        current_time = datetime.now()
        time_since_last = (current_time - self.last_request_time).total_seconds()

        # Ensure we don't exceed the rate limit
        min_interval = 3600 / config.requests_per_hour  # seconds between requests
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = datetime.now()
        self.request_count += 1

    def parse_github_url(self, url: str) -> Tuple[str, str]:
        """Parse GitHub URL to extract owner and repository name."""
        # Handle different URL formats
        if url.startswith("https://swiftpackageindex.com/"):
            # Extract from Swift Package Index URL format
            path_parts = (
                url.replace("https://swiftpackageindex.com/", "")
                .rstrip(".git")
                .split("/")
            )
            if len(path_parts) >= 2:
                return path_parts[0], path_parts[1]

        # Handle direct GitHub URLs
        parsed = urlparse(url)
        if "github.com" in parsed.netloc:
            path_parts = parsed.path.strip("/").rstrip(".git").split("/")
            if len(path_parts) >= 2:
                return path_parts[0], path_parts[1]

        raise ValueError(f"Unable to parse GitHub URL: {url}")

    def fetch_repository_metadata(self, url: str) -> Optional[Dict]:
        """Fetch repository metadata from GitHub API."""
        try:
            owner, repo_name = self.parse_github_url(url)
            logger.info(f"Fetching metadata for {owner}/{repo_name}")

            self._wait_for_rate_limit()

            # Get repository information
            repo = self.github.get_repo(f"{owner}/{repo_name}")

            # Extract metadata
            metadata = {
                "url": url,
                "owner": owner,
                "name": repo_name,
                "description": repo.description,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "watchers": repo.watchers_count,
                "issues_count": repo.get_issues(state="all").totalCount,
                "open_issues_count": repo.open_issues_count,
                "created_at": repo.created_at,
                "updated_at": repo.updated_at,
                "pushed_at": repo.pushed_at,
                "language": repo.language,
                "license_name": repo.license.name if repo.license else None,
                "default_branch": repo.default_branch,
            }

            # Try to fetch Package.swift content
            package_swift_content = self._fetch_package_swift(repo)
            metadata["has_package_swift"] = package_swift_content is not None
            metadata["package_swift_content"] = package_swift_content

            if package_swift_content:
                metadata["swift_tools_version"] = self._extract_swift_tools_version(
                    package_swift_content
                )
                metadata["dependencies_json"] = json.dumps(
                    self._extract_dependencies(package_swift_content)
                )
                metadata["dependencies_count"] = len(
                    self._extract_dependencies(package_swift_content)
                )

            logger.info(f"Successfully fetched metadata for {owner}/{repo_name}")
            return metadata

        except RateLimitExceededException:
            logger.error("GitHub API rate limit exceeded")
            raise
        except Exception as e:
            logger.error(f"Error fetching metadata for {url}: {str(e)}")
            return None

    def _fetch_package_swift(self, repo) -> Optional[str]:
        """Fetch Package.swift file content."""
        try:
            package_file = repo.get_contents("Package.swift")
            return package_file.decoded_content.decode("utf-8")
        except Exception:
            return None

    def _extract_swift_tools_version(self, package_content: str) -> Optional[str]:
        """Extract Swift tools version from Package.swift content."""
        for line in package_content.split("\n"):
            if "swift-tools-version" in line:
                # Extract version from comment like "// swift-tools-version:5.7"
                parts = line.split(":")
                if len(parts) > 1:
                    return parts[1].strip()
        return None

    def _extract_dependencies(self, package_content: str) -> List[Dict]:
        """Extract dependencies from Package.swift content (basic parsing)."""
        dependencies = []
        # This is a simple regex-based approach - could be improved with proper parsing
        import re

        # Look for .package patterns
        package_patterns = re.findall(r"\.package\([^)]+\)", package_content)

        for pattern in package_patterns:
            dep_info = {}

            # Extract URL
            url_match = re.search(r'url:\s*["\']([^"\']+)["\']', pattern)
            if url_match:
                dep_info["url"] = url_match.group(1)

            # Extract version requirements
            version_match = re.search(r'from:\s*["\']([^"\']+)["\']', pattern)
            if version_match:
                dep_info["version_requirement"] = f"from: {version_match.group(1)}"

            if dep_info:
                dependencies.append(dep_info)

        return dependencies


class DataProcessor:
    """Processes repository data and updates the database."""

    def __init__(self):
        self.fetcher = GitHubFetcher()
        self.db = SessionLocal()

    def load_csv_repositories(self) -> List[str]:
        """Load repository URLs from the CSV file."""
        import pandas as pd

        try:
            df = pd.read_csv(config.csv_file_path, header=None, names=["url"])
            urls = df["url"].str.strip('"').tolist()
            logger.info(f"Loaded {len(urls)} repository URLs from CSV")
            return urls
        except Exception as e:
            logger.error(f"Error loading CSV file: {str(e)}")
            return []

    def process_repository(self, url: str) -> bool:
        """Process a single repository."""
        start_time = datetime.now()

        try:
            # Check if repository already exists
            existing_repo = (
                self.db.query(Repository).filter(Repository.url == url).first()
            )

            # Skip if recently processed (within last 24 hours)
            if existing_repo and existing_repo.last_fetched:
                time_since_fetch = datetime.now() - existing_repo.last_fetched
                if time_since_fetch < timedelta(hours=24):
                    logger.info(f"Skipping {url} - recently processed")
                    return True

            # Fetch metadata
            metadata = self.fetcher.fetch_repository_metadata(url)
            if not metadata:
                self._log_processing_error(url, "Failed to fetch metadata", start_time)
                return False

            # Update or create repository record
            if existing_repo:
                for key, value in metadata.items():
                    setattr(existing_repo, key, value)
                existing_repo.last_fetched = datetime.now()
                existing_repo.processing_status = "completed"
                existing_repo.fetch_error = None
            else:
                repo = Repository(**metadata)
                repo.last_fetched = datetime.now()
                repo.processing_status = "completed"
                repo.linux_compatible = (
                    True  # All repos in our CSV are Linux compatible
                )
                repo.android_compatible = (
                    False  # All repos in our CSV are NOT Android compatible
                )
                self.db.add(repo)

            self.db.commit()

            # Log successful processing
            duration = (datetime.now() - start_time).total_seconds()
            log_entry = ProcessingLog(
                repository_url=url,
                action="fetch_metadata",
                status="success",
                message=f"Successfully processed {metadata.get('owner')}/{metadata.get('name')}",
                duration_seconds=duration,
            )
            self.db.add(log_entry)
            self.db.commit()

            logger.info(f"Successfully processed {url}")
            return True

        except Exception as e:
            self._log_processing_error(url, str(e), start_time)
            return False

    def _log_processing_error(self, url: str, error_message: str, start_time: datetime):
        """Log processing error to database and logs."""
        duration = (datetime.now() - start_time).total_seconds()

        # Update repository record with error
        existing_repo = self.db.query(Repository).filter(Repository.url == url).first()
        if existing_repo:
            existing_repo.processing_status = "error"
            existing_repo.fetch_error = error_message
            existing_repo.last_fetched = datetime.now()

        # Log error
        log_entry = ProcessingLog(
            repository_url=url,
            action="fetch_metadata",
            status="error",
            message=error_message,
            duration_seconds=duration,
        )
        self.db.add(log_entry)
        self.db.commit()

        logger.error(f"Error processing {url}: {error_message}")

    def process_batch(self, urls: List[str]) -> Dict[str, int]:
        """Process a batch of repositories."""
        results = {"success": 0, "error": 0}

        for url in urls:
            if self.process_repository(url):
                results["success"] += 1
            else:
                results["error"] += 1

            # Small delay between repositories
            time.sleep(1)

        return results

    def close(self):
        """Close database connection."""
        self.db.close()

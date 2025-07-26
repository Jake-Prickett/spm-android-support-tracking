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
from github import Github, RateLimitExceededException, GithubException
from tqdm import tqdm

from swift_package_analyzer.core.config import config
from swift_package_analyzer.core.models import ProcessingLog, Repository, SessionLocal

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
        self.success_count = 0
        self.error_count = 0
        
        # Check rate limit on initialization
        self._check_rate_limit_status()
    
    def _check_rate_limit_status(self):
        """Check and log current rate limit status."""
        try:
            rate_limit = self.github.get_rate_limit()
            core_limit = rate_limit.core
            logger.info(f"Rate limit status: {core_limit.remaining}/{core_limit.limit} requests remaining")
            if core_limit.remaining < 100:
                reset_time = core_limit.reset
                logger.warning(f"Low rate limit remaining! Resets at {reset_time}")
        except Exception as e:
            logger.warning(f"Could not check rate limit status: {e}")

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
                .replace(".git", "")
                .split("/")
            )
            if len(path_parts) >= 2:
                return path_parts[0], path_parts[1]

        # Handle direct GitHub URLs
        parsed = urlparse(url)
        if "github.com" in parsed.netloc:
            path_parts = parsed.path.strip("/").replace(".git", "").split("/")
            if len(path_parts) >= 2:
                return path_parts[0], path_parts[1]

        raise ValueError(f"Unable to parse GitHub URL: {url}")

    def fetch_repository_metadata(self, url: str) -> Optional[Dict]:
        """Fetch repository metadata from GitHub API with enhanced error handling."""
        start_time = time.time()
        
        try:
            owner, repo_name = self.parse_github_url(url)
            logger.info(f"Fetching metadata for {owner}/{repo_name}")

            self._wait_for_rate_limit()

            # Get repository information with retry logic
            repo = self._get_repo_with_retry(f"{owner}/{repo_name}")
            if not repo:
                self.error_count += 1
                return None

            # Extract basic metadata with error handling
            metadata = self._extract_basic_metadata(url, owner, repo_name, repo)
            
            # Try to fetch Package.swift content
            package_swift_content = self._fetch_package_swift_safe(repo)
            metadata["has_package_swift"] = package_swift_content is not None
            metadata["package_swift_content"] = package_swift_content

            if package_swift_content:
                try:
                    metadata["swift_tools_version"] = self._extract_swift_tools_version(
                        package_swift_content
                    )
                    dependencies = self._extract_dependencies(package_swift_content)
                    metadata["dependencies_json"] = json.dumps(dependencies)
                    metadata["dependencies_count"] = len(dependencies)
                except Exception as e:
                    logger.warning(f"Error parsing Package.swift for {owner}/{repo_name}: {e}")
                    metadata["dependencies_count"] = 0

            # Add processing metadata
            metadata["fetch_duration"] = time.time() - start_time
            
            self.success_count += 1
            logger.info(f"Successfully fetched metadata for {owner}/{repo_name} in {metadata['fetch_duration']:.2f}s")
            return metadata

        except RateLimitExceededException:
            logger.error("GitHub API rate limit exceeded")
            self._handle_rate_limit_exceeded()
            raise
        except GithubException as e:
            self.error_count += 1
            logger.error(f"GitHub API error for {url}: {e.status} - {e.data.get('message', str(e))}")
            return None
        except Exception as e:
            self.error_count += 1
            logger.error(f"Unexpected error fetching metadata for {url}: {str(e)}")
            return None
    
    def _get_repo_with_retry(self, repo_path: str, max_retries: int = 3):
        """Get repository with retry logic for transient errors."""
        for attempt in range(max_retries):
            try:
                return self.github.get_repo(repo_path)
            except GithubException as e:
                if e.status == 404:
                    logger.warning(f"Repository {repo_path} not found (404)")
                    return None
                elif e.status in [502, 503, 504] and attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Transient error {e.status} for {repo_path}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        return None
    
    def _extract_basic_metadata(self, url: str, owner: str, repo_name: str, repo) -> Dict:
        """Extract basic repository metadata with error handling."""
        metadata = {
            "url": url,
            "owner": owner,
            "name": repo_name,
        }
        
        # Safe extraction of optional fields
        safe_fields = {
            "description": lambda: repo.description,
            "stars": lambda: repo.stargazers_count or 0,
            "forks": lambda: repo.forks_count or 0,
            "watchers": lambda: repo.watchers_count or 0,
            "open_issues_count": lambda: repo.open_issues_count or 0,
            "created_at": lambda: repo.created_at,
            "updated_at": lambda: repo.updated_at,
            "pushed_at": lambda: repo.pushed_at,
            "language": lambda: repo.language,
            "default_branch": lambda: repo.default_branch or "main",
        }
        
        for field, extractor in safe_fields.items():
            try:
                metadata[field] = extractor()
            except Exception as e:
                logger.warning(f"Could not extract {field} for {owner}/{repo_name}: {e}")
                metadata[field] = None
        
        # Handle license separately as it requires additional API call
        try:
            metadata["license_name"] = repo.license.name if repo.license else None
        except Exception:
            metadata["license_name"] = None
        
        # Handle issues count separately as it's expensive
        try:
            metadata["issues_count"] = repo.get_issues(state="all").totalCount
        except Exception:
            metadata["issues_count"] = metadata["open_issues_count"]
        
        return metadata
    
    def _handle_rate_limit_exceeded(self):
        """Handle rate limit exceeded scenario."""
        try:
            rate_limit = self.github.get_rate_limit()
            reset_time = rate_limit.core.reset
            wait_seconds = (reset_time - datetime.now()).total_seconds()
            logger.error(f"Rate limit exceeded. Reset in {wait_seconds:.0f} seconds at {reset_time}")
        except Exception:
            logger.error("Rate limit exceeded. Please wait before making more requests.")

    def _fetch_package_swift_safe(self, repo) -> Optional[str]:
        """Safely fetch Package.swift file content with better error handling."""
        try:
            package_file = repo.get_contents("Package.swift")
            content = package_file.decoded_content.decode("utf-8")
            logger.debug(f"Successfully fetched Package.swift ({len(content)} chars)")
            return content
        except GithubException as e:
            if e.status == 404:
                logger.debug("No Package.swift file found")
            else:
                logger.warning(f"Error fetching Package.swift: {e.status} - {e.data.get('message', str(e))}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error fetching Package.swift: {e}")
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
    """Processes repository data and updates the database with enhanced progress tracking."""

    def __init__(self):
        self.fetcher = GitHubFetcher()
        self.db = SessionLocal()
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        self.start_time = None

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

    def process_repository(self, url: str) -> str:
        """Process a single repository. Returns 'success', 'error', or 'skipped'."""
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
                    logger.debug(f"Skipping {url} - recently processed")
                    return "skipped"

            # Fetch metadata
            metadata = self.fetcher.fetch_repository_metadata(url)
            if not metadata:
                self._log_processing_error(url, "Failed to fetch metadata", start_time)
                return "error"

            # Update or create repository record
            try:
                if existing_repo:
                    for key, value in metadata.items():
                        if hasattr(existing_repo, key):  # Only set existing attributes
                            setattr(existing_repo, key, value)
                    existing_repo.last_fetched = datetime.now()
                    existing_repo.processing_status = "completed"
                    existing_repo.fetch_error = None
                else:
                    # Filter metadata to only include valid Repository fields
                    valid_fields = {key: value for key, value in metadata.items() 
                                  if hasattr(Repository, key)}
                    
                    repo = Repository(**valid_fields)
                    repo.last_fetched = datetime.now()
                    repo.processing_status = "completed"
                    repo.linux_compatible = True  # All repos in our CSV are Linux compatible
                    repo.android_compatible = False  # All repos in our CSV are NOT Android compatible
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

                logger.info(f"Successfully processed {url} in {duration:.1f}s")
                return "success"
                
            except Exception as db_error:
                logger.error(f"Database error for {url}: {db_error}")
                self.db.rollback()
                self._log_processing_error(url, f"Database error: {str(db_error)}", start_time)
                return "error"

        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {e}")
            self._log_processing_error(url, str(e), start_time)
            return "error"

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
        """Process a batch of repositories with progress tracking."""
        if not self.start_time:
            self.start_time = time.time()
        
        results = {"success": 0, "error": 0, "skipped": 0}
        batch_start = time.time()
        
        # Use tqdm for progress bar
        progress_bar = tqdm(urls, desc="Processing repositories", unit="repo")
        
        for url in progress_bar:
            result = self.process_repository(url)
            
            if result == "success":
                results["success"] += 1
                self.success_count += 1
            elif result == "error":
                results["error"] += 1
                self.error_count += 1
            else:  # skipped
                results["skipped"] += 1
            
            self.processed_count += 1
            
            # Update progress bar with current stats
            progress_bar.set_postfix({
                'Success': results["success"],
                'Errors': results["error"],
                'Skipped': results["skipped"]
            })

            # Small delay between repositories
            time.sleep(1)
        
        progress_bar.close()
        
        batch_duration = time.time() - batch_start
        logger.info(f"Batch completed in {batch_duration:.1f}s: {results}")
        
        return results

    def get_processing_stats(self) -> Dict[str, any]:
        """Get current processing statistics."""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": (self.success_count / max(self.processed_count, 1)) * 100,
            "elapsed_time": elapsed_time,
            "repos_per_minute": (self.processed_count / max(elapsed_time / 60, 1)) if elapsed_time > 0 else 0,
            "fetcher_stats": {
                "success_count": self.fetcher.success_count,
                "error_count": self.fetcher.error_count,
                "request_count": self.fetcher.request_count
            }
        }
    
    def close(self):
        """Close database connection and log final stats."""
        if self.processed_count > 0:
            stats = self.get_processing_stats()
            logger.info(f"Final processing stats: {stats}")
        self.db.close()

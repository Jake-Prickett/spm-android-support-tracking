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
from bs4 import BeautifulSoup

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
            logger.info(
                f"Rate limit status: {core_limit.remaining}/{core_limit.limit} requests remaining"
            )
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
                    logger.warning(
                        f"Error parsing Package.swift for {owner}/{repo_name}: {e}"
                    )
                    metadata["dependencies_count"] = 0

            # Check Android support from Swift Package Index
            try:
                android_support = self.check_android_support_spi(owner, repo_name)
                if android_support is not None:
                    metadata["android_compatible"] = android_support
                    logger.info(
                        f"Updated Android support status for {owner}/{repo_name}: {android_support}"
                    )
            except Exception as e:
                logger.warning(
                    f"Error checking Android support for {owner}/{repo_name}: {e}"
                )

            # Add processing metadata
            metadata["fetch_duration"] = time.time() - start_time

            self.success_count += 1
            logger.info(
                f"Successfully fetched metadata for {owner}/{repo_name} in {metadata['fetch_duration']:.2f}s"
            )
            return metadata

        except RateLimitExceededException:
            logger.error("GitHub API rate limit exceeded")
            self._handle_rate_limit_exceeded()
            raise
        except GithubException as e:
            self.error_count += 1
            logger.error(
                f"GitHub API error for {url}: {e.status} - {e.data.get('message', str(e))}"
            )
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
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Transient error {e.status} for {repo_path}, retrying in {wait_time}s"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        return None

    def _extract_basic_metadata(
        self, url: str, owner: str, repo_name: str, repo
    ) -> Dict:
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
                logger.warning(
                    f"Could not extract {field} for {owner}/{repo_name}: {e}"
                )
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
            logger.error(
                f"Rate limit exceeded. Reset in {wait_seconds:.0f} seconds at {reset_time}"
            )
        except Exception:
            logger.error(
                "Rate limit exceeded. Please wait before making more requests."
            )

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
                logger.warning(
                    f"Error fetching Package.swift: {e.status} - {e.data.get('message', str(e))}"
                )
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

    def check_android_support_spi(self, owner: str, repo_name: str) -> Optional[bool]:
        """Check Android support status from Swift Package Index with multiple strategies."""
        # Strategy 1: Try Swift Package Index website
        android_support = self._scrape_spi_website(owner, repo_name)
        if android_support is not None:
            return android_support

        # Strategy 2: Check Package.swift for platform declarations (if we have the content)
        # This will be handled separately in the main processing flow

        # Strategy 3: Heuristic based on package characteristics
        # For now, return None if we can't determine from SPI
        return None

    def _scrape_spi_website(self, owner: str, repo_name: str) -> Optional[bool]:
        """Scrape Swift Package Index website for Android support indicators."""
        spi_url = f"https://swiftpackageindex.com/{owner}/{repo_name}"

        try:
            # Multiple user agents to try
            user_agents = [
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]

            for user_agent in user_agents:
                headers = {
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }

                try:
                    # Add delay to be respectful
                    time.sleep(1)
                    response = self.session.get(spi_url, headers=headers, timeout=15)

                    if response.status_code == 200:
                        return self._parse_spi_page(response.content, owner, repo_name)
                    elif response.status_code == 404:
                        logger.debug(
                            f"Package {owner}/{repo_name} not found on Swift Package Index"
                        )
                        return None
                    elif response.status_code == 403:
                        logger.debug(
                            f"Access denied for {owner}/{repo_name}, trying next user agent"
                        )
                        continue
                    else:
                        logger.warning(
                            f"HTTP {response.status_code} for {owner}/{repo_name}"
                        )
                        continue

                except requests.exceptions.RequestException as e:
                    logger.debug(
                        f"Request failed for {owner}/{repo_name} with user agent {user_agent[:20]}...: {e}"
                    )
                    continue

            # If all user agents failed
            logger.warning(
                f"All attempts failed to fetch SPI page for {owner}/{repo_name}"
            )
            return None

        except Exception as e:
            logger.warning(f"Error fetching SPI page for {owner}/{repo_name}: {e}")
            return None

    def _parse_spi_page(
        self, content: bytes, owner: str, repo_name: str
    ) -> Optional[bool]:
        """Parse Swift Package Index page content for Android support indicators.

        Looks for platform compatibility badges and checks their visual state:
        - Green background indicates supported platform
        - Grey/disabled background indicates unsupported platform
        """
        try:
            soup = BeautifulSoup(content, "html.parser")

            # Strategy 1: Look for platform compatibility badges/buttons with Android text
            # These usually have classes like 'badge', 'platform', 'btn', etc.
            android_elements = soup.find_all(
                ["span", "div", "button", "a"],
                string=lambda text: text and "android" in text.lower(),
            )

            for element in android_elements:
                # Check the element and its parents for styling indicators
                elements_to_check = [element] + list(element.parents)[
                    :3
                ]  # Check element + up to 3 parents

                for elem in elements_to_check:
                    # Get style attribute
                    style = elem.get("style", "").lower()

                    # Get class attributes
                    class_attr = elem.get("class", [])
                    if isinstance(class_attr, str):
                        class_attr = [class_attr]
                    classes = " ".join(class_attr).lower()

                    # Check for green indicators (supported) - Swift Package Index specific
                    green_indicators = [
                        "green",
                        "success",
                        "enabled",
                        "supported",
                        "active",
                        # Swift Package Index enabled Android colors
                        "rgb(14, 191, 76)",
                        "rgb(255, 255, 255)",
                        "#0ebf4c",
                        "#ffffff",
                        # Swift Package Index CSS classes - be specific to avoid matching "incompatible"
                        "result compatible",
                        # Additional common green variations
                        "rgb(34, 197, 94)",
                        "rgb(22, 163, 74)",
                        "#22c55e",
                        "#16a34a",
                        "bg-green",
                        "text-green",
                        "border-green",
                    ]

                    # Check for grey/disabled indicators (not supported) - Swift Package Index specific
                    grey_indicators = [
                        "grey",
                        "gray",
                        "disabled",
                        "inactive",
                        "muted",
                        "unavailable",
                        "incompatible",
                        # Swift Package Index disabled Android colors
                        "rgb(25, 25, 35)",
                        "rgb(154, 154, 154)",
                        "#191923",
                        "#9a9a9a",
                        # Swift Package Index CSS classes
                        "result incompatible",
                        "incompatible",
                        "result unknown",
                        "unknown",
                        # Additional common grey variations
                        "rgb(156, 163, 175)",
                        "rgb(107, 114, 128)",
                        "#9ca3af",
                        "#6b7280",
                        "bg-gray",
                        "text-gray",
                        "border-gray",
                        "opacity-50",
                        "opacity-25",
                    ]

                    # Check style and classes for indicators
                    content_to_check = f"{style} {classes}"

                    if any(
                        indicator in content_to_check for indicator in green_indicators
                    ):
                        logger.info(
                            f"Found Android with green/supported styling for {owner}/{repo_name}"
                        )
                        return True
                    elif any(
                        indicator in content_to_check for indicator in grey_indicators
                    ):
                        logger.info(
                            f"Found Android with grey/disabled styling for {owner}/{repo_name}"
                        )
                        return False

            # Strategy 2: Look for platform grids/lists and check Android element styling
            platform_containers = soup.find_all(
                ["div", "ul", "ol"],
                class_=lambda x: x
                and any(
                    keyword in str(x).lower()
                    for keyword in ["platform", "compatibility", "support", "badge"]
                ),
            )

            for container in platform_containers:
                # Find all elements in container that might contain Android
                child_elements = container.find_all(
                    ["span", "div", "li", "button", "a"]
                )

                for child in child_elements:
                    text = child.get_text().lower()
                    if "android" in text:
                        # Check styling of this specific child
                        style = child.get("style", "").lower()
                        classes = " ".join(child.get("class", [])).lower()
                        content_to_check = f"{style} {classes}"

                        green_indicators = [
                            "green",
                            "success",
                            "enabled",
                            "supported",
                            "active",
                            # Swift Package Index enabled colors
                            "rgb(14, 191, 76)",
                            "rgb(255, 255, 255)",
                            "#0ebf4c",
                            "#ffffff",
                            # Swift Package Index CSS classes - be specific to avoid matching "incompatible"
                            "result compatible",
                            # Additional variations
                            "rgb(34, 197, 94)",
                            "#22c55e",
                            "bg-green",
                        ]
                        grey_indicators = [
                            "grey",
                            "gray",
                            "disabled",
                            "inactive",
                            "muted",
                            "incompatible",
                            # Swift Package Index disabled colors
                            "rgb(25, 25, 35)",
                            "rgb(154, 154, 154)",
                            "#191923",
                            "#9a9a9a",
                            # Swift Package Index CSS classes
                            "result incompatible",
                            "incompatible",
                            "result unknown",
                            "unknown",
                            # Additional variations
                            "rgb(156, 163, 175)",
                            "#9ca3af",
                            "bg-gray",
                            "opacity-50",
                        ]

                        if any(
                            indicator in content_to_check
                            for indicator in green_indicators
                        ):
                            logger.info(
                                f"Found Android with green styling in platform container for {owner}/{repo_name}"
                            )
                            return True
                        elif any(
                            indicator in content_to_check
                            for indicator in grey_indicators
                        ):
                            logger.info(
                                f"Found Android with grey styling in platform container for {owner}/{repo_name}"
                            )
                            return False

            # Strategy 3: Look for images/icons with Android in alt/title and check parent styling
            images = soup.find_all("img")
            for img in images:
                alt_text = img.get("alt", "").lower()
                title = img.get("title", "").lower()
                src = img.get("src", "").lower()

                if any("android" in text for text in [alt_text, title, src]):
                    # Check parent elements for styling
                    for parent in list(img.parents)[:3]:
                        style = parent.get("style", "").lower()
                        classes = " ".join(parent.get("class", [])).lower()
                        content_to_check = f"{style} {classes}"

                        if any(
                            indicator in content_to_check
                            for indicator in ["green", "success", "enabled"]
                        ):
                            logger.info(
                                f"Found Android icon with green parent styling for {owner}/{repo_name}"
                            )
                            return True
                        elif any(
                            indicator in content_to_check
                            for indicator in ["grey", "gray", "disabled"]
                        ):
                            logger.info(
                                f"Found Android icon with grey parent styling for {owner}/{repo_name}"
                            )
                            return False

            # Strategy 4: Fallback - if we found Android mentioned but no clear styling indicators,
            # look for general patterns that might indicate support
            page_text = soup.get_text().lower()
            if "android" in page_text:
                # Look for positive indicators near Android mentions
                if any(
                    phrase in page_text
                    for phrase in [
                        "android support",
                        "supports android",
                        "android compatible",
                    ]
                ):
                    logger.info(
                        f"Found positive Android support text for {owner}/{repo_name}"
                    )
                    return True

            # No clear Android support indicators found
            logger.debug(
                f"No clear Android support indicators found for {owner}/{repo_name}"
            )
            return False  # Default to False (not supported) instead of None

        except Exception as e:
            logger.warning(
                f"Error parsing SPI page content for {owner}/{repo_name}: {e}"
            )
            return None


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
                    valid_fields = {
                        key: value
                        for key, value in metadata.items()
                        if hasattr(Repository, key)
                    }

                    repo = Repository(**valid_fields)
                    repo.last_fetched = datetime.now()
                    repo.processing_status = "completed"
                    repo.linux_compatible = (
                        True  # All repos in our CSV are Linux compatible
                    )
                    # android_compatible will be set from metadata if detected, otherwise defaults to False
                    if "android_compatible" not in valid_fields:
                        repo.android_compatible = False  # Default for repos in our CSV
                    self.db.add(repo)

                # Update current_state based on android_compatible
                repo_obj = existing_repo if existing_repo else repo
                if repo_obj.android_compatible:
                    repo_obj.current_state = "android_supported"
                elif repo_obj.current_state == "android_supported" and not repo_obj.android_compatible:
                    # Reset incorrectly marked repositories
                    repo_obj.current_state = "tracking"

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
                self._log_processing_error(
                    url, f"Database error: {str(db_error)}", start_time
                )
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
            progress_bar.set_postfix(
                {
                    "Success": results["success"],
                    "Errors": results["error"],
                    "Skipped": results["skipped"],
                }
            )

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
            "repos_per_minute": (self.processed_count / max(elapsed_time / 60, 1))
            if elapsed_time > 0
            else 0,
            "fetcher_stats": {
                "success_count": self.fetcher.success_count,
                "error_count": self.fetcher.error_count,
                "request_count": self.fetcher.request_count,
            },
        }

    def get_repositories_for_refresh(
        self, all_urls: List[str], chunk_size: int = 250
    ) -> List[str]:
        """Get the oldest repositories that need refreshing, up to chunk_size."""
        db = SessionLocal()
        try:
            # Get repositories ordered by staleness (never fetched first, then oldest first)
            stale_repos = (
                db.query(Repository)
                .filter(Repository.url.in_(all_urls))
                .order_by(
                    Repository.last_fetched.asc().nullsfirst(),  # Never fetched first
                    Repository.updated_at.asc().nullsfirst(),  # Then oldest updates
                )
                .limit(chunk_size)
                .all()
            )

            stale_urls = [repo.url for repo in stale_repos]

            # Add any new URLs that aren't in the database yet
            existing_urls = {repo.url for repo in db.query(Repository.url).all()}
            new_urls = [url for url in all_urls if url not in existing_urls]

            # Combine new URLs with stale URLs, limiting to chunk_size
            urls_to_process = new_urls + stale_urls
            urls_to_process = urls_to_process[:chunk_size]

            logger.info(
                f"Selected {len(urls_to_process)} repositories for refresh "
                f"({len(new_urls)} new, {len(stale_urls)} existing)"
            )

            return urls_to_process

        finally:
            db.close()

    def process_chunk(self, all_urls: List[str], chunk_size: int = 250) -> dict:
        """Process a chunk of repositories (up to chunk_size) that need refreshing."""

        # Get repositories that need refreshing
        urls_to_process = self.get_repositories_for_refresh(all_urls, chunk_size)

        if not urls_to_process:
            logger.info("No repositories need refreshing at this time")
            return {"success": 0, "error": 0, "skipped": len(all_urls)}

        logger.info(f"Processing {len(urls_to_process)} repositories in chunk")

        # Process the chunk using existing batch method
        results = self.process_batch(urls_to_process)

        logger.info(
            f"Chunk completed: {results['success']} success, {results['error']} errors"
        )

        return {
            "success": results["success"],
            "error": results["error"],
            "processed": len(urls_to_process),
            "total_available": len(all_urls),
        }

    def get_refresh_status(self) -> dict:
        """Get status of repositories by freshness."""
        db = SessionLocal()
        try:
            total_repos = db.query(Repository).count()

            # Count by staleness
            now = datetime.utcnow()
            one_day_ago = now - timedelta(days=1)
            one_week_ago = now - timedelta(days=7)

            fresh_repos = (
                db.query(Repository)
                .filter(Repository.last_fetched > one_day_ago)
                .count()
            )

            recent_repos = (
                db.query(Repository)
                .filter(
                    Repository.last_fetched <= one_day_ago,
                    Repository.last_fetched > one_week_ago,
                )
                .count()
            )

            stale_repos = (
                db.query(Repository)
                .filter(Repository.last_fetched <= one_week_ago)
                .count()
            )

            never_fetched = (
                db.query(Repository).filter(Repository.last_fetched.is_(None)).count()
            )

            completed_repos = (
                db.query(Repository)
                .filter(Repository.processing_status == "completed")
                .count()
            )

            return {
                "total_repositories": total_repos,
                "completed_repositories": completed_repos,
                "freshness": {
                    "fresh_1_day": fresh_repos,
                    "recent_1_week": recent_repos,
                    "stale_older": stale_repos,
                    "never_fetched": never_fetched,
                },
            }

        finally:
            db.close()

    def close(self):
        """Close database connection and log final stats."""
        if self.processed_count > 0:
            stats = self.get_processing_stats()
            logger.info(f"Final processing stats: {stats}")
        self.db.close()

#!/usr/bin/env python3
"""
Dependency Analysis System for Swift Packages
Provides data structures and parsing utilities for Package.swift files.
"""

import re
import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PackageDependency:
    """Represents a single package dependency."""

    name: str
    url: str
    version_requirement: Optional[str] = None
    type: str = "regular"  # regular, development, test
    resolved_owner: Optional[str] = None
    resolved_repo: Optional[str] = None

    def __post_init__(self):
        """Extract owner and repo from URL."""
        if self.url and not self.resolved_owner:
            self.resolved_owner, self.resolved_repo = self._parse_github_url(self.url)

    def _parse_github_url(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse GitHub URL to extract owner and repository name."""
        try:
            # Remove .git suffix and clean URL
            clean_url = url.rstrip(".git")

            # Handle various GitHub URL formats
            patterns = [
                r"github\.com[:/]([^/]+)/([^/]+)",
                r"github\.com/([^/]+)/([^/]+)",
            ]

            for pattern in patterns:
                match = re.search(pattern, clean_url)
                if match:
                    return match.group(1), match.group(2)

            return None, None
        except Exception:
            return None, None


@dataclass
class DependencyNode:
    """Represents a node in the dependency tree."""

    package_id: str  # owner/repo format
    name: str
    owner: str
    repo: str
    url: str
    stars: int = 0
    forks: int = 0
    has_package_swift: bool = False
    linux_compatible: bool = False
    android_compatible: bool = False
    dependencies: List[PackageDependency] = None
    dependents: List[str] = None  # List of package_ids that depend on this
    depth: int = 0

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.dependents is None:
            self.dependents = []

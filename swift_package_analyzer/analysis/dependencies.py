#!/usr/bin/env python3
"""
Dependency Analysis System for Swift Packages
Analyzes Package.swift files to create dependency trees and network visualizations.
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import deque
from dataclasses import dataclass

import networkx as nx

from swift_package_analyzer.core.models import Repository, SessionLocal

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


class EnhancedPackageSwiftParser:
    """Enhanced parser for Package.swift files with better dependency extraction."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse_package_swift(self, content: str) -> List[PackageDependency]:
        """Enhanced parsing of Package.swift content to extract dependencies."""
        dependencies = []

        try:
            # Remove comments and clean content
            content = self._clean_package_swift_content(content)

            # Extract dependencies section
            deps_section = self._extract_dependencies_section(content)
            if not deps_section:
                return dependencies

            # Parse individual dependency declarations
            dependencies.extend(self._parse_dependency_declarations(deps_section))

            self.logger.debug(f"Parsed {len(dependencies)} dependencies")
            return dependencies

        except Exception as e:
            self.logger.error(f"Error parsing Package.swift: {e}")
            return dependencies

    def _clean_package_swift_content(self, content: str) -> str:
        """Clean Package.swift content by removing comments and normalizing whitespace."""
        # Remove single-line comments
        content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)

        # Remove multi-line comments
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        # Normalize whitespace
        content = re.sub(r"\s+", " ", content)

        return content

    def _extract_dependencies_section(self, content: str) -> Optional[str]:
        """Extract the dependencies array from Package.swift content."""
        # Look for dependencies: [ ... ] pattern
        patterns = [
            r"dependencies\s*:\s*\[(.*?)\]",
            r"dependencies\s*:\s*\[(.*?)\n\s*\]",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _parse_dependency_declarations(
        self, deps_content: str
    ) -> List[PackageDependency]:
        """Parse individual dependency declarations from the dependencies section."""
        dependencies = []

        # Split by .package( to find individual package declarations
        package_declarations = re.findall(
            r"\.package\([^)]*(?:\([^)]*\)[^)]*)*\)", deps_content
        )

        for declaration in package_declarations:
            dep = self._parse_single_dependency(declaration)
            if dep:
                dependencies.append(dep)

        return dependencies

    def _parse_single_dependency(self, declaration: str) -> Optional[PackageDependency]:
        """Parse a single .package(...) declaration."""
        try:
            # Extract URL
            url_patterns = [
                r'url\s*:\s*["\']([^"\']+)["\']',
                r'url\s*:\s*["\']([^"\']+)["\']',
            ]

            url = None
            for pattern in url_patterns:
                match = re.search(pattern, declaration)
                if match:
                    url = match.group(1)
                    break

            if not url:
                return None

            # Extract name (if explicitly specified)
            name_match = re.search(r'name\s*:\s*["\']([^"\']+)["\']', declaration)
            name = (
                name_match.group(1) if name_match else self._extract_name_from_url(url)
            )

            # Extract version requirements
            version_requirement = self._extract_version_requirement(declaration)

            # Determine dependency type
            dep_type = "regular"
            if "testTarget" in declaration or "test" in declaration.lower():
                dep_type = "test"

            return PackageDependency(
                name=name,
                url=url,
                version_requirement=version_requirement,
                type=dep_type,
            )

        except Exception as e:
            self.logger.warning(
                f"Error parsing dependency declaration '{declaration}': {e}"
            )
            return None

    def _extract_name_from_url(self, url: str) -> str:
        """Extract package name from URL."""
        # Extract repository name from URL
        match = re.search(r"/([^/]+?)(?:\.git)?$", url)
        return match.group(1) if match else url.split("/")[-1]

    def _extract_version_requirement(self, declaration: str) -> Optional[str]:
        """Extract version requirement from package declaration."""
        version_patterns = [
            r'from\s*:\s*["\']([^"\']+)["\']',
            r'\.upToNext(?:Major|Minor)From\s*\(\s*["\']([^"\']+)["\']',
            r'exact\s*:\s*["\']([^"\']+)["\']',
            r'branch\s*:\s*["\']([^"\']+)["\']',
            r'revision\s*:\s*["\']([^"\']+)["\']',
        ]

        for pattern in version_patterns:
            match = re.search(pattern, declaration)
            if match:
                return match.group(1)

        return None


class DependencyTreeAnalyzer:
    """Analyzes dependency relationships and builds dependency trees."""

    def __init__(self):
        self.db = SessionLocal()
        self.parser = EnhancedPackageSwiftParser()
        self.logger = logging.getLogger(self.__class__.__name__)

        # Cache for processed packages
        self._package_cache: Dict[str, DependencyNode] = {}
        self._dependency_graph: nx.DiGraph = nx.DiGraph()

    def build_dependency_tree(
        self, refresh_cache: bool = False
    ) -> Dict[str, DependencyNode]:
        """Build comprehensive dependency tree from all repositories."""
        if refresh_cache or not self._package_cache:
            self.logger.info("Building dependency tree from database...")
            self._build_package_cache()
            self._build_dependency_graph()
            self._calculate_dependency_metrics()

        return self._package_cache

    def _build_package_cache(self):
        """Build cache of all packages with their metadata."""
        repos = (
            self.db.query(Repository)
            .filter(Repository.processing_status == "completed")
            .all()
        )

        self.logger.info(
            f"Processing {len(repos)} repositories for dependency analysis"
        )

        for repo in repos:
            package_id = f"{repo.owner}/{repo.name}"

            # Parse dependencies if Package.swift exists
            dependencies = []
            if repo.package_swift_content:
                dependencies = self.parser.parse_package_swift(
                    repo.package_swift_content
                )

            node = DependencyNode(
                package_id=package_id,
                name=repo.name,
                owner=repo.owner,
                repo=repo.name,
                url=repo.url,
                stars=repo.stars or 0,
                forks=repo.forks or 0,
                has_package_swift=repo.has_package_swift or False,
                linux_compatible=repo.linux_compatible or False,
                android_compatible=repo.android_compatible or False,
                dependencies=dependencies,
            )

            self._package_cache[package_id] = node

    def _build_dependency_graph(self):
        """Build NetworkX graph of dependencies."""
        self.logger.info("Building dependency graph...")

        for package_id, node in self._package_cache.items():
            # Add node to graph
            self._dependency_graph.add_node(
                package_id,
                name=node.name,
                stars=node.stars,
                forks=node.forks,
                has_package_swift=node.has_package_swift,
                linux_compatible=node.linux_compatible,
                android_compatible=node.android_compatible,
            )

            # Add edges for dependencies
            for dep in node.dependencies:
                if dep.resolved_owner and dep.resolved_repo:
                    dep_package_id = f"{dep.resolved_owner}/{dep.resolved_repo}"

                    # Add dependency node if it doesn't exist
                    if dep_package_id not in self._dependency_graph:
                        self._dependency_graph.add_node(
                            dep_package_id,
                            name=dep.resolved_repo,
                            external=True,  # Mark as external dependency
                        )

                    # Add edge from package to its dependency
                    self._dependency_graph.add_edge(
                        package_id,
                        dep_package_id,
                        dependency_type=dep.type,
                        version_requirement=dep.version_requirement,
                    )

                    # Update dependents list
                    if dep_package_id in self._package_cache:
                        self._package_cache[dep_package_id].dependents.append(
                            package_id
                        )

    def _calculate_dependency_metrics(self):
        """Calculate various dependency metrics for each package."""
        self.logger.info("Calculating dependency metrics...")

        for package_id, node in self._package_cache.items():
            if package_id in self._dependency_graph:
                # Calculate metrics
                node.depth = self._calculate_dependency_depth(package_id)

                # Add graph-based metrics
                in_degree = self._dependency_graph.in_degree(
                    package_id
                )  # How many depend on this
                out_degree = self._dependency_graph.out_degree(
                    package_id
                )  # How many this depends on

                node.dependency_count = out_degree
                node.dependent_count = in_degree

    def _calculate_dependency_depth(self, package_id: str) -> int:
        """Calculate the maximum depth of dependencies for a package."""
        try:
            if package_id not in self._dependency_graph:
                return 0

            # Use BFS to find maximum depth
            max_depth = 0
            visited = set()
            queue = deque([(package_id, 0)])

            while queue:
                current_id, depth = queue.popleft()
                if current_id in visited:
                    continue

                visited.add(current_id)
                max_depth = max(max_depth, depth)

                # Add dependencies to queue
                for successor in self._dependency_graph.successors(current_id):
                    if successor not in visited:
                        queue.append((successor, depth + 1))

            return max_depth
        except Exception as e:
            self.logger.warning(f"Error calculating depth for {package_id}: {e}")
            return 0

    def get_impact_analysis(self) -> Dict[str, Any]:
        """Analyze impact of migrating packages based on dependency relationships."""
        impact_data = []

        for package_id, node in self._package_cache.items():
            if package_id in self._dependency_graph:
                # Calculate impact metrics
                direct_dependents = len(
                    list(self._dependency_graph.predecessors(package_id))
                )
                indirect_impact = self._calculate_indirect_impact(package_id)

                impact_data.append(
                    {
                        "package_id": package_id,
                        "name": node.name,
                        "owner": node.owner,
                        "stars": node.stars,
                        "direct_dependents": direct_dependents,
                        "indirect_impact": indirect_impact,
                        "total_impact": direct_dependents + indirect_impact,
                        "has_package_swift": node.has_package_swift,
                        "linux_compatible": node.linux_compatible,
                        "android_compatible": node.android_compatible,
                        "dependency_count": len(node.dependencies),
                    }
                )

        # Sort by total impact
        impact_data.sort(key=lambda x: x["total_impact"], reverse=True)

        return {
            "packages": impact_data,
            "summary": {
                "total_packages": len(impact_data),
                "high_impact_packages": len(
                    [p for p in impact_data if p["total_impact"] > 5]
                ),
                "foundational_packages": len(
                    [p for p in impact_data if p["direct_dependents"] > 10]
                ),
            },
        }

    def _calculate_indirect_impact(
        self, package_id: str, visited: Set[str] = None
    ) -> int:
        """Calculate indirect impact by counting packages that would be unlocked."""
        if visited is None:
            visited = set()

        if package_id in visited:
            return 0

        visited.add(package_id)
        indirect_count = 0

        # Count packages that depend on this package
        for dependent in self._dependency_graph.predecessors(package_id):
            indirect_count += 1 + self._calculate_indirect_impact(
                dependent, visited.copy()
            )

        return indirect_count

    def close(self):
        """Close database connection."""
        self.db.close()


def main():
    """Main entry point for dependency analysis."""
    import argparse

    parser = argparse.ArgumentParser(description="Swift Package Dependency Analysis")
    parser.add_argument(
        "--output-dir", default="docs/dependencies", help="Output directory"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    analyzer = DependencyTreeAnalyzer()

    try:
        print("🔍 Building dependency tree...")
        analyzer.build_dependency_tree()

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print("📊 Generating impact analysis...")
        impact_analysis = analyzer.get_impact_analysis()

        # Save impact analysis
        with open(output_dir / "impact_analysis.json", "w") as f:
            json.dump(impact_analysis, f, indent=2)
        print(f"✅ Impact analysis saved to {output_dir / 'impact_analysis.json'}")

        # Show top impact packages
        print("\n🎯 Top 10 Packages by Dependency Impact:")
        for i, pkg in enumerate(impact_analysis["packages"][:10], 1):
            print(
                f"{i:2d}. {pkg['package_id']} - Impact: {pkg['total_impact']} packages"
            )

        print(f"\n🎉 Dependency analysis complete! Files saved to {output_dir}")

    finally:
        analyzer.close()


if __name__ == "__main__":
    main()

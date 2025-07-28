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

import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot
import networkx as nx
from jinja2 import Template

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

    def get_dependency_tree_for_package(
        self, package_id: str, max_depth: int = 3
    ) -> Dict[str, Any]:
        """Get dependency tree for a specific package."""
        if package_id not in self._package_cache:
            return {"error": f"Package {package_id} not found"}

        tree = self._build_tree_recursive(package_id, max_depth, 0, set())
        return {
            "root": package_id,
            "tree": tree,
            "stats": self._calculate_tree_stats(tree),
        }

    def _build_tree_recursive(
        self, package_id: str, max_depth: int, current_depth: int, visited: Set[str]
    ) -> Dict[str, Any]:
        """Recursively build dependency tree."""
        if current_depth >= max_depth or package_id in visited:
            return {"package_id": package_id, "truncated": True}

        visited.add(package_id)

        node_data = {
            "package_id": package_id,
            "depth": current_depth,
            "dependencies": [],
        }

        # Add package metadata if available
        if package_id in self._package_cache:
            pkg = self._package_cache[package_id]
            node_data.update(
                {
                    "name": pkg.name,
                    "stars": pkg.stars,
                    "has_package_swift": pkg.has_package_swift,
                    "linux_compatible": pkg.linux_compatible,
                    "android_compatible": pkg.android_compatible,
                }
            )

        # Add dependencies
        if package_id in self._dependency_graph:
            for dep_id in self._dependency_graph.successors(package_id):
                dep_tree = self._build_tree_recursive(
                    dep_id, max_depth, current_depth + 1, visited.copy()
                )
                node_data["dependencies"].append(dep_tree)

        return node_data

    def _calculate_tree_stats(self, tree: Dict[str, Any]) -> Dict[str, int]:
        """Calculate statistics for a dependency tree."""
        stats = {
            "total_packages": 0,
            "max_depth": 0,
            "external_dependencies": 0,
            "linux_compatible": 0,
            "android_compatible": 0,
        }

        def count_recursive(node: Dict[str, Any], depth: int):
            stats["total_packages"] += 1
            stats["max_depth"] = max(stats["max_depth"], depth)

            if node.get("linux_compatible"):
                stats["linux_compatible"] += 1
            if node.get("android_compatible"):
                stats["android_compatible"] += 1
            if node.get("package_id", "").count("/") == 1 and not node.get(
                "has_package_swift"
            ):
                stats["external_dependencies"] += 1

            for dep in node.get("dependencies", []):
                count_recursive(dep, depth + 1)

        count_recursive(tree, 0)
        return stats

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


class DependencyVisualizer:
    """Creates visualizations for dependency relationships."""

    def __init__(self, analyzer: DependencyTreeAnalyzer):
        self.analyzer = analyzer
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_dependency_network_visualization(
        self, output_path: str, max_nodes: int = 100
    ) -> str:
        """Generate interactive network visualization of dependencies."""
        self.logger.info(
            f"Generating dependency network visualization with max {max_nodes} nodes"
        )

        # Get top packages by impact
        impact_analysis = self.analyzer.get_impact_analysis()
        top_packages = impact_analysis["packages"][:max_nodes]

        # Build subgraph
        package_ids = [p["package_id"] for p in top_packages]
        subgraph = self.analyzer._dependency_graph.subgraph(package_ids)

        # Calculate layout
        pos = nx.spring_layout(subgraph, k=3, iterations=50)

        # Create edges
        edge_x = []
        edge_y = []
        edge_info = []

        for edge in subgraph.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_info.append(f"{edge[0]} → {edge[1]}")

        # Create nodes
        node_x = []
        node_y = []
        node_text = []
        node_size = []
        node_color = []
        node_info = []

        for node in subgraph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            # Get node data
            node_data = subgraph.nodes[node]
            package_data = next(
                (p for p in top_packages if p["package_id"] == node), {}
            )

            stars = package_data.get("stars", 0)
            impact = package_data.get("total_impact", 0)

            node_text.append(node.split("/")[-1])  # Show just repo name
            node_size.append(max(10, min(50, stars / 100)))  # Size by stars

            # Color by compatibility status
            if package_data.get("android_compatible"):
                node_color.append("green")
            elif package_data.get("linux_compatible"):
                node_color.append("orange")
            else:
                node_color.append("red")

            node_info.append(
                f"<b>{node}</b><br>"
                f"Stars: {stars}<br>"
                f"Impact: {impact} packages<br>"
                f"Direct dependents: {package_data.get('direct_dependents', 0)}<br>"
                f"Linux: {'✅' if package_data.get('linux_compatible') else '❌'}<br>"
                f"Android: {'✅' if package_data.get('android_compatible') else '❌'}"
            )

        # Create Plotly figure
        fig = go.Figure()

        # Add edges
        fig.add_trace(
            go.Scatter(
                x=edge_x,
                y=edge_y,
                line=dict(width=1, color="rgba(125,125,125,0.3)"),
                hoverinfo="none",
                mode="lines",
                showlegend=False,
            )
        )

        # Add nodes
        fig.add_trace(
            go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers+text",
                hoverinfo="text",
                text=node_text,
                textposition="middle center",
                hovertext=node_info,
                marker=dict(
                    size=node_size,
                    color=node_color,
                    line=dict(width=2, color="white"),
                    opacity=0.8,
                ),
                textfont=dict(size=8),
                showlegend=False,
            )
        )

        fig.update_layout(
            title="Swift Package Dependency Network<br><sub>Orange: Linux-only, Green: Android-compatible, Red: Neither</sub>",
            titlefont_size=16,
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    text="Node size = GitHub stars, Color = compatibility status",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.005,
                    y=-0.002,
                    xanchor="left",
                    yanchor="bottom",
                    font=dict(color="gray", size=12),
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="white",
        )

        # Save visualization
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plot(fig, filename=output_path, auto_open=False)

        self.logger.info(f"Dependency network visualization saved to {output_path}")
        return output_path

    def generate_dependency_tree_html(
        self, package_id: str, output_path: str, max_depth: int = 3
    ) -> str:
        """Generate HTML visualization of a specific package's dependency tree."""
        tree_data = self.analyzer.get_dependency_tree_for_package(package_id, max_depth)

        if "error" in tree_data:
            raise ValueError(tree_data["error"])

        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Dependency Tree: {{ package_id }}</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .tree { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .tree-node { margin: 10px 0; padding: 10px; border-left: 3px solid #ddd; margin-left: 20px; }
        .tree-node.depth-0 { border-left-color: #007acc; margin-left: 0; }
        .tree-node.depth-1 { border-left-color: #28a745; }
        .tree-node.depth-2 { border-left-color: #ffc107; }
        .tree-node.depth-3 { border-left-color: #dc3545; }
        .package-name { font-weight: bold; color: #333; }
        .package-stats { color: #666; font-size: 0.9em; margin-top: 5px; }
        .compatibility { display: inline-block; margin-right: 10px; }
        .compatible { color: green; }
        .incompatible { color: red; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px; }
        .stat-card { background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-value { font-size: 1.5em; font-weight: bold; color: #007acc; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Dependency Tree Analysis</h1>
            <h2>{{ package_id }}</h2>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{{ stats.total_packages }}</div>
                    <div>Total Packages</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ stats.max_depth }}</div>
                    <div>Maximum Depth</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ stats.linux_compatible }}</div>
                    <div>Linux Compatible</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ stats.android_compatible }}</div>
                    <div>Android Compatible</div>
                </div>
            </div>
        </div>
        
        <div class="tree">
            {{ render_tree_node(tree, 0) }}
        </div>
    </div>
</body>
</html>
        """

        def render_tree_node(node, depth):
            """Recursively render tree nodes."""
            html = f'<div class="tree-node depth-{depth}">'
            html += (
                f'<div class="package-name">{node.get("package_id", "Unknown")}</div>'
            )

            if node.get("stars") is not None:
                html += '<div class="package-stats">'
                html += f'⭐ {node["stars"]} stars | '
                html += f'<span class="compatibility {"compatible" if node.get("linux_compatible") else "incompatible"}">Linux: {"✅" if node.get("linux_compatible") else "❌"}</span> | '
                html += f'<span class="compatibility {"compatible" if node.get("android_compatible") else "incompatible"}">Android: {"✅" if node.get("android_compatible") else "❌"}</span>'
                html += "</div>"

            # Render dependencies
            for dep in node.get("dependencies", []):
                html += render_tree_node(dep, depth + 1)

            html += "</div>"
            return html

        template = Template(html_template)
        template.globals["render_tree_node"] = render_tree_node

        html_content = template.render(
            package_id=package_id, tree=tree_data["tree"], stats=tree_data["stats"]
        )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.logger.info(f"Dependency tree HTML saved to {output_path}")
        return output_path


def main():
    """Main entry point for dependency analysis."""
    import argparse

    parser = argparse.ArgumentParser(description="Swift Package Dependency Analysis")
    parser.add_argument(
        "--output-dir", default="exports/dependencies", help="Output directory"
    )
    parser.add_argument("--package", help="Specific package to analyze (owner/repo)")
    parser.add_argument(
        "--max-nodes",
        type=int,
        default=100,
        help="Maximum nodes in network visualization",
    )
    parser.add_argument(
        "--max-depth", type=int, default=3, help="Maximum depth for tree analysis"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    analyzer = DependencyTreeAnalyzer()
    visualizer = DependencyVisualizer(analyzer)

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

        print("🕸️ Generating network visualization...")
        network_path = visualizer.generate_dependency_network_visualization(
            str(output_dir / "dependency_network.html"), args.max_nodes
        )

        # Generate tree visualization for specific package if requested
        if args.package:
            print(f"🌳 Generating dependency tree for {args.package}...")
            tree_path = visualizer.generate_dependency_tree_html(
                args.package,
                str(
                    output_dir
                    / f"dependency_tree_{args.package.replace('/', '_')}.html"
                ),
                args.max_depth,
            )

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

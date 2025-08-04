"""
Analysis and visualization tools for Swift Package support data.
"""

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from swift_package_analyzer.core.models import Repository, SessionLocal


class PackageAnalyzer:
    """Analyzes Swift Package data and generates insights."""

    def __init__(self):
        self.db = SessionLocal()

    def get_completed_repositories(self) -> pd.DataFrame:
        """Get all completed repositories as a pandas DataFrame."""
        repos = (
            self.db.query(Repository)
            .filter(Repository.processing_status == "completed")
            .all()
        )

        data = []
        for repo in repos:
            data.append(
                {
                    "owner": repo.owner,
                    "name": repo.name,
                    "stars": repo.stars or 0,
                    "forks": repo.forks or 0,
                    "watchers": repo.watchers or 0,
                    "issues_count": repo.issues_count or 0,
                    "open_issues_count": repo.open_issues_count or 0,
                    "language": repo.language,
                    "license_name": repo.license_name,
                    "has_package_swift": repo.has_package_swift,
                    "swift_tools_version": repo.swift_tools_version,
                    "dependencies_count": repo.dependencies_count or 0,
                    "linux_compatible": repo.linux_compatible,
                    "android_compatible": repo.android_compatible,
                    "current_state": repo.current_state,
                    "created_at": repo.created_at,
                    "updated_at": repo.updated_at,
                    "pushed_at": repo.pushed_at,
                }
            )

        return pd.DataFrame(data)

    def get_tracking_repositories(self) -> pd.DataFrame:
        """Get repositories that are currently being tracked for migration."""
        repos = (
            self.db.query(Repository)
            .filter(
                Repository.processing_status == "completed",
                Repository.current_state.in_(["tracking", "in_progress", "unknown"]),
            )
            .all()
        )
        data = []
        for repo in repos:
            data.append(
                {
                    "owner": repo.owner,
                    "name": repo.name,
                    "stars": repo.stars or 0,
                    "forks": repo.forks or 0,
                    "watchers": repo.watchers or 0,
                    "issues_count": repo.issues_count or 0,
                    "open_issues_count": repo.open_issues_count or 0,
                    "language": repo.language,
                    "license_name": repo.license_name,
                    "has_package_swift": repo.has_package_swift,
                    "swift_tools_version": repo.swift_tools_version,
                    "dependencies_count": repo.dependencies_count or 0,
                    "linux_compatible": repo.linux_compatible,
                    "android_compatible": repo.android_compatible,
                    "current_state": repo.current_state,
                    "created_at": repo.created_at,
                    "updated_at": repo.updated_at,
                    "pushed_at": repo.pushed_at,
                }
            )
        return pd.DataFrame(data)

    def get_all_repositories_for_display(self) -> pd.DataFrame:
        """Get all repositories for web interface display, including android_supported ones."""
        repos = (
            self.db.query(Repository)
            .filter(
                Repository.processing_status == "completed",
                Repository.current_state.in_(
                    ["tracking", "in_progress", "unknown", "android_supported"]
                ),
            )
            .all()
        )

        data = []
        for repo in repos:
            data.append(
                {
                    "owner": repo.owner,
                    "name": repo.name,
                    "stars": repo.stars or 0,
                    "forks": repo.forks or 0,
                    "watchers": repo.watchers or 0,
                    "issues_count": repo.issues_count or 0,
                    "open_issues_count": repo.open_issues_count or 0,
                    "language": repo.language,
                    "license_name": repo.license_name,
                    "has_package_swift": repo.has_package_swift,
                    "swift_tools_version": repo.swift_tools_version,
                    "dependencies_count": repo.dependencies_count or 0,
                    "linux_compatible": repo.linux_compatible,
                    "android_compatible": repo.android_compatible,
                    "current_state": repo.current_state,
                    "created_at": repo.created_at,
                    "updated_at": repo.updated_at,
                    "pushed_at": repo.pushed_at,
                }
            )
        return pd.DataFrame(data)

    def get_all_repositories_unfiltered(self) -> pd.DataFrame:
        """Get ALL repositories without any filtering - pure data dump for frontend consumption."""
        repos = (
            self.db.query(Repository)
            .filter(Repository.processing_status == "completed")
            .all()
        )

        data = []
        for repo in repos:
            data.append(
                {
                    "owner": repo.owner,
                    "name": repo.name,
                    "stars": repo.stars or 0,
                    "forks": repo.forks or 0,
                    "watchers": repo.watchers or 0,
                    "issues_count": repo.issues_count or 0,
                    "open_issues_count": repo.open_issues_count or 0,
                    "language": repo.language,
                    "license_name": repo.license_name,
                    "has_package_swift": repo.has_package_swift,
                    "swift_tools_version": repo.swift_tools_version,
                    "dependencies_count": repo.dependencies_count or 0,
                    "linux_compatible": repo.linux_compatible,
                    "android_compatible": repo.android_compatible,
                    "current_state": repo.current_state,
                    "created_at": repo.created_at,
                    "updated_at": repo.updated_at,
                    "pushed_at": repo.pushed_at,
                }
            )
        return pd.DataFrame(data)

    def generate_popularity_analysis(self) -> Dict[str, Any]:
        """Analyze repository popularity metrics."""
        df = self.get_completed_repositories()

        if df.empty:
            return {"error": "No data available"}

        analysis = {
            "total_repositories": len(df),
            "star_statistics": {
                "mean": df["stars"].mean(),
                "median": df["stars"].median(),
                "std": df["stars"].std(),
                "top_10": df.nlargest(10, "stars")[["owner", "name", "stars"]].to_dict(
                    "records"
                ),
            },
            "fork_statistics": {
                "mean": df["forks"].mean(),
                "median": df["forks"].median(),
                "top_10": df.nlargest(10, "forks")[["owner", "name", "forks"]].to_dict(
                    "records"
                ),
            },
        }

        return analysis

    def generate_dependency_analysis(self) -> Dict[str, Any]:
        """Analyze dependency patterns."""
        df = self.get_completed_repositories()

        if df.empty:
            return {"error": "No data available"}

        analysis = {
            "dependency_statistics": {
                "mean_dependencies": df["dependencies_count"].mean(),
                "median_dependencies": df["dependencies_count"].median(),
                "max_dependencies": df["dependencies_count"].max(),
                "repositories_without_dependencies": (
                    df["dependencies_count"] == 0
                ).sum(),
            },
        }

        return analysis

    def generate_language_analysis(self) -> Dict[str, Any]:
        """Analyze programming language distribution."""
        df = self.get_completed_repositories()

        if df.empty:
            return {"error": "No data available"}

        language_counts = df["language"].value_counts()

        analysis = {
            "language_distribution": language_counts.to_dict(),
            "total_languages": len(language_counts),
            "swift_percentage": (
                (language_counts.get("Swift", 0) / len(df)) * 100 if len(df) > 0 else 0
            ),
        }

        return analysis

    def generate_priority_analysis(self) -> List[Dict[str, Any]]:
        """Generate priority list for Android compatibility work."""
        # Only analyze repositories that are still being tracked (not android_supported, archived, etc.)
        df = self.get_tracking_repositories()

        if df.empty:
            return []

        # Calculate priority score based on multiple factors
        df["priority_score"] = 0

        # Factor 1: Popularity (stars) - normalized to 0-1
        max_stars = df["stars"].max()
        if max_stars > 0:
            df["popularity_score"] = df["stars"] / max_stars
            df["priority_score"] += df["popularity_score"] * 0.4  # 40% weight

        # Factor 2: Community engagement (forks + watchers) - normalized
        df["engagement"] = df["forks"] + df["watchers"]
        max_engagement = df["engagement"].max()
        if max_engagement > 0:
            df["engagement_score"] = df["engagement"] / max_engagement
            df["priority_score"] += df["engagement_score"] * 0.3  # 30% weight

        # Factor 3: Recent activity (based on pushed_at) - normalized
        if "pushed_at" in df.columns and df["pushed_at"].notna().any():
            df["pushed_at"] = pd.to_datetime(df["pushed_at"])
            current_time = pd.Timestamp.now()
            df["days_since_push"] = (current_time - df["pushed_at"]).dt.days
            # More recent = higher score
            max_days = df["days_since_push"].max()
            if max_days > 0:
                df["recency_score"] = 1 - (df["days_since_push"] / max_days)
                df["priority_score"] += df["recency_score"] * 0.2  # 20% weight

        # Factor 4: Low dependency complexity (easier to migrate)
        max_deps = df["dependencies_count"].max()
        if max_deps > 0:
            df["simplicity_score"] = 1 - (df["dependencies_count"] / max_deps)
            df["priority_score"] += df["simplicity_score"] * 0.1  # 10% weight

        # Sort by star count - show all repositories
        priority_repos = df.sort_values("stars", ascending=False)

        result = []
        for _, repo in priority_repos.iterrows():
            result.append(
                {
                    "owner": repo["owner"],
                    "name": repo["name"],
                    "stars": repo["stars"],
                    "forks": repo["forks"],
                    "dependencies_count": repo["dependencies_count"],
                    "priority_score": round(repo["priority_score"], 3),
                    "has_package_swift": repo["has_package_swift"],
                    "swift_tools_version": repo["swift_tools_version"],
                    "current_state": repo["current_state"],
                    "rationale": self._generate_priority_rationale(repo),
                }
            )

        return result

    def generate_unfiltered_data_dump(self) -> List[Dict[str, Any]]:
        """Generate pure data dump of ALL repositories without any filtering or processing for frontend consumption."""
        df = self.get_all_repositories_unfiltered()

        if df.empty:
            return []

        # Return raw data without any scoring or filtering - just convert to dict format
        result = []
        for _, repo in df.iterrows():
            result.append(
                {
                    "owner": repo["owner"],
                    "name": repo["name"],
                    "stars": repo["stars"],
                    "forks": repo["forks"],
                    "watchers": repo["watchers"],
                    "issues_count": repo["issues_count"],
                    "open_issues_count": repo["open_issues_count"],
                    "language": repo["language"],
                    "license_name": repo["license_name"],
                    "has_package_swift": repo["has_package_swift"],
                    "swift_tools_version": repo["swift_tools_version"],
                    "dependencies_count": repo["dependencies_count"],
                    "linux_compatible": repo["linux_compatible"],
                    "android_compatible": repo["android_compatible"],
                    "current_state": repo["current_state"],
                    "created_at": repo["created_at"],
                    "updated_at": repo["updated_at"],
                    "pushed_at": repo["pushed_at"],
                }
            )

        return result

    def _generate_priority_rationale(self, repo) -> str:
        """Generate a rationale for why this repository is prioritized."""
        reasons = []

        if repo["stars"] > 1000:
            reasons.append("High popularity")

        if repo["forks"] > 100:
            reasons.append("Active community")

        if repo["dependencies_count"] <= 5:
            reasons.append("Low complexity")

        if repo["has_package_swift"]:
            reasons.append("Modern Swift package")

        return "; ".join(reasons) if reasons else "General priority"

    def close(self):
        """Close database connection."""
        self.db.close()

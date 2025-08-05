"""
Analysis and visualization tools for Swift Package support data.
"""

from typing import Any, Dict, List

import pandas as pd

from src.models import Repository, SessionLocal


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

    def close(self):
        """Close database connection."""
        self.db.close()

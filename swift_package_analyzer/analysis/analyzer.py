"""
Analysis and visualization tools for Swift Package support data.
"""

from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from swift_package_analyzer.core.models import Repository, SessionLocal


class PackageAnalyzer:
    """Analyzes Swift Package data and generates insights."""

    def __init__(self):
        self.db = SessionLocal()
        # Set up matplotlib style
        plt.style.use("seaborn-v0_8")
        sns.set_palette("husl")

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
                Repository.current_state.in_(["tracking", "in_progress", "unknown", "android_supported"]),
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

    def generate_visualizations(self, output_dir: str = "docs/visualizations"):
        """Generate visualization charts."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        df = self.get_completed_repositories()

        if df.empty:
            print("No data available for visualization")
            return

        # 1. Repository popularity distribution
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))

        # Stars distribution (log scale)
        df[df["stars"] > 0]["stars"].hist(bins=50, ax=ax1, alpha=0.7)
        ax1.set_yscale("log")
        ax1.set_xlabel("Stars")
        ax1.set_ylabel("Number of Repositories (log scale)")
        ax1.set_title("Distribution of Repository Stars")

        # Top 20 most starred repositories
        top_starred = df.nlargest(20, "stars")
        ax2.barh(range(len(top_starred)), top_starred["stars"])
        ax2.set_yticks(range(len(top_starred)))
        ax2.set_yticklabels(
            [f"{row['owner']}/{row['name']}" for _, row in top_starred.iterrows()]
        )
        ax2.set_xlabel("Stars")
        ax2.set_title("Top 20 Most Starred Repositories")

        # Language distribution
        language_counts = df["language"].value_counts().head(10)
        ax3.pie(language_counts.values, labels=language_counts.index, autopct="%1.1f%%")
        ax3.set_title("Programming Language Distribution (Top 10)")

        # Dependencies distribution
        df["dependencies_count"].hist(bins=30, ax=ax4, alpha=0.7)
        ax4.set_xlabel("Number of Dependencies")
        ax4.set_ylabel("Number of Repositories")
        ax4.set_title("Distribution of Dependency Counts")

        plt.tight_layout()
        plt.savefig(
            f"{output_dir}/repository_analysis.png", dpi=300, bbox_inches="tight"
        )
        plt.close()

        # 2. Timeline analysis
        if "created_at" in df.columns and df["created_at"].notna().any():
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

            # Repository creation timeline
            df["created_at"] = pd.to_datetime(df["created_at"])
            creation_by_year = df.groupby(df["created_at"].dt.year).size()

            ax1.plot(creation_by_year.index, creation_by_year.values, marker="o")
            ax1.set_xlabel("Year")
            ax1.set_ylabel("Repositories Created")
            ax1.set_title("Repository Creation Timeline")
            ax1.grid(True, alpha=0.3)

            # Activity heatmap (by year and month)
            df["created_year"] = df["created_at"].dt.year
            df["created_month"] = df["created_at"].dt.month

            activity_matrix = (
                df.groupby(["created_year", "created_month"])
                .size()
                .unstack(fill_value=0)
            )

            if not activity_matrix.empty:
                sns.heatmap(
                    activity_matrix.T,
                    cmap="YlOrRd",
                    ax=ax2,
                    cbar_kws={"label": "Repositories Created"},
                )
                ax2.set_xlabel("Year")
                ax2.set_ylabel("Month")
                ax2.set_title("Repository Creation Activity Heatmap")

            plt.tight_layout()
            plt.savefig(
                f"{output_dir}/timeline_analysis.png", dpi=300, bbox_inches="tight"
            )
            plt.close()

        # 3. Package.swift analysis
        package_swift_repos = df[df["has_package_swift"]]

        if not package_swift_repos.empty:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

            # Swift tools version distribution
            tools_versions = (
                package_swift_repos["swift_tools_version"].value_counts().head(10)
            )
            ax1.bar(range(len(tools_versions)), tools_versions.values)
            ax1.set_xticks(range(len(tools_versions)))
            ax1.set_xticklabels(tools_versions.index, rotation=45)
            ax1.set_xlabel("Swift Tools Version")
            ax1.set_ylabel("Number of Repositories")
            ax1.set_title("Swift Tools Version Distribution")

            # Dependencies vs Stars scatter plot
            scatter_data = package_swift_repos[["stars", "dependencies_count"]].dropna()
            ax2.scatter(
                scatter_data["dependencies_count"], scatter_data["stars"], alpha=0.6
            )
            ax2.set_xlabel("Number of Dependencies")
            ax2.set_ylabel("Stars")
            ax2.set_title("Dependencies vs Repository Popularity")
            ax2.set_yscale("log")

            plt.tight_layout()
            plt.savefig(
                f"{output_dir}/package_swift_analysis.png", dpi=300, bbox_inches="tight"
            )
            plt.close()

        print(f"Visualizations saved to {output_dir}/")

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

    def generate_display_analysis(self) -> List[Dict[str, Any]]:
        """Generate analysis for web display including all relevant repositories (tracking + android_supported)."""
        df = self.get_all_repositories_for_display()
        
        if df.empty:
            return []

        # Calculate priority score based on multiple factors (similar to priority_analysis but for display)
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

        # Factor 3: Package.swift presence (binary: has it or not)
        df["priority_score"] += df["has_package_swift"].astype(int) * 0.2  # 20% weight

        # Factor 4: Recent activity (recency score)
        if "pushed_at" in df.columns:
            max_pushed = df["pushed_at"].max()
            if pd.notna(max_pushed):
                # Days since last push, converted to recency score (0-1, recent = higher)
                df["days_since_push"] = (max_pushed - df["pushed_at"]).dt.days
                max_days = df["days_since_push"].max()
                if max_days > 0:
                    df["recency_score"] = 1 - (df["days_since_push"] / max_days)
                    df["priority_score"] += df["recency_score"] * 0.1  # 10% weight

        # Sort by priority score (descending)
        df_sorted = df.sort_values("priority_score", ascending=False)

        # Format results
        result = []
        for _, repo in df_sorted.iterrows():
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
                    "rationale": self._generate_display_rationale(repo),
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

    def _generate_display_rationale(self, repo) -> str:
        """Generate a rationale for display, including android_supported status."""
        if repo["current_state"] == "android_supported":
            return "Already supports Android platform"
        
        reasons = []
        
        if repo["stars"] > 1000:
            reasons.append("High popularity")
        elif repo["stars"] > 100:
            reasons.append("Good community adoption")

        if repo["forks"] > 50:
            reasons.append("Active community contributions")

        if repo["has_package_swift"]:
            reasons.append("Swift Package Manager ready")

        if repo["dependencies_count"] > 0:
            reasons.append(f"Has {repo['dependencies_count']} dependencies")

        return "; ".join(reasons) if reasons else "Standard migration candidate"

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

    def generate_state_analysis(self) -> Dict[str, Any]:
        """Analyze migration state distribution."""
        df = self.get_completed_repositories()

        if df.empty:
            return {"error": "No data available"}

        state_counts = df["current_state"].value_counts()
        total_repos = len(df)

        analysis = {
            "total_repositories": total_repos,
            "state_distribution": state_counts.to_dict(),
            "state_percentages": {
                state: round((count / total_repos) * 100, 1)
                for state, count in state_counts.items()
            },
            "migration_progress": {
                "android_supported": state_counts.get("android_supported", 0),
                "in_progress": state_counts.get("in_progress", 0),
                "tracking": state_counts.get("tracking", 0),
                "total_active": (
                    state_counts.get("android_supported", 0)
                    + state_counts.get("in_progress", 0)
                    + state_counts.get("tracking", 0)
                ),
            },
        }

        # Calculate completion percentage
        android_supported = state_counts.get("android_supported", 0)
        active_total = analysis["migration_progress"]["total_active"]
        if active_total > 0:
            analysis["migration_progress"]["completion_percentage"] = round(
                (android_supported / active_total) * 100, 1
            )
        else:
            analysis["migration_progress"]["completion_percentage"] = 0

        return analysis

    def close(self):
        """Close database connection."""
        self.db.close()

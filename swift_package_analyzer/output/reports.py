#!/usr/bin/env python3
"""
Enhanced report generation for Swift Package analysis.
Supports multiple output formats including JSON, HTML, and interactive visualizations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from swift_package_analyzer.analysis.analyzer import PackageAnalyzer
from swift_package_analyzer.core.models import Repository, SessionLocal
from swift_package_analyzer.analysis.dependencies import DependencyTreeAnalyzer


class ReportGenerator:
    """Generate comprehensive reports in multiple formats."""

    def __init__(self):
        self.analyzer = PackageAnalyzer()
        self.dependency_analyzer = DependencyTreeAnalyzer()
        self.db = SessionLocal()

    def _generate_executive_summary(
        self, popularity, dependencies, languages
    ) -> Dict[str, Any]:
        """Generate executive summary for the report."""
        total_repos = popularity.get("total_repositories", 0)
        avg_stars = popularity.get("star_statistics", {}).get("mean", 0)

        # Identify key insights
        top_repo = popularity.get("star_statistics", {}).get("top_10", [{}])[0]
        primary_lang = self._get_primary_language(languages)

        summary = {
            "overview": f"Analysis of {total_repos} Swift packages that support Linux but lack Android compatibility",
            "key_metrics": {
                "average_popularity": f"{avg_stars:.0f} stars per repository",
                "primary_language": primary_lang,
                "most_popular": f"{top_repo.get('owner', 'N/A')}/{top_repo.get('name', 'N/A')}"
                if top_repo
                else "N/A",
            },
            "recommendations": [
                "Focus on high-star repositories for maximum impact",
                "Prioritize packages with existing Package.swift files",
                "Consider dependency chains to unlock multiple packages",
                "Target recently active repositories for better maintenance",
            ],
        }

        return summary

    def _get_primary_language(self, languages) -> str:
        """Get the primary programming language from analysis."""
        lang_dist = languages.get("language_distribution", {})
        if not lang_dist:
            return "Unknown"
        return max(lang_dist.items(), key=lambda x: x[1])[0]

    def _get_android_compatibility_stats(self) -> Dict[str, Any]:
        """Get Android compatibility statistics."""
        try:
            total_repos = (
                self.db.query(Repository)
                .filter(Repository.processing_status == "completed")
                .count()
            )

            android_compatible = (
                self.db.query(Repository)
                .filter(
                    Repository.processing_status == "completed",
                    Repository.android_compatible == True,
                )
                .count()
            )

            android_not_compatible = (
                self.db.query(Repository)
                .filter(
                    Repository.processing_status == "completed",
                    Repository.android_compatible == False,
                )
                .count()
            )

            # Calculate percentages
            android_percentage = (
                (android_compatible / total_repos * 100) if total_repos > 0 else 0
            )
            progress_percentage = (
                android_percentage  # Same as android_percentage for now
            )

            return {
                "total_repositories": total_repos,
                "android_compatible": android_compatible,
                "android_not_compatible": android_not_compatible,
                "android_percentage": round(android_percentage, 1),
                "progress_percentage": round(progress_percentage, 1),
                "migration_target": total_repos,
                "remaining_to_migrate": android_not_compatible,
            }
        except Exception as e:
            print(f"Error calculating Android compatibility stats: {e}")
            return {
                "total_repositories": 0,
                "android_compatible": 0,
                "android_not_compatible": 0,
                "android_percentage": 0.0,
                "progress_percentage": 0.0,
                "migration_target": 0,
                "remaining_to_migrate": 0,
            }

    def _get_api_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics from processing logs."""
        from swift_package_analyzer.core.models import ProcessingLog, SessionLocal

        db = SessionLocal()
        try:
            total_api_calls = (
                db.query(ProcessingLog)
                .filter(ProcessingLog.action == "fetch_metadata")
                .count()
            )

            successful_fetches = (
                db.query(ProcessingLog)
                .filter(
                    ProcessingLog.action == "fetch_metadata",
                    ProcessingLog.status == "success",
                )
                .count()
            )

            failed_fetches = (
                db.query(ProcessingLog)
                .filter(
                    ProcessingLog.action == "fetch_metadata",
                    ProcessingLog.status == "error",
                )
                .count()
            )

            success_rate = (
                (successful_fetches / total_api_calls * 100)
                if total_api_calls > 0
                else 0
            )

            return {
                "total_api_calls": total_api_calls,
                "successful_fetches": successful_fetches,
                "failed_fetches": failed_fetches,
                "success_rate": round(success_rate, 1),
            }
        finally:
            db.close()


    def generate_priority_csv(
        self, output_path: str = "docs/priority_analysis.csv", limit: int = 50
    ) -> str:
        """Generate a detailed CSV of priority repositories."""
        priorities = self.analyzer.generate_priority_analysis()[:limit]

        # Convert to DataFrame for better CSV output
        df = pd.DataFrame(priorities)

        # Add additional calculated columns
        df["github_url"] = df.apply(
            lambda row: f"https://github.com/{row['owner']}/{row['name']}", axis=1
        )
        df["package_index_url"] = df.apply(
            lambda row: f"https://swiftpackageindex.com/{row['owner']}/{row['name']}",
            axis=1,
        )

        # Reorder columns for better readability
        column_order = [
            "owner",
            "name",
            "priority_score",
            "stars",
            "forks",
            "watchers",
            "dependencies_count",
            "has_package_swift",
            "swift_tools_version",
            "language",
            "license_name",
            "rationale",
            "github_url",
            "package_index_url",
        ]

        # Only include columns that exist
        existing_columns = [col for col in column_order if col in df.columns]
        df_ordered = df[existing_columns]

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df_ordered.to_csv(output_path, index=False)

        print(f"Priority CSV: {output_path}")
        return output_path

    def generate_github_pages_site(self, output_path: str = "docs/index.html") -> str:
        """Generate a single-file GitHub Pages compatible site."""
        from pathlib import Path
        import json

        print("🌐 Generating GitHub Pages site...")

        # Generate all analyses
        popularity = self.analyzer.generate_popularity_analysis()
        dependencies = self.analyzer.generate_dependency_analysis()
        languages = self.analyzer.generate_language_analysis()
        all_repositories = self.analyzer.generate_unfiltered_data_dump()  # Use unfiltered data dump for frontend

        # Generate dependency tree analysis
        print("Building dependency analysis...")
        self.dependency_analyzer.build_dependency_tree()
        impact_analysis = self.dependency_analyzer.get_impact_analysis()

        if "error" in popularity:
            print("No data available for analysis!")
            return ""

        # Prepare comprehensive data optimized for web
        web_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_repositories": popularity.get("total_repositories", 0),
                "generation_tool": "Swift Package Android Compatibility Analyzer",
                "data_size_kb": 0,  # Will be calculated
            },
            "executive_summary": self._generate_executive_summary(
                popularity, dependencies, languages
            ),
            "popularity_analysis": popularity,
            "dependency_analysis": dependencies,
            "language_analysis": languages,
            "all_repositories": all_repositories,  # Complete unfiltered dataset for frontend
            "dependency_impact_analysis": {
                "packages": impact_analysis.get("packages", [])[:50],  # Top 50 for web
                "summary": impact_analysis.get("summary", {}),
            },
            "statistics": {
                "avg_stars": round(
                    popularity.get("star_statistics", {}).get("mean", 0), 1
                ),
                "median_stars": round(
                    popularity.get("star_statistics", {}).get("median", 0), 1
                ),
                "primary_language": self._get_primary_language(languages),
                "total_analyzed": popularity.get("total_repositories", 0),
                "android_compatibility": self._get_android_compatibility_stats(),
                "api_usage": self._get_api_usage_stats(),
            },
        }

        # Calculate data size
        data_json = json.dumps(web_data, default=str)
        data_size_kb = len(data_json.encode("utf-8")) / 1024
        web_data["metadata"]["data_size_kb"] = round(data_size_kb, 1)

        print(f"📊 Embedded data size: {data_size_kb:.1f} KB")

        # Generate JSON data file for Next.js frontend
        json_output_path = Path(output_path).parent / "swift_packages.json"
        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(web_data, f, indent=2, default=str)
        
        print(f"📊 Data exported to: {json_output_path}")
        
        # Generate a simple redirect HTML page
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0; url=./frontend/">
    <title>Swift Package Analysis - Redirecting...</title>
</head>
<body>
    <p>Redirecting to the analysis dashboard...</p>
    <p>If you are not redirected automatically, <a href="./frontend/">click here</a>.</p>
</body>
</html>"""

        # Save the final file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        final_size_kb = output_file.stat().st_size / 1024
        print(f"✅ Redirect page generated: {output_path}")
        print(f"📄 Final file size: {final_size_kb:.1f} KB")
        print(f"🚀 Data ready for Next.js frontend!")

        return str(output_path)

    def close(self):
        """Close database connections."""
        self.analyzer.close()
        self.dependency_analyzer.close()
        self.db.close()


def main():
    """Generate comprehensive reports when run directly."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate comprehensive Swift Package analysis reports"
    )
    parser.add_argument(
        "--output-dir", default="docs", help="Output directory for reports"
    )
    parser.add_argument(
        "--csv-limit",
        type=int,
        default=50,
        help="Number of repositories in priority CSV",
    )
    parser.add_argument(
        "--github-pages",
        action="store_true",
        help="Generate GitHub Pages compatible site",
    )

    args = parser.parse_args()

    generator = ReportGenerator()

    try:
        if args.github_pages:
            # Generate GitHub Pages site
            github_pages_path = generator.generate_github_pages_site(
                f"{args.output_dir}/index.html"
            )
            print(f"\n🌐 GitHub Pages site ready: {github_pages_path}")
            print("To deploy:")
            print("1. Commit the index.html file to your repository")
            print("2. Enable GitHub Pages in repository settings")
            print("3. Set source to main branch / root")
        else:
            # Generate priority CSV
            files = {}
            csv_path = generator.generate_priority_csv(
                f"{args.output_dir}/priority_analysis.csv", args.csv_limit
            )
            files["priority_csv"] = csv_path

            print("\n🎉 Report generation complete!")
            print("Generated files:")
            for report_type, file_path in files.items():
                print(f"  • {report_type}: {file_path}")

    finally:
        generator.close()


if __name__ == "__main__":
    main()

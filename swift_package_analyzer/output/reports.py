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
from jinja2 import Template

from swift_package_analyzer.analysis.analyzer import PackageAnalyzer
from swift_package_analyzer.core.models import Repository, SessionLocal
from swift_package_analyzer.analysis.dependencies import (
    DependencyTreeAnalyzer,
    DependencyVisualizer,
)


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

    def _generate_html_report(self, report_data: Dict, output_path: Path):
        """Generate an HTML report with embedded visualizations."""

        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Swift Package Android Compatibility Analysis Report</title>
    <meta charset="utf-8">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            line-height: 1.6; 
            color: #333; 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px; 
            background-color: #f8f9fa;
        }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 30px; 
            border-radius: 10px; 
            margin-bottom: 30px; 
            text-align: center;
        }
        .summary-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }
        .summary-card { 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
            border-left: 4px solid #667eea;
        }
        .metric-value { 
            font-size: 2em; 
            font-weight: bold; 
            color: #667eea; 
        }
        .section { 
            background: white; 
            margin: 20px 0; 
            padding: 25px; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }
        .priority-repo { 
            border: 1px solid #e9ecef; 
            margin: 10px 0; 
            padding: 15px; 
            border-radius: 5px; 
            background: #f8f9fa;
        }
        .repo-title { 
            font-weight: bold; 
            color: #495057; 
            font-size: 1.1em; 
        }
        .repo-stats { 
            color: #6c757d; 
            margin: 5px 0; 
        }
        .recommendation { 
            background: #e3f2fd; 
            border-left: 4px solid #2196f3; 
            padding: 10px 15px; 
            margin: 10px 0; 
            border-radius: 4px; 
        }
        h1, h2, h3 { color: #495057; }
        .generated-info { 
            text-align: center; 
            color: #6c757d; 
            font-size: 0.9em; 
            margin-top: 30px; 
            padding-top: 20px; 
            border-top: 1px solid #e9ecef; 
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Swift Package Android Compatibility Analysis</h1>
        <p>Comprehensive analysis of {{ report_data.metadata.total_repositories }} Swift packages</p>
        <p>Generated on {{ report_data.metadata.generated_at[:19] | replace('T', ' ') }}</p>
    </div>

    <div class="summary-grid">
        <div class="summary-card">
            <div class="metric-value">{{ report_data.statistics.total_analyzed }}</div>
            <div>Total Repositories Analyzed</div>
        </div>
        <div class="summary-card">
            <div class="metric-value">{{ "%.0f"|format(report_data.statistics.avg_stars) }}</div>
            <div>Average Stars per Repository</div>
        </div>
        <div class="summary-card">
        <div class="summary-card">
            <div class="metric-value">{{ report_data.statistics.primary_language }}</div>
            <div>Primary Programming Language</div>
        </div>
        <div class="summary-card">
            <div class="metric-value">{{ report_data.statistics.api_usage.total_api_calls }}</div>
            <div>GitHub API Calls Made</div>
        </div>
        <div class="summary-card">
            <div class="metric-value">{{ "%.1f"|format(report_data.statistics.api_usage.success_rate) }}%</div>
            <div>API Success Rate</div>
        </div>
    </div>

    <div class="section">
        <h2>📋 Executive Summary</h2>
        <p><strong>Overview:</strong> {{ report_data.executive_summary.overview }}</p>
        
        <h3>Key Metrics</h3>
        <ul>
            <li><strong>Average Popularity:</strong> {{ report_data.executive_summary.key_metrics.average_popularity }}</li>
            <li><strong>Most Popular Repository:</strong> {{ report_data.executive_summary.key_metrics.most_popular }}</li>
        </ul>

        <h3>🎯 Recommendations</h3>
        {% for rec in report_data.executive_summary.recommendations %}
        <div class="recommendation">{{ rec }}</div>
        {% endfor %}
    </div>

    <div class="section">
        <h2>🏆 Top Priority Repositories for Android Migration</h2>
        {% for repo in report_data.priority_repositories[:10] %}
        <div class="priority-repo">
            <div class="repo-title">{{ loop.index }}. {{ repo.owner }}/{{ repo.name }}</div>
            <div class="repo-stats">
                ⭐ {{ repo.stars }} stars | 🍴 {{ repo.forks }} forks | 📦 {{ repo.dependencies_count }} dependencies
            </div>
            <div class="repo-stats">
                Priority Score: {{ "%.3f"|format(repo.priority_score) }} | {{ repo.rationale }}
            </div>
            <div class="repo-stats">
                Package.swift: {{ "✅" if repo.has_package_swift else "❌" }} | 
                Swift Version: {{ repo.swift_tools_version or "Unknown" }}
            </div>
        </div>
        {% endfor %}
    </div>


    <div class="generated-info">
        <p>Report generated by {{ report_data.metadata.generation_tool }}</p>
        <p>For detailed data, see the accompanying JSON report and dependency visualization files.</p>
    </div>
</body>
</html>
        """

        template = Template(html_template)
        html_content = template.render(report_data=report_data)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)


    def generate_priority_csv(
        self, output_path: str = "exports/priority_analysis.csv", limit: int = 50
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

    def generate_github_pages_site(
        self, output_path: str = "exports/index.html"
    ) -> str:
        """Generate a single-file GitHub Pages compatible site."""
        from pathlib import Path
        import json

        print("🌐 Generating GitHub Pages site...")

        # Generate all analyses
        popularity = self.analyzer.generate_popularity_analysis()
        dependencies = self.analyzer.generate_dependency_analysis()
        languages = self.analyzer.generate_language_analysis()
        priorities = self.analyzer.generate_priority_analysis()

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
            "priority_repositories": priorities,  # All repositories for complete dataset
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

        # Load template
        template_path = (
            Path(__file__).parent.parent / "templates" / "github_pages_template.html"
        )
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # Embed data in template
        html_content = template_content.replace(
            "{{ EMBEDDED_DATA }}", json.dumps(web_data, default=str)
        )

        # Save the final file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        final_size_kb = output_file.stat().st_size / 1024
        print(f"✅ GitHub Pages site generated: {output_path}")
        print(f"📄 Final file size: {final_size_kb:.1f} KB")
        print(f"🚀 Ready for GitHub Pages deployment!")

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
        "--output-dir", default="exports", help="Output directory for reports"
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

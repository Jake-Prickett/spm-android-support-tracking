#!/usr/bin/env python3
"""
Analysis CLI - Extended commands for data analysis and visualization.
"""
import argparse
import json
import sys
from pathlib import Path

from swift_package_analyzer.analysis.analyzer import PackageAnalyzer
from swift_package_analyzer.output.reports import ReportGenerator
from swift_package_analyzer.analysis.dependencies import (
    DependencyTreeAnalyzer,
    DependencyVisualizer,
)


def generate_report(args):
    """Generate comprehensive analysis report."""
    from datetime import datetime

    analyzer = PackageAnalyzer()

    print("Generating report...")

    # Generate all analyses
    popularity = analyzer.generate_popularity_analysis()
    dependencies = analyzer.generate_dependency_analysis()
    languages = analyzer.generate_language_analysis()
    priorities = analyzer.generate_priority_analysis()

    # Combine into comprehensive report
    report_data = {
        "generated_at": datetime.now().isoformat(),
        "popularity_analysis": popularity,
        "dependency_analysis": dependencies,
        "language_analysis": languages,
        "priority_repositories": priorities[:20],  # Top 20 priorities
        "summary": {
            "total_repositories_analyzed": popularity.get("total_repositories", 0),
            "avg_stars": round(popularity.get("star_statistics", {}).get("mean", 0), 1),
            "primary_language": (
                max(
                    languages.get("language_distribution", {}).items(),
                    key=lambda x: x[1],
                )[0]
                if languages.get("language_distribution")
                else "Unknown"
            ),
        },
    }

    # Save report
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(report_data, f, indent=2, default=str)

    print(f"Report saved: {args.output}")

    # Print summary
    print("\n=== ANALYSIS SUMMARY ===")
    print(
        f"Total repositories: {report_data['summary']['total_repositories_analyzed']}"
    )
    print(f"Average stars: {report_data['summary']['avg_stars']}")
    print(f"Primary language: {report_data['summary']['primary_language']}")

    analyzer.close()


def generate_visualizations(args):
    """Generate visualization charts."""
    analyzer = PackageAnalyzer()

    print(f"Generating visualizations...")
    analyzer.generate_visualizations(args.output_dir)

    analyzer.close()


def generate_priorities(args):
    """Generate priority list for Android compatibility work."""
    analyzer = PackageAnalyzer()

    print("Analyzing priorities...")

    priority_list = analyzer.generate_priority_analysis()[: args.limit]

    # Save to file
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(priority_list, f, indent=2)

    # Display top priorities
    print(f"\n=== TOP {min(args.limit, len(priority_list))} PRIORITY REPOSITORIES ===")
    print(
        "(Ranked by popularity, community engagement, recent activity, and complexity)"
    )
    print()

    for i, repo in enumerate(priority_list, 1):
        print(f"{i:2d}. {repo['owner']}/{repo['name']}")
        print(
            f"    ⭐ {repo['stars']} stars | 🍴 {repo['forks']} forks | 📦 {repo['dependencies_count']} deps"
        )
        print(f"    Priority Score: {repo['priority_score']} | {repo['rationale']}")
        print(
            f"    Package.swift: {'✅' if repo['has_package_swift'] else '❌'} | Swift: {repo['swift_tools_version'] or 'Unknown'}"
        )
        print()

    print(f"Priority list saved: {args.output}")
    analyzer.close()


def show_stats(args):
    """Show quick statistics."""
    analyzer = PackageAnalyzer()

    popularity = analyzer.generate_popularity_analysis()
    dependencies = analyzer.generate_dependency_analysis()
    languages = analyzer.generate_language_analysis()

    if "error" in popularity:
        print("No data available")
        return

    print("=== QUICK STATISTICS ===")
    print(f"📊 Total Repositories: {popularity['total_repositories']}")
    print(f"⭐ Average Stars: {popularity['star_statistics']['mean']:.1f}")
    print(
        f"🔗 Average Dependencies: {dependencies['dependency_statistics']['mean_dependencies']:.1f}"
    )

    # API Usage statistics
    from swift_package_analyzer.core.models import ProcessingLog, SessionLocal

    db = SessionLocal()
    total_api_calls = (
        db.query(ProcessingLog).filter(ProcessingLog.action == "fetch_metadata").count()
    )
    successful_fetches = (
        db.query(ProcessingLog)
        .filter(
            ProcessingLog.action == "fetch_metadata", ProcessingLog.status == "success"
        )
        .count()
    )
    failed_fetches = (
        db.query(ProcessingLog)
        .filter(
            ProcessingLog.action == "fetch_metadata", ProcessingLog.status == "error"
        )
        .count()
    )

    if total_api_calls > 0:
        print(f"\n🌐 API Usage Summary:")
        print(f"   Total API calls made: {total_api_calls}")
        print(f"   Successful fetches: {successful_fetches}")
        print(f"   Failed fetches: {failed_fetches}")
        success_rate = (successful_fetches / total_api_calls) * 100
        print(f"   Success rate: {success_rate:.1f}%")
        if popularity["total_repositories"] > 0:
            avg_calls = total_api_calls / popularity["total_repositories"]
            print(f"   Average calls per package: {avg_calls:.1f}")

    db.close()

    # Top repositories
    print("\n🏆 Most Popular Repositories:")
    for i, repo in enumerate(popularity["star_statistics"]["top_10"][:5], 1):
        print(f"  {i}. {repo['owner']}/{repo['name']} ({repo['stars']} ⭐)")

    # Language distribution
    print("\n💻 Language Distribution:")
    for lang, count in list(languages["language_distribution"].items())[:5]:
        percentage = (count / popularity["total_repositories"]) * 100
        print(f"  {lang}: {count} ({percentage:.1f}%)")

    analyzer.close()


def generate_comprehensive_report(args):
    """Generate comprehensive report with multiple formats."""
    generator = ReportGenerator()

    try:
        files = generator.generate_comprehensive_report(args.output_dir)

        # Also generate priority CSV
        csv_path = generator.generate_priority_csv(
            f"{args.output_dir}/priority_analysis.csv", getattr(args, "csv_limit", 50)
        )
        files["priority_csv"] = csv_path

        print("\nGenerated files:")
        for report_type, file_path in files.items():
            print(f"  • {report_type}: {file_path}")

    finally:
        generator.close()


def analyze_dependencies(args):
    """Analyze package dependencies and generate visualizations."""
    analyzer = DependencyTreeAnalyzer()
    visualizer = DependencyVisualizer(analyzer)

    try:
        print("Building dependency tree...")
        analyzer.build_dependency_tree()

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print("Generating impact analysis...")
        impact_analysis = analyzer.get_impact_analysis()

        # Save impact analysis
        with open(output_dir / "impact_analysis.json", "w") as f:
            json.dump(impact_analysis, f, indent=2)
        print(f"Impact analysis: {output_dir / 'impact_analysis.json'}")

        print("Generating network visualization...")
        network_path = visualizer.generate_dependency_network_visualization(
            str(output_dir / "dependency_network.html"), args.max_nodes
        )

        # Generate tree visualization for specific package if requested
        if args.package:
            print(f"Generating tree for {args.package}...")
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
            print(
                f"     ⭐ {pkg['stars']} stars | 👥 {pkg['direct_dependents']} direct dependents"
            )

        print(f"\nAnalysis complete: {output_dir}")

    finally:
        analyzer.close()


def generate_github_pages(args):
    """Generate GitHub Pages compatible site."""
    generator = ReportGenerator()

    try:
        github_pages_path = generator.generate_github_pages_site(
            f"{args.output_dir}/index.html"
        )

        print(f"\nGitHub Pages site: {github_pages_path}")

    finally:
        generator.close()


def main():
    """Main analysis CLI entry point with argparse."""
    parser = argparse.ArgumentParser(
        description="Swift Package Analysis and Visualization CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate analysis report")
    report_parser.add_argument(
        "--output",
        default="exports/analysis_report.json",
        help="Output file for analysis report",
    )
    report_parser.set_defaults(func=generate_report)

    # Visualize command
    viz_parser = subparsers.add_parser(
        "visualize", help="Generate visualization charts"
    )
    viz_parser.add_argument(
        "--output-dir",
        default="exports/visualizations",
        help="Directory for visualization outputs",
    )
    viz_parser.set_defaults(func=generate_visualizations)

    # Priorities command
    priorities_parser = subparsers.add_parser(
        "priorities", help="Generate priority rankings"
    )
    priorities_parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Number of top priority repositories to show",
    )
    priorities_parser.add_argument(
        "--output",
        default="exports/priority_list.json",
        help="Output file for priority list",
    )
    priorities_parser.set_defaults(func=generate_priorities)

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show quick statistics")
    stats_parser.set_defaults(func=show_stats)

    # Comprehensive report command
    comp_parser = subparsers.add_parser(
        "comprehensive", help="Generate multi-format reports"
    )
    comp_parser.add_argument(
        "--output-dir",
        default="exports",
        help="Output directory for comprehensive reports",
    )
    comp_parser.add_argument(
        "--csv-limit",
        type=int,
        default=50,
        help="Number of repositories in priority CSV",
    )
    comp_parser.set_defaults(func=generate_comprehensive_report)

    # Dependencies command
    deps_parser = subparsers.add_parser(
        "dependencies", help="Analyze package dependencies"
    )
    deps_parser.add_argument(
        "--output-dir",
        default="exports/dependencies",
        help="Output directory for dependency analysis",
    )
    deps_parser.add_argument(
        "--package", help="Specific package to analyze (owner/repo format)"
    )
    deps_parser.add_argument(
        "--max-nodes",
        type=int,
        default=100,
        help="Maximum nodes in network visualization",
    )
    deps_parser.add_argument(
        "--max-depth", type=int, default=3, help="Maximum depth for tree analysis"
    )
    deps_parser.set_defaults(func=analyze_dependencies)

    # GitHub Pages command
    pages_parser = subparsers.add_parser("github-pages", help="Generate web-ready site")
    pages_parser.add_argument(
        "--output-dir", default="exports", help="Output directory for GitHub Pages site"
    )
    pages_parser.set_defaults(func=generate_github_pages)

    # Parse arguments and run appropriate function
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()

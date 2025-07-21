#!/usr/bin/env python3
"""
Analysis CLI - Extended commands for data analysis and visualization.
"""
import json
from pathlib import Path

import click

from analyzer import PackageAnalyzer


@click.group()
def analyze():
    """Analysis and visualization commands."""
    pass


@analyze.command()
@click.option(
    "--output",
    default="exports/analysis_report.json",
    help="Output file for analysis report",
)
def report(output):
    """Generate comprehensive analysis report."""
    analyzer = PackageAnalyzer()

    click.echo("Generating analysis report...")

    # Generate all analyses
    popularity = analyzer.generate_popularity_analysis()
    dependencies = analyzer.generate_dependency_analysis()
    languages = analyzer.generate_language_analysis()
    priorities = analyzer.generate_priority_analysis()

    # Combine into comprehensive report
    report_data = {
        "generated_at": click.DateTime().convert(
            click.get_current_context(), None, None
        ),
        "popularity_analysis": popularity,
        "dependency_analysis": dependencies,
        "language_analysis": languages,
        "priority_repositories": priorities[:20],  # Top 20 priorities
        "summary": {
            "total_repositories_analyzed": popularity.get("total_repositories", 0),
            "avg_stars": round(popularity.get("star_statistics", {}).get("mean", 0), 1),
            "package_swift_coverage": dependencies.get(
                "package_swift_coverage", {}
            ).get("coverage_percentage", 0),
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
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(report_data, f, indent=2, default=str)

    click.echo(f"Analysis report saved to {output}")

    # Print summary
    click.echo("\n=== ANALYSIS SUMMARY ===")
    click.echo(
        f"Total repositories: {report_data['summary']['total_repositories_analyzed']}"
    )
    click.echo(f"Average stars: {report_data['summary']['avg_stars']}")
    click.echo(
        f"Package.swift coverage: {report_data['summary']['package_swift_coverage']:.1f}%"
    )
    click.echo(f"Primary language: {report_data['summary']['primary_language']}")

    analyzer.close()


@analyze.command()
@click.option(
    "--output-dir",
    default="exports/visualizations",
    help="Directory for visualization outputs",
)
def visualize(output_dir):
    """Generate visualization charts."""
    analyzer = PackageAnalyzer()

    click.echo(f"Generating visualizations in {output_dir}...")
    analyzer.generate_visualizations(output_dir)

    analyzer.close()


@analyze.command()
@click.option("--limit", default=25, help="Number of top priority repositories to show")
@click.option(
    "--output",
    default="exports/priority_list.json",
    help="Output file for priority list",
)
def priorities(limit, output):
    """Generate priority list for Android compatibility work."""
    analyzer = PackageAnalyzer()

    click.echo("Analyzing repository priorities...")

    priority_list = analyzer.generate_priority_analysis()[:limit]

    # Save to file
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        json.dump(priority_list, f, indent=2)

    # Display top priorities
    click.echo(f"\n=== TOP {min(limit, len(priority_list))} PRIORITY REPOSITORIES ===")
    click.echo(
        "(Ranked by popularity, community engagement, recent activity, and complexity)"
    )
    click.echo()

    for i, repo in enumerate(priority_list, 1):
        click.echo(f"{i:2d}. {repo['owner']}/{repo['name']}")
        click.echo(
            f"    ⭐ {repo['stars']} stars | 🍴 {repo['forks']} forks | 📦 {repo['dependencies_count']} deps"
        )
        click.echo(
            f"    Priority Score: {repo['priority_score']} | {repo['rationale']}"
        )
        click.echo(
            f"    Package.swift: {'✅' if repo['has_package_swift'] else '❌'} | Swift: {repo['swift_tools_version'] or 'Unknown'}"
        )
        click.echo()

    click.echo(f"Full priority list saved to {output}")
    analyzer.close()


@analyze.command()
def stats():
    """Show quick statistics."""
    analyzer = PackageAnalyzer()

    popularity = analyzer.generate_popularity_analysis()
    dependencies = analyzer.generate_dependency_analysis()
    languages = analyzer.generate_language_analysis()

    if "error" in popularity:
        click.echo("No data available for analysis!")
        return

    click.echo("=== QUICK STATISTICS ===")
    click.echo(f"📊 Total Repositories: {popularity['total_repositories']}")
    click.echo(f"⭐ Average Stars: {popularity['star_statistics']['mean']:.1f}")
    click.echo(
        f"📦 Package.swift Coverage: {dependencies['package_swift_coverage']['coverage_percentage']:.1f}%"
    )
    click.echo(
        f"🔗 Average Dependencies: {dependencies['dependency_statistics']['mean_dependencies']:.1f}"
    )

    # Top repositories
    click.echo("\n🏆 Most Popular Repositories:")
    for i, repo in enumerate(popularity["star_statistics"]["top_10"][:5], 1):
        click.echo(f"  {i}. {repo['owner']}/{repo['name']} ({repo['stars']} ⭐)")

    # Language distribution
    click.echo("\n💻 Language Distribution:")
    for lang, count in list(languages["language_distribution"].items())[:5]:
        percentage = (count / popularity["total_repositories"]) * 100
        click.echo(f"  {lang}: {count} ({percentage:.1f}%)")

    analyzer.close()


if __name__ == "__main__":
    analyze()

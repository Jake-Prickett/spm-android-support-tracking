#!/usr/bin/env python3
"""
Swift Package Analyzer - Unified CLI
Simplified command-line interface for Swift package Android migration analysis.
"""

import argparse
import json
import sys
from pathlib import Path

from swift_package_analyzer.core.config import config
from swift_package_analyzer.cli.main import (
    init_database,
    show_status,
    export_data,
    set_package_state,
    list_states,
)
from swift_package_analyzer.data.fetcher import DataProcessor
from swift_package_analyzer.analysis.analyzer import PackageAnalyzer
from swift_package_analyzer.analysis.dependencies import DependencyTreeAnalyzer
from swift_package_analyzer.output.reports import ReportGenerator


def setup_command(args):
    """Initialize database and environment."""
    print("Setting up Swift Package Analyzer...")
    init_database(args)

    if not config.github_token:
        print("\nRecommendation: Add GitHub token to .env file for higher API limits")
        print("Without token: 60 requests/hour | With token: 5000 requests/hour")
        print("Get token at: https://github.com/settings/tokens")


def collect_command(args):
    """Fetch repository data using simplified chunked processing."""
    # Apply smart defaults
    if args.test:
        args.batch_size = 3
        print("Running test collection (3 repositories)")
    elif not config.github_token and args.batch_size == config.repositories_per_batch:
        # Reduce batch size if using default with no token
        args.batch_size = 5
        print(f"Using reduced batch size: {args.batch_size} (no GitHub token)")
    else:
        print(f"Using batch size: {args.batch_size}")

    print("Running simplified chunked data collection...")

    processor = DataProcessor()
    urls = processor.load_csv_repositories()

    if not urls:
        print("No repositories found in source data")
        return

    # Process chunk (batch_size determines chunk size)
    results = processor.process_chunk(urls, chunk_size=args.batch_size)

    processor.close()

    print(f"\nChunked collection completed:")
    print(f"  Processed: {results.get('processed', 0)} repositories")
    print(f"  Success: {results['success']}")
    print(f"  Errors: {results['error']}")
    print(f"  Total available: {results.get('total_available', 0)}")

    if results.get("processed", 0) > 0:
        print(
            f"  Success rate: {(results['success'] / results.get('processed', 1)) * 100:.1f}%"
        )

    # Show freshness status
    status = processor.get_refresh_status()
    print(f"\nRepository freshness:")
    print(f"  Fresh (< 1 day): {status['freshness']['fresh_1_day']}")
    print(f"  Recent (1-7 days): {status['freshness']['recent_1_week']}")
    print(f"  Stale (> 7 days): {status['freshness']['stale_older']}")
    print(f"  Never fetched: {status['freshness']['never_fetched']}")

    # Show updated status
    print("\nUpdated repository status:")
    show_status(args)


def analyze_command(args):
    """Generate comprehensive analysis, reports, and exports."""
    # Set output directory default
    if not hasattr(args, "output_dir") or not args.output_dir:
        args.output_dir = "docs"

    print("Running comprehensive analysis with all outputs...")

    analyzer = PackageAnalyzer()
    dependency_analyzer = DependencyTreeAnalyzer()
    generator = ReportGenerator()

    try:
        # Show current statistics
        print("\nCurrent Statistics:")
        popularity = analyzer.generate_popularity_analysis()
        if "error" not in popularity:
            print(f"📊 Total Repositories: {popularity['total_repositories']}")
            print(f"⭐ Average Stars: {popularity['star_statistics']['mean']:.1f}")

        # Generate dependency analysis
        print("\nAnalyzing dependencies...")
        dependency_analyzer.build_dependency_tree()
        impact_analysis = dependency_analyzer.get_impact_analysis()
        
        # Save impact analysis
        deps_output_dir = Path(f"{args.output_dir}/dependencies")
        deps_output_dir.mkdir(parents=True, exist_ok=True)
        with open(deps_output_dir / "impact_analysis.json", "w") as f:
            json.dump(impact_analysis, f, indent=2)
        

        # Generate web-ready site
        print("\nGenerating web-ready site...")
        generator.generate_github_pages_site(f"{args.output_dir}/index.html")

        # Export data in both formats
        print("\nExporting data...")
        
        # Export CSV
        csv_args = argparse.Namespace(
            format="csv", output=f"{args.output_dir}/swift_packages.csv"
        )
        export_data(csv_args)

        # Export JSON
        json_args = argparse.Namespace(
            format="json", output=f"{args.output_dir}/swift_packages.json"
        )
        export_data(json_args)

        print(f"\nAnalysis complete! All outputs available in: {args.output_dir}/")
        print(f"Web site ready at: {args.output_dir}/index.html")

    finally:
        analyzer.close()
        dependency_analyzer.close()
        generator.close()


def status_command(args):
    """Show processing status and statistics."""
    show_status(args)


def set_state_command(args):
    """Set package migration state."""
    set_package_state(args)


def list_states_command(args):
    """List available package states."""
    list_states(args)


def main():
    """Main CLI entry point with flag-based commands."""
    parser = argparse.ArgumentParser(
        prog="swift-analyzer",
        description="Swift Package Android Migration Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  swift-analyzer --setup                              # One-time setup
  swift-analyzer --collect                            # Fetch data with smart chunked processing
  swift-analyzer --collect --test                     # Test with small batch
  swift-analyzer --collect --batch-size 250           # Large batch refresh
  swift-analyzer --analyze                            # Generate all analysis and exports
  swift-analyzer --status                             # Check processing status
  
  swift-analyzer --list-states                        # Show available package states
  swift-analyzer --set-state --owner apple --name swift-format --state migrated --reason "Successfully ported"
  swift-analyzer --set-state --url https://github.com/apple/swift-format --state in_progress

State Management:
  Available states: unknown, tracking, in_progress, migrated, archived, irrelevant, blocked, dependency
  Use --list-states to see descriptions and current distribution.

Automation:
  Collection automatically processes the oldest repositories first, providing a simple
  refresh mechanism suitable for nightly automation (~4 day refresh cycle at 250 repos/night).
        """,
    )

    # Command flags (mutually exclusive)
    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument(
        "--setup", action="store_true", help="Initialize database and environment"
    )
    command_group.add_argument(
        "--collect", action="store_true", help="Fetch repository data from GitHub"
    )
    command_group.add_argument(
        "--analyze",
        action="store_true",
        help="Generate comprehensive analysis, reports, and exports",
    )
    command_group.add_argument(
        "--status",
        action="store_true",
        help="Show processing status and database statistics",
    )
    command_group.add_argument(
        "--set-state",
        action="store_true",
        help="Set migration state for a package",
    )
    command_group.add_argument(
        "--list-states",
        action="store_true",
        help="List available package states",
    )

    # Collect options
    parser.add_argument(
        "--batch-size",
        type=int,
        default=config.repositories_per_batch,
        help=f"Repositories per batch (default: {config.repositories_per_batch})",
    )
    parser.add_argument(
        "--test", action="store_true", help="Run small test batch (3 repositories)"
    )

    # Analyze options
    parser.add_argument(
        "--output-dir",
        default="docs",
        help="Output directory for all outputs (default: docs)",
    )

    # State management options
    parser.add_argument(
        "--state",
        help="Package state to set (use --list-states to see available states)",
    )
    parser.add_argument(
        "--url",
        help="Repository URL to update",
    )
    parser.add_argument(
        "--owner",
        help="Repository owner (use with --name)",
    )
    parser.add_argument(
        "--name",
        help="Repository name (use with --owner)",
    )
    parser.add_argument(
        "--reason",
        help="Reason for state change",
    )

    # Parse arguments and run appropriate function
    args = parser.parse_args()

    # Execute the appropriate command
    try:
        if args.setup:
            setup_command(args)
        elif args.collect:
            collect_command(args)
        elif args.analyze:
            analyze_command(args)
        elif args.status:
            status_command(args)
        elif args.set_state:
            set_state_command(args)
        elif args.list_states:
            list_states_command(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

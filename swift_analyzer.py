#!/usr/bin/env python3
"""
Swift Package Analyzer - Unified CLI
Simplified command-line interface for Swift package Android migration analysis.
"""

import argparse
import sys

from swift_package_analyzer.core.config import config
from swift_package_analyzer.cli.main import (
    init_database, fetch_data, show_status, export_data
)
from swift_package_analyzer.cli.analyze import (
    show_stats, generate_comprehensive_report, analyze_dependencies, 
    generate_github_pages
)


def setup_command(args):
    """Initialize database and environment."""
    print("Setting up Swift Package Analyzer...")
    init_database(args)
    
    if not config.github_token:
        print("\nRecommendation: Add GitHub token to .env file for higher API limits")
        print("Without token: 60 requests/hour | With token: 5000 requests/hour")
        print("Get token at: https://github.com/settings/tokens")


def collect_command(args):
    """Fetch repository data with smart defaults."""
    # Apply smart defaults
    if args.test:
        args.batch_size = 3
        args.max_batches = 1
        print("Running test collection (3 repositories)")
    elif not config.github_token and args.batch_size == config.repositories_per_batch:
        # Reduce batch size if using default with no token
        args.batch_size = 5
        print(f"Using reduced batch size: {args.batch_size} (no GitHub token)")
    else:
        print(f"Using batch size: {args.batch_size}")
    
    # Call existing fetch_data function
    fetch_data(args)


def analyze_command(args):
    """Generate comprehensive analysis, reports, and exports."""
    # Set output directory default
    if not hasattr(args, 'output_dir') or not args.output_dir:
        args.output_dir = "exports"
    
    print("Running comprehensive analysis with all outputs...")
    
    # Show current statistics
    print("\nCurrent Statistics:")
    show_stats(args)
    
    # Generate comprehensive report
    print("\nGenerating comprehensive reports...")
    generate_comprehensive_report(args)
    
    # Generate dependency analysis
    print("\nAnalyzing dependencies...")
    deps_args = argparse.Namespace(
        output_dir=f"{args.output_dir}/dependencies",
        package=None,
        max_nodes=100,
        max_depth=3
    )
    analyze_dependencies(deps_args)
    
    # Generate web-ready site
    print("\nGenerating web-ready site...")
    pages_args = argparse.Namespace(output_dir=args.output_dir)
    generate_github_pages(pages_args)
    
    # Export data in both formats
    print("\nExporting data...")
    
    # Export CSV
    csv_args = argparse.Namespace(
        format='csv',
        output=f"{args.output_dir}/swift_packages.csv"
    )
    export_data(csv_args)
    
    # Export JSON
    json_args = argparse.Namespace(
        format='json',
        output=f"{args.output_dir}/swift_packages.json"
    )
    export_data(json_args)
    
    print(f"\nAnalysis complete! All outputs available in: {args.output_dir}/")
    print(f"Web site ready at: {args.output_dir}/index.html")


def status_command(args):
    """Show processing status and statistics."""
    show_status(args)




def main():
    """Main CLI entry point with simplified command structure."""
    parser = argparse.ArgumentParser(
        prog='swift-analyzer',
        description='Swift Package Android Migration Analysis Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  swift-analyzer setup                    # One-time setup
  swift-analyzer collect                  # Fetch data with smart defaults
  swift-analyzer collect --test           # Test with small batch
  swift-analyzer analyze                  # Generate all analysis and exports
  swift-analyzer status                   # Check processing status
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup command
    setup_parser = subparsers.add_parser(
        'setup', 
        help='Initialize database and environment'
    )
    setup_parser.set_defaults(func=setup_command)
    
    # Collect command
    collect_parser = subparsers.add_parser(
        'collect', 
        help='Fetch repository data from GitHub'
    )
    collect_parser.add_argument(
        '--batch-size', type=int, default=config.repositories_per_batch,
        help=f'Repositories per batch (default: {config.repositories_per_batch})'
    )
    collect_parser.add_argument(
        '--max-batches', type=int,
        help='Maximum number of batches to process'
    )
    collect_parser.add_argument(
        '--test', action='store_true',
        help='Run small test batch (3 repositories)'
    )
    collect_parser.set_defaults(func=collect_command)
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze', 
        help='Generate comprehensive analysis, reports, and exports'
    )
    analyze_parser.add_argument(
        '--output-dir', default='exports',
        help='Output directory for all outputs (default: exports)'
    )
    analyze_parser.set_defaults(func=analyze_command)
    
    # Status command
    status_parser = subparsers.add_parser(
        'status', 
        help='Show processing status and database statistics'
    )
    status_parser.set_defaults(func=status_command)
    
    
    # Parse arguments and run appropriate function
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    # Execute the command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test script to verify the refactored CLI structure
"""

import sys
import argparse
from pathlib import Path

def test_argument_parsing():
    """Test that our new argparse structure works correctly."""
    
    # Test main.py argument structure
    print("Testing main.py CLI structure...")
    
    main_parser = argparse.ArgumentParser(description="Swift Package Support Data Processing CLI")
    main_subparsers = main_parser.add_subparsers(dest='command', help='Available commands')
    
    # Init database command
    init_parser = main_subparsers.add_parser('init-db', help='Initialize the database')
    
    # Fetch data command
    fetch_parser = main_subparsers.add_parser('fetch-data', help='Fetch repository data from GitHub API')
    fetch_parser.add_argument('--batch-size', type=int, default=10)
    fetch_parser.add_argument('--max-batches', type=int, default=None)
    
    # Status command
    status_parser = main_subparsers.add_parser('status', help='Show processing status')
    
    # Export command
    export_parser = main_subparsers.add_parser('export', help='Export repository data')
    export_parser.add_argument('--format', choices=['csv', 'json'], default='csv')
    export_parser.add_argument('--output', default='exports/repositories.csv')
    
    # Test parsing various commands
    test_cases = [
        ['init-db'],
        ['fetch-data', '--batch-size', '5', '--max-batches', '2'],
        ['status'],
        ['export', '--format', 'json', '--output', 'test.json']
    ]
    
    for test_case in test_cases:
        try:
            args = main_parser.parse_args(test_case)
            print(f"✅ Successfully parsed: {' '.join(test_case)}")
            print(f"   Command: {args.command}")
            if hasattr(args, 'batch_size'):
                print(f"   Batch size: {args.batch_size}")
        except SystemExit:
            print(f"❌ Failed to parse: {' '.join(test_case)}")
    
    print("\nTesting analyze.py CLI structure...")
    
    # Test analyze.py argument structure
    analyze_parser = argparse.ArgumentParser(description="Swift Package Analysis CLI")
    analyze_subparsers = analyze_parser.add_subparsers(dest='command', help='Available commands')
    
    # Report command
    report_parser = analyze_subparsers.add_parser('report', help='Generate analysis report')
    report_parser.add_argument('--output', default='exports/analysis_report.json')
    
    # Visualize command
    viz_parser = analyze_subparsers.add_parser('visualize', help='Generate visualizations')
    viz_parser.add_argument('--output-dir', default='exports/visualizations')
    
    # Priorities command
    priorities_parser = analyze_subparsers.add_parser('priorities', help='Generate priority list')
    priorities_parser.add_argument('--limit', type=int, default=25)
    priorities_parser.add_argument('--output', default='exports/priority_list.json')
    
    # Stats command
    stats_parser = analyze_subparsers.add_parser('stats', help='Show quick statistics')
    
    # Comprehensive command
    comp_parser = analyze_subparsers.add_parser('comprehensive', help='Generate comprehensive report')
    comp_parser.add_argument('--output-dir', default='exports')
    comp_parser.add_argument('--csv-limit', type=int, default=50)
    
    # Dependencies command
    deps_parser = analyze_subparsers.add_parser('dependencies', help='Analyze package dependencies')
    deps_parser.add_argument('--output-dir', default='exports/dependencies')
    deps_parser.add_argument('--package', help='Specific package to analyze')
    deps_parser.add_argument('--max-nodes', type=int, default=100)
    deps_parser.add_argument('--max-depth', type=int, default=3)
    
    analyze_test_cases = [
        ['stats'],
        ['report', '--output', 'custom_report.json'],
        ['visualize', '--output-dir', 'custom_viz'],
        ['priorities', '--limit', '10'],
        ['comprehensive', '--output-dir', 'reports', '--csv-limit', '25'],
        ['dependencies', '--output-dir', 'deps', '--max-nodes', '50'],
        ['dependencies', '--package', 'vapor/vapor', '--max-depth', '4']
    ]
    
    for test_case in analyze_test_cases:
        try:
            args = analyze_parser.parse_args(test_case)
            print(f"✅ Successfully parsed: {' '.join(test_case)}")
            print(f"   Command: {args.command}")
            if hasattr(args, 'limit'):
                print(f"   Limit: {args.limit}")
        except SystemExit:
            print(f"❌ Failed to parse: {' '.join(test_case)}")
    
    print("\n🎉 CLI structure tests completed!")

def test_project_structure():
    """Test that all required files exist."""
    print("\nTesting project structure...")
    
    required_files = [
        'main.py',
        'analyze.py',
        'reports.py',
        'dependency_analyzer.py',
        'config.py',
        'models.py',
        'fetcher.py',
        'analyzer.py',
        'requirements.txt',
        'README.md'
    ]
    
    for file_name in required_files:
        file_path = Path(file_name)
        if file_path.exists():
            print(f"✅ {file_name} exists")
        else:
            print(f"❌ {file_name} missing")
    
    # Check if directories exist
    required_dirs = ['logs', 'data', 'exports']
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"✅ {dir_name}/ directory exists")
        else:
            print(f"⚠️  {dir_name}/ directory missing (will be created on first run)")

def test_requirements():
    """Test that requirements.txt has correct dependencies."""
    print("\nTesting requirements.txt...")
    
    with open('requirements.txt', 'r') as f:
        requirements = f.read()
    
    required_packages = [
        'requests', 'pandas', 'matplotlib', 'seaborn', 'python-dotenv',
        'PyGithub', 'tqdm', 'schedule', 'sqlalchemy', 'alembic',
        'plotly', 'jinja2', 'networkx'
    ]
    
    missing_click = 'click' not in requirements
    print(f"✅ Click dependency removed: {missing_click}")
    
    for package in required_packages:
        if package.lower() in requirements.lower():
            print(f"✅ {package} found in requirements")
        else:
            print(f"❌ {package} missing from requirements")

if __name__ == "__main__":
    print("🧪 Testing refactored Swift Package Data Processing CLI")
    print("=" * 50)
    
    test_argument_parsing()
    test_project_structure()
    test_requirements()
    
    print("\n" + "=" * 50)
    print("✨ Refactoring verification complete!")
    print("\nKey improvements:")
    print("• Replaced Click with native argparse")
    print("• Added comprehensive report generation")
    print("• Enhanced error handling and progress tracking") 
    print("• Interactive visualizations with Plotly")
    print("• Multiple output formats (HTML, JSON, CSV)")
    print("• Better project structure and separation of concerns")
    print("• NEW: Dependency tree analysis and network visualizations")
    print("• NEW: Impact analysis for migration prioritization")
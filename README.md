# Swift Package Support Data Processing

This repository contains tools for analyzing Swift Packages that currently support Linux but not Android, helping prioritize work for the Swift Android Working Group.

## About This Project

This project processes the **847 Swift packages** listed in `linux-compatible-android-incompatible.csv` - packages that currently run on Linux but lack Android support. The data comes from Swift Package Index URLs and helps identify which packages would have the highest impact if migrated to Android compatibility.

## Overview

The goal is to build a comprehensive database of Swift packages to:
- 📊 Analyze repository popularity and community engagement from GitHub
- 🔍 Identify high-impact packages for Android compatibility work
- 📈 Track migration progress and dependency relationships
- 🎯 Prioritize efforts based on data-driven insights from real usage metrics

## ✨ New Features (Refactored Version)

- **🚀 Enhanced CLI**: Replaced Click with native argparse for simpler dependencies
- **📊 Rich Reports**: Generate HTML, JSON, and interactive visualizations
- **⚡ Better Performance**: Improved error handling and progress tracking
- **📈 Interactive Charts**: Plotly-based visualizations with hover data
- **🔄 Comprehensive Logging**: Detailed processing statistics and error tracking
- **📋 Multiple Formats**: Export data in CSV, JSON, and HTML formats
- **🕸️ Dependency Analysis**: Network graphs and tree visualizations of package dependencies
- **🎯 Impact Analysis**: Identify which packages unlock the most others when migrated

## Features

- **Swift Package Index Integration**: Processes URLs from Swift Package Index format
- **Automated Data Collection**: Fetch repository metadata from GitHub API with intelligent rate limiting
- **Local SQLite Database**: Efficient local storage for 800+ repositories and analysis
- **Package.swift Parsing**: Extract dependencies and Swift tools versions automatically
- **Priority Scoring**: Multi-factor algorithm to rank repositories by migration value
- **Rich Visualizations**: Generate charts and reports for actionable insights
- **Batch Processing**: Respect GitHub API limits while processing hundreds of repositories
- **Progress Tracking**: Real-time progress bars and comprehensive statistics

## Quick Start

### 1. Setup Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template and add GitHub token
cp .env.example .env
# Edit .env with your GitHub token from: https://github.com/settings/tokens
# Required scope: public_repo (for reading public repositories)
```

### 2. Initialize Database

```bash
python main.py init-db
```

### 3. Process Repository Data

```bash
# Start with a small test batch (5 repos)
python main.py fetch-data --batch-size 5 --max-batches 1

# Process more repositories (50 repos over 5 batches)
python main.py fetch-data --batch-size 10 --max-batches 5

# For continuous processing of all 847 repositories:
python main.py fetch-data
# This will process all repos in the CSV, respecting rate limits
```

### 4. Generate Analysis & Insights

```bash
# Quick overview statistics
python analyze.py stats

# Generate comprehensive report with HTML, JSON, and interactive charts
python analyze.py comprehensive --output-dir exports

# NEW: Analyze package dependencies and generate network visualizations
python analyze.py dependencies --output-dir exports/dependencies

# Generate specific analysis types
python analyze.py report --output exports/analysis_report.json
python analyze.py visualize --output-dir exports/visualizations
python analyze.py priorities --limit 25 --output exports/priority_list.json
```

## New CLI Structure

### Main Commands (`main.py`)

```bash
# Initialize database
python main.py init-db

# Fetch repository data with enhanced progress tracking
python main.py fetch-data [--batch-size N] [--max-batches N]

# Show detailed processing status
python main.py status

# Export data in multiple formats
python main.py export [--format csv|json] [--output path]

# Run scheduled processing
python main.py schedule-runner
```

### Analysis Commands (`analyze.py`)

```bash
# Quick statistics overview
python analyze.py stats

# Generate comprehensive report (HTML + JSON + Interactive Charts)
python analyze.py comprehensive [--output-dir path] [--csv-limit N]

# Generate specific report types
python analyze.py report [--output path]              # JSON analysis report
python analyze.py visualize [--output-dir path]       # Static visualizations
python analyze.py priorities [--limit N] [--output path]  # Priority analysis
python analyze.py dependencies [--output-dir path]    # NEW: Dependency analysis
```

### Enhanced Report Generation (`reports.py`)

```bash
# Generate comprehensive reports directly
python reports.py [--output-dir exports] [--csv-limit 50]
```

## Project Structure

```
├── main.py                 # Main CLI interface (refactored with argparse)
├── analyze.py              # Analysis and visualization CLI (enhanced)
├── reports.py              # NEW: Comprehensive report generation
├── dependency_analyzer.py  # NEW: Dependency tree analysis and visualization
├── config.py               # Configuration management
├── models.py               # Database models (SQLAlchemy)
├── fetcher.py              # GitHub API data fetching (enhanced error handling)
├── analyzer.py             # Data analysis and visualization
├── requirements.txt        # Python dependencies (Click removed, Plotly+NetworkX added)
├── .env.example           # Environment template
├── logs/                  # Application logs
├── data/                  # Raw data files
└── exports/               # Generated reports and visualizations
    ├── comprehensive_report.html     # NEW: Rich HTML report
    ├── comprehensive_report.json     # Enhanced JSON report
    ├── priority_analysis.csv        # NEW: Detailed CSV export
    ├── interactive_charts/           # NEW: Interactive Plotly charts
    │   ├── stars_vs_forks.html
    │   ├── language_distribution.html
    │   ├── priority_repositories.html
    │   └── dependencies_histogram.html
    └── dependency_visualizations/    # NEW: Dependency analysis outputs
        ├── dependency_network.html   # Interactive network graph
        ├── dependency_impact.json    # Impact analysis data
        └── dependency_tree_[package].html  # Individual tree visualizations
```

## New Output Formats

### 1. HTML Reports
Rich, styled HTML reports with:
- Executive summary with key metrics
- Visual metric cards
- Top priority repositories with detailed information
- Language distribution grid
- Professional styling and responsive design

### 2. Interactive Visualizations
Plotly-based charts with:
- **Stars vs Forks Scatter Plot**: Interactive exploration of repository popularity
- **Language Distribution Pie Chart**: Hover data showing exact counts
- **Priority Repositories Bar Chart**: Top repositories ranked by migration priority
- **Dependencies Histogram**: Distribution of package complexity

### 3. Enhanced CSV Export
Detailed CSV files with:
- Priority scores and rationale
- Direct GitHub and Package Index URLs
- Comprehensive metadata for spreadsheet analysis

### 4. JSON Reports
Structured JSON data with:
- Executive summary and recommendations
- Complete analysis datasets
- Metadata and generation timestamps
- Easy integration with other tools

### 5. 🆕 Dependency Analysis Visualizations
Advanced dependency relationship analysis:

#### Interactive Network Graphs
- **Package Dependency Networks**: Interactive network showing how packages depend on each other
- **Node Sizing**: Proportional to GitHub stars (popularity indicator)
- **Color Coding**: Green (Android-compatible), Orange (Linux-only), Red (Neither)
- **Hover Information**: Detailed package metadata and impact metrics
- **Zoom & Pan**: Explore large dependency networks interactively

#### Dependency Tree Visualizations
- **Hierarchical Trees**: Visual representation of dependency hierarchies
- **Depth Analysis**: Maximum dependency depth for each package
- **Impact Metrics**: Shows how many packages would be unlocked by migration
- **Compatibility Status**: Visual indicators for platform support

#### Impact Analysis Reports
- **Direct Dependents**: Packages that directly depend on each package
- **Indirect Impact**: Total packages that would benefit from migration
- **Foundational Packages**: High-impact packages that unlock many others
- **Migration Priority**: Data-driven prioritization based on dependency relationships

## Enhanced Error Handling & Logging

### Improved GitHub API Integration
- **Retry Logic**: Automatic retry for transient errors (502, 503, 504)
- **Rate Limit Monitoring**: Real-time rate limit status checking
- **Graceful Degradation**: Continues processing even with partial failures
- **Detailed Error Logging**: Specific error codes and messages

### Progress Tracking
- **Real-time Progress Bars**: Visual feedback during batch processing
- **Processing Statistics**: Success rates, timing, and throughput metrics
- **Comprehensive Logging**: File and console logging with multiple levels

## Configuration

Key settings in `config.py` and `.env`:

- **GitHub Token**: Required for higher API limits (5000/hour vs 60/hour)
- **Batch Size**: Repositories per processing batch (default: 10)
- **Batch Delay**: Minutes between batches (default: 12)
- **Database URL**: SQLite file location

## Rate Limiting Strategy

- **Authenticated**: 5000 requests/hour (recommended)
- **Unauthenticated**: 60 requests/hour
- **Batch Processing**: Process N repositories, wait M minutes
- **Automatic Delays**: Built-in delays between individual requests
- **Rate Limit Recovery**: Automatic handling of rate limit exceeded scenarios

## Example Outputs

### Comprehensive HTML Report
```
📊 Swift Package Android Compatibility Analysis
Total Repositories: 847 | Average Stars: 1,247 | Package.swift Coverage: 89.2%

🎯 Top Priority Repositories:
1. vapor/vapor - ⭐ 23,500 stars | 🍴 1,400 forks | Priority: 0.891
2. Alamofire/Alamofire - ⭐ 40,000 stars | 🍴 7,500 forks | Priority: 0.876
```

### 🆕 Dependency Analysis Output
```bash
python analyze.py dependencies --output-dir exports/dependencies

🔍 Building dependency tree...
📊 Generating impact analysis...
✅ Impact analysis saved to exports/dependencies/impact_analysis.json
🕸️ Generating network visualization...
✅ Dependency network visualization saved to exports/dependencies/dependency_network.html

🎯 Top 10 Packages by Dependency Impact:
 1. apple/swift-nio - Impact: 45 packages
     ⭐ 7,234 stars | 👥 32 direct dependents
 2. vapor/vapor - Impact: 28 packages  
     ⭐ 23,500 stars | 👥 18 direct dependents
 3. Alamofire/Alamofire - Impact: 22 packages
     ⭐ 40,000 stars | 👥 15 direct dependents
```

### Interactive Charts
- **Hover Data**: Detailed repository information on mouse hover
- **Zoom & Pan**: Interactive exploration of large datasets
- **Responsive Design**: Works on desktop and mobile devices

### Priority CSV Export
```csv
owner,name,priority_score,stars,forks,rationale,github_url,package_index_url
vapor,vapor,0.891,23500,1400,"High popularity; Active community",https://github.com/vapor/vapor,https://swiftpackageindex.com/vapor/vapor
```

## Performance Improvements

### Processing Speed
- **Parallel Operations**: Where possible, operations run concurrently
- **Optimized Database Queries**: Reduced database round trips
- **Smart Caching**: 24-hour cache for recently processed repositories
- **Progress Indicators**: Real-time feedback on processing status

### Error Recovery
- **Graceful Handling**: Continues processing despite individual failures
- **Detailed Logging**: Complete audit trail of all operations
- **Retry Mechanisms**: Automatic retry for transient network issues

## Development Roadmap

### Phase 1: Core Refactoring ✅
- [x] Replace Click with argparse
- [x] Enhanced error handling and logging
- [x] Multiple output formats (HTML, JSON, CSV)
- [x] Interactive visualizations with Plotly
- [x] Progress tracking and statistics

### Phase 2: Analysis Enhancement 🚧
- [x] Priority scoring algorithm improvements
- [x] Comprehensive report generation
- [x] Interactive data exploration tools
- [ ] Migration difficulty estimation
- [ ] Dependency graph analysis

### Phase 3: Monitoring & Automation 📋
- [ ] Automated progress tracking
- [ ] Web dashboard interface
- [ ] Notification system for updates
- [ ] CI/CD integration for regular updates

## Migration from Old Version

The refactored version maintains backward compatibility while adding new features:

### Command Changes
```bash
# Old Click-based commands still work, but use new argparse versions:
# Old: python main.py fetch-data --batch-size 10
# New: python main.py fetch-data --batch-size 10  (same syntax!)

# New comprehensive report generation:
python analyze.py comprehensive --output-dir exports

# New dependency analysis:
python analyze.py dependencies --output-dir exports/dependencies
python analyze.py dependencies --package vapor/vapor --max-depth 4
```

### Dependencies
- **Removed**: click (no longer needed)
- **Added**: plotly (interactive charts), jinja2 (HTML templating), networkx (dependency graphs)
- **Enhanced**: Better error handling, progress tracking, dependency analysis

## Contributing

This project supports the **Swift Android Working Group** initiative. The enhanced version provides:

**Improved Data Analysis:**
- Interactive visualizations for better insight discovery
- Multiple export formats for different use cases
- Enhanced error handling for more reliable data collection
- Progress tracking for long-running operations

**Better Developer Experience:**
- Simplified CLI without external dependencies
- Comprehensive logging and debugging information
- Rich HTML reports for easy sharing
- Detailed CSV exports for spreadsheet analysis

Contributions welcome for:
- Additional interactive visualizations
- Enhanced Package.swift parsing capabilities
- Performance optimizations for large datasets
- Web dashboard development
- Migration tracking features

## License

See LICENSE file for details.

---

**Goal**: Accelerate Swift's Android ecosystem by prioritizing high-impact package migrations through enhanced data-driven insights! 🚀

**New in This Version**: Comprehensive reporting, interactive visualizations, enhanced error handling, and simplified CLI interface for better developer experience.
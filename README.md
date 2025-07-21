# Swift Package Support Data Processing

This repository contains tools for # Priority list for Android migration work
python analyze.py priorities --limit 25
```

### ⏱️ Time Estimates
- **Setup**: 5 minutes
- **First 50 repositories**: ~1 hour (with API rate limiting)
- **All 847 repositories**: ~17 hours (spread over multiple days recommended)
- **Analysis generation**: 2-5 minutes (once data is collected)lyzing Swift Packages that currently support Linux but not Android, helping prioritize work for the Swift Android Working Group.

## About This Project

This project processes the **847 Swift packages** listed in `linux-compatible-android-incompatible.csv` - packages that currently run on Linux but lack Android support. The data comes from Swift Package Index URLs and helps identify which packages would have the highest impact if migrated to Android compatibility.

## Overview

The goal is to build a comprehensive database of Swift packages to:
- 📊 Analyze repository popularity and community engagement from GitHub
- 🔍 Identify high-impact packages for Android compatibility work
- 📈 Track migration progress and dependency relationships
- 🎯 Prioritize efforts based on data-driven insights from real usage metrics

## Features

- **Swift Package Index Integration**: Processes URLs from Swift Package Index format
- **Automated Data Collection**: Fetch repository metadata from GitHub API with intelligent rate limiting
- **Local SQLite Database**: Efficient local storage for 800+ repositories and analysis
- **Package.swift Parsing**: Extract dependencies and Swift tools versions automatically
- **Priority Scoring**: Multi-factor algorithm to rank repositories by migration value
- **Rich Visualizations**: Generate charts and reports for actionable insights
- **Batch Processing**: Respect GitHub API limits while processing hundreds of repositories

## Quick Start

### 1. Setup Environment

```bash
# Run the automated setup script
./setup.sh

# OR manual setup:
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

# Generate comprehensive analysis report
python analyze.py report

# Create visualizations (charts and graphs)
python analyze.py visualize

# Get priority list for Android migration work
python analyze.py priorities --limit 25
```

## Project Structure

```
├── main.py                 # Main CLI interface
├── analyze.py              # Analysis and visualization CLI
├── config.py               # Configuration management
├── models.py               # Database models (SQLAlchemy)
├── fetcher.py              # GitHub API data fetching
├── analyzer.py             # Data analysis and visualization
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── logs/                  # Application logs
├── data/                  # Raw data files
└── exports/               # Generated reports and visualizations
```

## Database Schema

### Repositories Table
- **Metadata**: URL, owner, name, description
- **Popularity**: stars, forks, watchers, issues
- **Activity**: creation date, last update, last push
- **Technical**: language, license, Swift tools version
- **Dependencies**: count and detailed JSON
- **Support Status**: Linux compatible (true), Android compatible (false)

### Processing Logs Table
- **Tracking**: repository, action, status, duration
- **Debugging**: error messages, timestamps

## Analysis Features

### Priority Scoring Algorithm
Repositories are scored based on:
- **Popularity (40%)**: GitHub stars (normalized)
- **Community (30%)**: Forks + watchers (engagement)
- **Recency (20%)**: Recent activity (maintenance)
- **Complexity (10%)**: Lower dependencies = easier migration

### Generated Visualizations
- Repository popularity distribution
- Top starred repositories
- Programming language breakdown
- Dependency complexity analysis
- Timeline of package creation
- Swift tools version distribution

## CLI Commands

### Main Commands (`main.py`)
```bash
# Initialize database
python main.py init-db

# Fetch repository data
python main.py fetch-data [--batch-size N] [--max-batches N]

# Show processing status
python main.py status

# Export data
python main.py export [--format csv|json] [--output path]

# Run scheduled processing
python main.py schedule-runner
```

### Analysis Commands (`analyze.py`)
```bash
# Quick statistics
python analyze.py stats

# Generate full report
python analyze.py report [--output path]

# Create visualizations
python analyze.py visualize [--output-dir path]

# Priority analysis
python analyze.py priorities [--limit N] [--output path]
```

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

## Data Sources & Processing

### Input Data
- **Primary Source**: `linux-compatible-android-incompatible.csv` (847 Swift Package Index URLs)
- **URL Format**: `https://swiftpackageindex.com/owner/repo.git`
- **Scope**: Packages verified to work on Linux but lacking Android support

### GitHub API Integration
- **Repository Metadata**: Stars, forks, issues, activity timestamps
- **Package.swift Analysis**: Dependencies, Swift tools versions, build configurations  
- **Rate Limiting**: Respects GitHub's 5,000 requests/hour limit (authenticated)
- **Error Handling**: Comprehensive logging and retry mechanisms

### Processing Strategy
- **Batch Size**: 10 repositories per batch (configurable)
- **Timing**: 12-minute delays between batches to stay under API limits
- **Caching**: 24-hour cache to avoid re-processing recent data
- **Progress Tracking**: Database logging of all processing activities

## Example Outputs

### Priority Analysis Sample
```
1. vapor/vapor
   ⭐ 23,500 stars | 🍴 1,400 forks | 📦 8 deps
   Priority Score: 0.891 | High popularity; Active community
   Package.swift: ✅ | Swift: 5.8

2. Alamofire/Alamofire
   ⭐ 40,000 stars | 🍴 7,500 forks | 📦 0 deps
   Priority Score: 0.876 | High popularity; Active community; Low complexity
   Package.swift: ✅ | Swift: 5.7
```

### Real Data Sample (From Your CSV)
```
📊 Total Repositories: 847 (from linux-compatible-android-incompatible.csv)
📝 Sample Packages:
  • pusher/pusher-http-swift
  • mongodb/mongo-swift-driver  
  • vapor/fluent-postgres-driver
  • apple/swift-nio-imap
  • realm/SwiftLint

🎯 Expected Analysis Output:
📊 Total Repositories: 847
⭐ Average Stars: ~1,200 (estimated)
📦 Package.swift Coverage: ~80% (estimated)
🔗 Average Dependencies: ~5 (estimated)
```

## Development Roadmap

### Phase 1: Data Collection ✅
- [x] CSV parsing
- [x] GitHub API integration
- [x] Database setup
- [x] Rate limiting

### Phase 2: Analysis 🚧
- [x] Priority scoring
- [x] Visualization generation
- [x] Dependency analysis
- [ ] Migration difficulty estimation

### Phase 3: Monitoring 📋
- [ ] Progress tracking
- [ ] Automated updates
- [ ] Notification system
- [ ] Web dashboard

## Contributing

This project supports the **Swift Android Working Group** initiative. The goal is to accelerate Swift's adoption on Android by identifying and prioritizing high-impact packages for migration.

**How the data helps:**
- **Popularity metrics** identify packages with large user bases
- **Dependency analysis** reveals foundational packages that unlock many others
- **Activity tracking** shows which packages are actively maintained
- **Complexity scoring** helps focus on achievable migration targets

Contributions welcome for:
- Enhanced Package.swift parsing (handling complex dependency declarations)
- Better priority algorithms (incorporating download metrics, etc.)
- Additional visualizations (dependency graphs, migration roadmaps)
- Migration tracking features (monitoring progress over time)
- Performance optimizations (faster processing of large datasets)

## License

See LICENSE file for details.

---

**Goal**: Accelerate Swift's Android ecosystem by prioritizing high-impact package migrations through data-driven insights! 🚀

# Swift Package Android Migration Analysis

A data analysis tool for the [Swift Android Working Group](https://www.swift.org/ecosystem/android/) that analyzes **1065 Swift packages** to prioritize Android migration efforts. Identifies Linux-compatible packages that lack Android support and provides data-driven migration recommendations.

## Quick Start

```bash
# Setup (one-time)
./setup.sh
python swift_analyzer.py setup

# Collect data
python swift_analyzer.py collect --test  # Small test batch
python swift_analyzer.py collect         # Full collection

# Generate analysis
python swift_analyzer.py analyze         # Complete reports & visualizations

# Check results
python swift_analyzer.py status
```

## What It Does

- **Analyzes 1065 Swift packages** that support Linux but not Android
- **Prioritizes migration targets** using GitHub stars, forks, and dependency impact
- **Maps dependency networks** to identify high-impact packages
- **Generates interactive reports** with visualizations and migration recommendations
- **Exports data** in HTML, JSON, and CSV formats for community use

## Requirements

- Python 3.8+
- GitHub token (recommended for higher API limits)

## Installation

```bash
git clone <repository-url>
cd swift-package-support-data-processing
./setup.sh
```

**Manual setup:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add GitHub token to .env: GITHUB_TOKEN=your_token_here
python swift_analyzer.py setup
```

## Usage

### Basic Workflow
```bash
# Collect repository data
python swift_analyzer.py collect --test                 # Test with 3 repos
python swift_analyzer.py collect --batch-size 10        # Process 10 at a time
python swift_analyzer.py collect                        # Full collection

# Generate analysis and reports
python swift_analyzer.py analyze                        # All reports
python swift_analyzer.py analyze --web                  # GitHub Pages site

# Check status and stats
python swift_analyzer.py status                         # Processing status
python swift_analyzer.py stats                          # Quick overview
```

### Commands

| Command | Description |
|---------|-------------|
| `setup` | Initialize database |
| `collect` | Fetch GitHub data |
| `analyze` | Generate reports |
| `status` | Show progress |
| `stats` | Quick statistics |

### Collection Options

| Flag | Description |
|------|-------------|
| `--test` | Process 3 repositories (testing) |
| `--batch-size N` | Set batch size (default: 10) |
| `--max-batches N` | Limit number of batches |

### Analysis Options

| Flag | Description |
|------|-------------|
| `--web` | Generate GitHub Pages site |
| `--comprehensive` | HTML/JSON reports |
| `--dependencies` | Dependency analysis |

## Output

**Generated files:**
- `exports/index.html` - GitHub Pages site
- `exports/comprehensive_report.html` - Detailed analysis
- `exports/priority_analysis.csv` - Migration priorities
- `exports/comprehensive_report.json` - Structured data

**Features:**
- Interactive dependency network graphs
- Priority rankings with rationale
- Repository cards with GitHub/Swift Package Index links
- Executive summary with key metrics

## GitHub Pages Deployment

```bash
# Generate web site
python swift_analyzer.py analyze --web

# Deploy (enable GitHub Pages in repo settings)
git add exports/index.html
git commit -m "Add analysis site"
git push origin main
```

Site will be available at: `https://username.github.io/repository-name/`

## Configuration

**Environment variables** (`.env`):
- `GITHUB_TOKEN` - GitHub API token (recommended)
- `DATABASE_URL` - Database path (optional)

**Rate limits:**
- With token: 5000 requests/hour
- Without token: 60 requests/hour

## Architecture

```
Input Data → GitHub API → SQLite Database → Analysis Engine → Reports
(1065 packages)  (Metadata)    (Storage)       (Priority Scoring)  (Multiple Formats)
```

**Priority scoring considers:**
- GitHub stars and forks
- Dependency impact
- Recent activity
- Package.swift presence

## Project Structure

```
├── swift_analyzer.py               # Main CLI
├── swift_package_analyzer/         # Core package
│   ├── cli/                       # Command interfaces
│   ├── core/                      # Config & models
│   ├── data/                      # GitHub API integration
│   ├── analysis/                  # Analysis logic
│   ├── output/                    # Report generation
│   └── templates/                 # HTML templates
├── data/linux-compatible-android-incompatible.csv
├── requirements.txt
└── exports/                       # Generated outputs
```

## Troubleshooting

**Common issues:**
- **Rate limits:** Add GitHub token to `.env`
- **Import errors:** Activate virtual environment: `source venv/bin/activate`
- **Database errors:** Reinitialize: `python swift_analyzer.py setup`
- **Empty results:** Verify CSV file exists and network connectivity

**Debug commands:**
```bash
python swift_analyzer.py status     # Check database state
python swift_analyzer.py collect --test  # Test with small batch
```

## Example Output

```bash
$ python swift_analyzer.py stats
=== QUICK STATISTICS ===
📊 Total Repositories: 156
⭐ Average Stars: 1,247
🔗 Average Dependencies: 12.3
🏆 Most Popular: Alamofire/Alamofire (40,234 ⭐)
```

---

*Supporting Swift's expansion to Android through data-driven migration prioritization.*
# Swift Package Android Migration Analysis

A data analysis tool for the [Swift Android Working Group](https://www.swift.org/android-workgroup/) that analyzes **1065 Swift packages** to prioritize Android migration efforts. Identifies Linux-compatible packages that lack Android support and provides data-driven migration recommendations.

## Quick Start

```bash
# Setup environment file
echo "GITHUB_TOKEN=your_token_here" > .env

# Python setup and usage
./scripts/setup.sh && python swift_analyzer.py --setup
python swift_analyzer.py --collect
python swift_analyzer.py --analyze
```

## What It Does

- **Analyzes 1065 Swift packages** that support Linux but not Android
- **Prioritizes migration targets** using GitHub stars, forks, and dependency impact
- **Maps dependency networks** to identify high-impact packages
- **Generates interactive reports** with visualizations and migration recommendations
- **Exports data** in HTML, JSON, and CSV formats for community use

## Data Flow Overview

```mermaid
flowchart TD
    A[CSV Input<br/>1065 Packages] --> B[GitHub API<br/>Repository Metadata]
    B --> C[SQLite Database<br/>Structured Storage]
    C --> D[Analysis Engine<br/>Priority Scoring]
    D --> E[Dependency Network<br/>Impact Analysis]
    D --> F[Multi-Format Reports<br/>HTML, JSON, CSV]
    
    G[Package.swift Files] --> C
    H[Dependency Data] --> E
    
    F --> I[Interactive Website<br/>GitHub Pages Ready]
    F --> J[Priority Rankings<br/>Migration Recommendations]
    F --> K[Data Exports<br/>Further Analysis]
    
    style A fill:#334155,stroke:#60a5fa,stroke-width:2px,color:#f9fafb
    style B fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#f9fafb
    style C fill:#0f172a,stroke:#f59e0b,stroke-width:2px,color:#f9fafb
    style D fill:#334155,stroke:#ef4444,stroke-width:2px,color:#f9fafb
    style E fill:#1e293b,stroke:#8b5cf6,stroke-width:2px,color:#f9fafb
    style F fill:#0f172a,stroke:#06b6d4,stroke-width:2px,color:#f9fafb
```

## Installation

**Requirements:** Python 3.11+

```bash
git clone <repository-url>
cd spm-android-support-tracking
echo "GITHUB_TOKEN=your_token_here" > .env

# Setup
./scripts/setup.sh
# OR: python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

## Usage

| Command | Description |
|---------|-------------|
| `--setup` | Initialize database |
| `--collect` | Fetch GitHub data (`--test` for 3 repos) |
| `--analyze` | Generate reports |
| `--status` | Show progress |

```bash
python swift_analyzer.py --setup
python swift_analyzer.py --collect --test               # Test with 3 repos
python swift_analyzer.py --collect --batch-size 10      # Custom batch size
python swift_analyzer.py --analyze --output-dir exports
```

## Output

**Generated files:**
- `exports/index.html` - GitHub Pages site with interactive features
- `exports/priority_analysis.csv` - Migration priority rankings
- `exports/swift_packages.csv` - Complete repository data
- `exports/swift_packages.json` - Repository data in JSON format
- `exports/dependencies/` - Dependency network analysis

**Features:**
- Interactive dependency network graphs
- Priority rankings with detailed rationale
- Repository cards with GitHub/Swift Package Index links
- Executive summary with key metrics
- Complete data exports for further analysis

## GitHub Pages Deployment

```bash
# Generate all reports including web site
python swift_analyzer.py --analyze

# Deploy (enable GitHub Pages in repo settings)
git add exports/index.html
git commit -m "Add analysis site"
git push origin main
```

Site will be available at: `https://username.github.io/repository-name/`

## Configuration

**Environment variables** (`.env`):
- `GITHUB_TOKEN` - GitHub API token (5000 req/hr vs 60 req/hr without)
- `DATABASE_URL` - Database path (optional)

**Priority scoring:** Stars/forks (40%), engagement (30%), recent activity (20%), low complexity (10%)

## Project Structure

```
├── swift_analyzer.py               # Single entry point CLI
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

- **Rate limits:** Add GitHub token to `.env`
- **Import errors:** Activate venv: `source .venv/bin/activate`  
- **Database errors:** Reinitialize: `python swift_analyzer.py --setup`
- **Debug:** Use `--status` and `--test` flags

## Example Output

```bash
$ python swift_analyzer.py --status
=== Processing Status ===
📊 Repositories in database: 156 / 1065
⭐ Average stars: 1,247
📈 Processing complete: 14.6%
🕒 Last update: 2 hours ago
```

---

*Supporting Swift's expansion to Android through data-driven migration prioritization.*
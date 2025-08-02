# 🚀 Automated Data Pipeline: Nightly Incremental Updates with GitHub Actions

## 📊 Overview

Set up an automated data ingestion pipeline that runs nightly to incrementally refresh the Swift package database and publish updated analysis to GitHub Pages. This will replace manual data collection with a scheduled, resumable system that can efficiently process 1065 repositories while staying within GitHub API rate limits.

## 🎯 Objectives

1. **Automated Nightly Data Collection**: Schedule incremental updates to refresh repository metadata
2. **Intelligent Resume Capability**: Resume processing from the last successful update after 45-minute timeout
3. **Database Incremental Updates**: Add tracking fields to support incremental processing
4. **GitHub Pages Auto-Publishing**: Automatically update and deploy analysis reports
5. **Rate Limit Compliance**: Ensure processing stays within GitHub API limits (5000 req/hr with token)

## 🏗️ Technical Requirements

### Database Schema Enhancements

Add incremental update tracking to the existing `Repository` model in `swift_package_analyzer/core/models.py`:

```python
# New fields to add to Repository class:
last_incremental_check = Column(DateTime)  # Last time this repo was checked for updates
needs_update = Column(Boolean, default=True)  # Flag to indicate if repo needs fresh data
incremental_update_count = Column(Integer, default=0)  # Track how many incremental updates
```

Add new table for tracking pipeline runs:
```python
class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    
    id = Column(Integer, primary_key=True)
    run_id = Column(String(50), unique=True)  # GitHub Actions run ID
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String(20))  # running, completed, timeout, error
    last_processed_repo_id = Column(Integer)  # Resume point
    repositories_processed = Column(Integer, default=0)
    repositories_updated = Column(Integer, default=0)
    repositories_skipped = Column(Integer, default=0)
    error_message = Column(Text)
```

### CLI Command Enhancements

Extend `swift_analyzer.py` with new incremental update commands:

```bash
# New commands to implement:
python swift_analyzer.py --incremental              # Run incremental update
python swift_analyzer.py --incremental --resume     # Resume from last checkpoint
python swift_analyzer.py --incremental --dry-run    # Show what would be updated
python swift_analyzer.py --set-stale-threshold 7    # Mark repos older than 7 days as needing update
```

### Core Logic Updates

Modify `swift_package_analyzer/data/fetcher.py` to support:
1. **Incremental Processing**: Skip repositories updated within configurable threshold (default 7 days)
2. **Resume Capability**: Save/restore processing state every 100 repositories
3. **Timeout Handling**: Gracefully stop after 45 minutes and save checkpoint
4. **Smart Prioritization**: Process repositories with oldest `last_incremental_check` first

### GitHub Actions Workflows

#### Workflow 1: Nightly Data Collection (`.github/workflows/nightly-data-collection.yml`)

```yaml
name: 🌙 Nightly Data Collection
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
  workflow_dispatch:     # Manual trigger

jobs:
  collect-data:
    runs-on: ubuntu-latest
    timeout-minutes: 50  # 5-minute buffer for cleanup
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      - name: Setup Python environment
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          
      - name: Setup database and environment
        run: |
          python swift_analyzer.py --setup
          
      - name: Run incremental data collection
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PIPELINE_RUN_ID: ${{ github.run_id }}
        run: |
          python swift_analyzer.py --incremental --timeout 45
          
      - name: Commit database updates
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add swift_packages.db
          if git diff --staged --quiet; then
            echo "No database changes to commit"
          else
            git commit -m "📊 Nightly data update - $(date '+%Y-%m-%d %H:%M UTC')"
            git push
          fi
          
      - name: Trigger analysis workflow
        if: success()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.actions.createWorkflowDispatch({
              owner: context.repo.owner,
              repo: context.repo.repo,
              workflow_id: 'nightly-analysis.yml'
            });
```

#### Workflow 2: Analysis & GitHub Pages Deploy (`.github/workflows/nightly-analysis.yml`)

```yaml
name: 📈 Generate Analysis & Deploy to GitHub Pages
on:
  workflow_dispatch:
  workflow_run:
    workflows: ["🌙 Nightly Data Collection"]
    types: [completed]
    branches: [main]

jobs:
  analyze-and-deploy:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'success' || github.event_name == 'workflow_dispatch'
    
    permissions:
      contents: read
      pages: write
      id-token: write
      
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        
      - name: Setup Python environment
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'
          
      - name: Install dependencies
        run: pip install -r requirements.txt
        
      - name: Generate analysis reports
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python swift_analyzer.py --analyze --output-dir docs
          
      - name: Setup GitHub Pages
        uses: actions/configure-pages@v4
        
      - name: Upload artifacts to GitHub Pages
        uses: actions/upload-pages-artifact@v3
        with:
          path: docs
          
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
        
      - name: Commit analysis updates
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add docs/
          if git diff --staged --quiet; then
            echo "No analysis changes to commit"
          else
            git commit -m "📈 Update analysis reports - $(date '+%Y-%m-%d %H:%M UTC')"
            git push
          fi
```

### Configuration Updates

Enhance `swift_package_analyzer/core/config.py` with new settings:

```python
# Add to config class:
incremental_update_threshold_days: int = 7
incremental_batch_size: int = 50
pipeline_timeout_minutes: int = 45
checkpoint_interval: int = 100  # Save state every N repositories
max_repos_per_run: int = 300   # Limit to stay within API limits
```

## 🔧 Implementation Steps

### Phase 1: Database Schema & Core Logic
- [ ] Add new database fields to `Repository` model
- [ ] Create `PipelineRun` model for tracking runs
- [ ] Update database migration/setup logic
- [ ] Implement incremental processing logic in `DataProcessor`

### Phase 2: CLI Command Extensions
- [ ] Add `--incremental` command with timeout support
- [ ] Add `--resume` functionality with checkpoint loading
- [ ] Add `--dry-run` mode for testing
- [ ] Add repository staleness management commands

### Phase 3: GitHub Actions Setup
- [ ] Create nightly data collection workflow
- [ ] Create analysis & deployment workflow
- [ ] Configure GitHub Pages deployment
- [ ] Set up required repository secrets

### Phase 4: Testing & Validation
- [ ] Test incremental updates on subset of repositories
- [ ] Validate resume functionality after timeout
- [ ] Test complete workflow end-to-end
- [ ] Verify GitHub Pages deployment works correctly

## 📊 Expected Outcomes

### Performance Improvements
- **First Run**: Complete collection of 1065 repositories (~3-4 hours)
- **Nightly Runs**: Process only updated repositories (~15-30 minutes)
- **API Efficiency**: Stay well within 5000 req/hr limit with intelligent batching

### Reliability Features
- **Resume Capability**: Automatic recovery from timeouts or failures
- **Incremental Updates**: Only fetch data for repositories that need refreshing
- **Error Handling**: Graceful handling of API failures with retry logic
- **Monitoring**: Built-in logging and status tracking for debugging

### User Experience
- **Always Fresh Data**: Automatically updated analysis without manual intervention
- **GitHub Pages**: Always-available web interface with latest data
- **Transparency**: Clear logging of what was processed and when

## 🛡️ Risk Mitigation

### API Rate Limiting
- Intelligent batching based on available rate limit
- Automatic throttling when approaching limits
- Checkpoint saves to prevent data loss on timeout

### Data Integrity
- Atomic database updates with rollback on errors
- Validation of fetched data before database writes
- Backup strategy for database state

### Monitoring & Alerting
- GitHub Actions status notifications
- Logging of processing statistics
- Error reporting for failed runs

## 🎛️ Configuration Options

Environment variables for fine-tuning:
```bash
# In .env or GitHub Actions secrets
GITHUB_TOKEN=ghp_xxxxx                           # Required for API access
INCREMENTAL_THRESHOLD_DAYS=7                     # Days before repo considered stale
PIPELINE_TIMEOUT_MINUTES=45                      # Max runtime before checkpoint
CHECKPOINT_INTERVAL=100                          # Repos processed before saving state
MAX_REPOS_PER_NIGHTLY_RUN=300                   # Limit repos per run
BATCH_SIZE_INCREMENTAL=50                        # Smaller batches for incremental
```

## 📈 Success Metrics

1. **Automation**: 100% hands-off nightly updates
2. **Efficiency**: <30 minute nightly runs (vs 3+ hour full runs)
3. **Reliability**: 95%+ successful run completion rate
4. **Data Freshness**: Repository data never more than 7 days old
5. **User Access**: GitHub Pages automatically updated within 1 hour of data collection

---

This automated pipeline will transform the Swift Package Analyzer from a manual tool into a fully automated, always-current resource for the Swift Android Working Group's migration planning efforts.
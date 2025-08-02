# Automation Features

This document describes the automated data collection and analysis pipeline implemented for the Swift Package Android Migration Analysis tool.

## Overview

The automation system provides:
- **Nightly chunked updates** via GitHub Actions (250 repositories per run)
- **Simple timestamp-based staleness tracking** for repository refresh prioritization
- **Automatic GitHub Pages deployment** of updated analysis
- **Database persistence** across workflow runs
- **~4 day refresh cycle** for the complete dataset (1065 repos / 250 per night)

## GitHub Actions Workflow

### Schedule
- Runs nightly at 2:00 AM UTC
- Can be manually triggered
- Uses chunked processing (250 repositories per run)

### Workflow Features

#### Chunked Processing
- Processes 250 repositories per run (configurable)
- Selects oldest repositories first (never fetched, then by last_fetched timestamp)
- Simple and reliable - no complex checkpoint system
- Natural timeout handling - progress saves automatically

#### Staleness-Based Selection
- New repositories (never fetched) are prioritized first
- Existing repositories selected by oldest last_fetched timestamp
- Provides even coverage across the entire dataset over time

#### Rate Limiting
- Respects GitHub API limits (5000 requests/hour with token)
- Configurable batch sizes and delays
- Automatic batch size adjustment based on token availability

### Configuration

#### Environment Variables
```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}  # Required for API access
  DATABASE_URL: sqlite:///swift_packages.db
  REPOSITORIES_PER_BATCH: 50  # Adjustable via workflow inputs
  BATCH_DELAY_MINUTES: 1
```

## Local Testing

### Test Chunked Processing
```bash
# Test with small chunk
python swift_analyzer.py --collect --chunked --test

# Test with custom chunk size
python swift_analyzer.py --collect --chunked --batch-size 50
```

### Test Workflow Components
```bash
# Check processing status and freshness
python swift_analyzer.py --status

# Run chunked collection (250 repos)
python swift_analyzer.py --collect --chunked --batch-size 250

# Generate analysis
python swift_analyzer.py --analyze --output-dir docs
```

## Database Management

### Repository Freshness Tracking
The system tracks repository freshness using simple timestamps:

```sql
-- View repositories by freshness
SELECT 
    COUNT(*) as count,
    CASE 
        WHEN last_fetched IS NULL THEN 'Never fetched'
        WHEN last_fetched > datetime('now', '-1 day') THEN 'Fresh (< 1 day)'
        WHEN last_fetched > datetime('now', '-7 days') THEN 'Recent (1-7 days)'
        ELSE 'Stale (> 7 days)'
    END as freshness_category
FROM repositories 
GROUP BY freshness_category;

-- View oldest repositories (next to be processed)
SELECT url, last_fetched, processing_status
FROM repositories
ORDER BY last_fetched ASC NULLS FIRST
LIMIT 10;
```

### Repository Selection Logic
Repositories are selected for processing in this order:
1. **New repositories**: Never been fetched (last_fetched IS NULL)
2. **Oldest repositories**: Ordered by last_fetched timestamp ascending
3. **Chunk size limit**: Up to 250 repositories per run

## Monitoring

### Workflow Status
Monitor the automation through:
- GitHub Actions workflow runs
- Workflow summary reports
- Processing checkpoint status
- Database completion metrics

### Key Metrics
- **Completion Rate**: Percentage of repositories successfully processed
- **Processing Speed**: Repositories per minute
- **API Efficiency**: Success rate and error frequency
- **Resume Effectiveness**: Time saved through checkpoint recovery

### Error Handling
- Automatic retry for transient failures
- Graceful handling of API rate limit exceeded
- Checkpoint preservation on timeout/interruption
- Detailed error logging and reporting

## Performance Optimization

### Batch Sizing
- Default: 50 repositories per batch
- Smaller batches for accounts without GitHub tokens
- Larger batches for high-rate limit scenarios

### API Efficiency
- ~3 API calls per repository on average
- Intelligent rate limiting to maximize throughput
- Batch processing with configurable delays

### Database Optimization
- SQLite for simplicity and portability
- Indexed queries for status checks
- Automatic cleanup of old checkpoints

## Deployment

### GitHub Pages
- Automatic deployment on successful analysis
- Static site generation from analysis output
- Force orphan commits to minimize history

### Database Persistence
- Database changes committed to repository with each run
- No artifact storage required - database persists in git history
- Simple and reliable persistence mechanism

## Configuration Reference

### CLI Options
```bash
--chunked                   # Enable chunked processing (recommended)
--incremental               # Enable legacy incremental processing  
--batch-size N              # Repositories per chunk/batch
--test                      # Process only 3 repositories for testing
```

### Environment Configuration
```bash
# .env file
GITHUB_TOKEN=ghp_xxxxx                    # GitHub API token
DATABASE_URL=sqlite:///swift_packages.db  # Database path
REPOSITORIES_PER_BATCH=50                 # Default batch size
BATCH_DELAY_MINUTES=2                     # Delay between batches
```

### Staleness Configuration
```python
# In config.py
staleness_threshold_days: int = 7          # Default update frequency
popular_repo_threshold_stars: int = 1000   # Popular repository threshold
popular_repo_staleness_days: int = 3       # Popular repo update frequency
checkpoint_cleanup_days: int = 7           # Checkpoint retention
```

## Troubleshooting

### Common Issues

#### Rate Limit Exceeded
- Check GitHub token is configured
- Reduce batch size or increase delays
- Monitor API usage in workflow logs

#### Processing Timeout
- Normal behavior for large datasets
- Progress is saved automatically
- Will resume in next workflow run

#### Database Issues
- Database is committed to git repository
- Check git history for database state
- Verify file permissions and disk space

#### Missing Dependencies
- Verify requirements.txt is up to date
- Check Python version compatibility
- Validate virtual environment setup

### Debug Commands
```bash
# Check processing status
python swift_analyzer.py --status

# View checkpoint information
python -c "
from swift_package_analyzer.core.models import ProcessingCheckpoint, SessionLocal
db = SessionLocal()
checkpoints = db.query(ProcessingCheckpoint).all()
for cp in checkpoints:
    print(f'{cp.session_id}: {cp.status} - {cp.repositories_processed}/{cp.total_repositories}')
db.close()
"

# Test API connectivity
python -c "
from swift_package_analyzer.data.fetcher import GitHubFetcher
fetcher = GitHubFetcher()
fetcher._check_rate_limit_status()
"
```

## Future Enhancements

### Planned Features
- Multi-repository parallel processing
- Webhook-triggered updates for popular repositories
- Integration with Swift Package Index API
- Advanced error recovery mechanisms
- Performance metrics dashboard

### Optimization Opportunities
- Delta synchronization for Package.swift changes
- Caching of dependency analysis results
- Distributed processing for large datasets
- Real-time progress reporting
# GitHub Actions Workflows

This directory contains the automated workflows for the Swift Package Android Migration Analysis project.

## Active Workflows

### 1. `nightly-analysis.yml` - Data Collection & Analysis
**Triggers:**
- ⏰ **Scheduled**: Daily at 2:00 AM UTC  
- 🎯 **Manual**: Workflow dispatch with parameters

**Parameters (Manual Trigger):**
- `batch_size`: Number of repositories to process (default: 250)
- `test_mode`: Run in test mode with only 3 repositories (default: false)

**What it does:**
1. Fetches metadata for Swift packages from GitHub API
2. Updates the SQLite database with new/refreshed data
3. Generates comprehensive analysis and dependency reports
4. Commits updated data to the repository
5. **Does NOT deploy** - only updates the `docs/` directory

**Outputs:**
- `docs/swift_packages.json` - Analysis data for frontend
- `docs/swift_packages.csv` - CSV export  
- `docs/dependencies/` - Dependency analysis and visualizations
- `swift_packages.db` - Updated SQLite database

---

### 2. `publish-docs.yml` - Documentation Publishing
**Triggers:**
- 📝 **Push to main**: When `docs/` or `frontend/` directories are modified
- 🎯 **Manual**: Workflow dispatch with force rebuild option

**Parameters (Manual Trigger):**
- `force_rebuild`: Force rebuild even if no docs changes detected (default: false)

**What it does:**
1. Detects changes to documentation or frontend code
2. Builds the Next.js frontend with updated data
3. Deploys the built site to GitHub Pages
4. **Only runs if** analysis data exists and is valid

**Outputs:**
- GitHub Pages deployment with interactive Swift package analysis site

---

## Workflow Separation Benefits

### 🔄 **Decoupled Operations**
- Analysis can run independently of publishing
- Publishing only happens when needed (docs changes)
- Reduced resource usage and faster deployments

### 🧪 **Better Testing**
- Test analysis with small batches without triggering deployment
- Test deployment with force rebuild without running full analysis
- Independent failure isolation

### ⚡ **Improved Performance**
- Analysis workflow focuses on data processing (45 min timeout)
- Publishing workflow is fast and lightweight (15 min timeout)
- No unnecessary rebuilds when only data changes

### 📊 **Enhanced Monitoring**
- Separate workflow status for analysis vs publishing
- Clear failure attribution
- Independent retry capabilities

---

## Usage Examples

### Test the Analysis Pipeline
```yaml
# Use workflow dispatch on nightly-analysis.yml
batch_size: "10"
test_mode: true
```

### Force Documentation Rebuild
```yaml
# Use workflow dispatch on publish-docs.yml  
force_rebuild: true
```

### Normal Operation
- Analysis runs automatically every night at 2:00 AM UTC
- Documentation publishes automatically when analysis commits new data
- No manual intervention required

---

## Deprecated Files

- `nightly-update.yml.deprecated` - Old monolithic workflow (kept for reference)
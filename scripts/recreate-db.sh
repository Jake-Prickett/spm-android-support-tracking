#!/bin/bash
# Database Recreation Script
# Rebuilds database from scratch using latest JSON export

set -e

echo "🗄️  Database Recreation Script"
echo "=============================="

# Configuration
DB_FILE="swift_packages.db"
BACKUP_DIR="backups"
JSON_SOURCE="docs/swift_packages.json"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup existing database if it exists
if [ -f "$DB_FILE" ]; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/${DB_FILE%.db}_$TIMESTAMP.db"
    echo "📦 Backing up existing database to: $BACKUP_FILE"
    cp "$DB_FILE" "$BACKUP_FILE"
    
    # Show current stats
    echo "📊 Current database stats:"
    sqlite3 "$DB_FILE" "
        SELECT 'Repositories: ' || COUNT(*) FROM repositories;
        SELECT 'State Transitions: ' || COUNT(*) FROM state_transitions;
        SELECT 'Processing Logs: ' || COUNT(*) FROM processing_logs;
    " 2>/dev/null || echo "   (Unable to read current database)"
fi

# Remove old database
echo "🗑️  Removing old database..."
rm -f "$DB_FILE"

# Create fresh schema
echo "🏗️  Creating fresh database schema..."
python3 -c "
from src.models import create_tables
from src.config import config
print('Creating database schema...')
create_tables()
print('✅ Database schema created successfully')
"

# Check if JSON source exists
if [ ! -f "$JSON_SOURCE" ]; then
    echo "⚠️  JSON source not found: $JSON_SOURCE"
    echo "   Creating empty database with schema only"
    echo "   Run: python3 swift_analyzer.py --collect --analyze"
    exit 0
fi

# Import data from JSON
echo "📥 Importing data from JSON export..."
python3 -c "
import json
import sys
from src.models import SessionLocal, Repository, StateTransition
from datetime import datetime

# Load JSON data
try:
    with open('$JSON_SOURCE', 'r') as f:
        data = json.load(f)
    repositories = data.get('repositories', [])
    print(f'Found {len(repositories)} repositories in JSON')
except Exception as e:
    print(f'Error loading JSON: {e}')
    sys.exit(1)

# Check for existing state transitions backup
transitions_backup = None
try:
    import os
    if os.path.exists('$BACKUP_DIR'):
        backup_files = [f for f in os.listdir('$BACKUP_DIR') if f.endswith('.db')]
        if backup_files:
            latest_backup = max([f'$BACKUP_DIR/{f}' for f in backup_files], key=os.path.getmtime)
            print(f'📋 Found backup database: {latest_backup}')
            
            # Extract state transitions from backup
            import sqlite3
            backup_conn = sqlite3.connect(latest_backup)
            cursor = backup_conn.cursor()
            try:
                cursor.execute('SELECT * FROM state_transitions')
                transitions_backup = cursor.fetchall()
                cursor.execute('PRAGMA table_info(state_transitions)')
                transition_columns = [col[1] for col in cursor.fetchall()]
                print(f'📋 Extracted {len(transitions_backup)} state transitions from backup')
            except:
                pass  # Table might not exist in backup
            finally:
                backup_conn.close()
except Exception as e:
    print(f'⚠️  Could not extract transitions from backup: {e}')

# Import to database
db = SessionLocal()
try:
    imported = 0
    for repo_data in repositories:
        # Create repository object
        repo = Repository()
        
        # Map JSON fields to model fields
        for field in ['url', 'owner', 'name', 'description', 'stars', 'forks', 
                     'watchers', 'language', 'license_name', 'has_package_swift',
                     'swift_tools_version', 'dependencies_count', 'linux_compatible', 
                     'android_compatible', 'current_state']:
            if field in repo_data:
                setattr(repo, field, repo_data[field])
        
        # Handle datetime fields
        for dt_field in ['created_at', 'updated_at', 'pushed_at', 'last_fetched']:
            if repo_data.get(dt_field):
                try:
                    setattr(repo, dt_field, datetime.fromisoformat(repo_data[dt_field].replace('Z', '+00:00')))
                except:
                    pass  # Skip invalid dates
        
        # Set processing status
        repo.processing_status = 'completed'
        
        try:
            db.add(repo)
            imported += 1
        except Exception as e:
            print(f'Error importing {repo.owner}/{repo.name}: {e}')
    
    # Restore state transitions if available
    if transitions_backup and transition_columns:
        print(f'📋 Restoring {len(transitions_backup)} state transitions...')
        restored = 0
        for transition_data in transitions_backup:
            try:
                # Map backup data to StateTransition object
                transition = StateTransition()
                for i, col in enumerate(transition_columns):
                    if col != 'id' and i < len(transition_data):  # Skip auto-increment ID
                        value = transition_data[i]
                        if col in ['created_at'] and value:
                            try:
                                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            except:
                                pass
                        setattr(transition, col, value)
                
                db.add(transition)
                restored += 1
            except Exception as e:
                print(f'Warning: Could not restore transition: {e}')
        
        print(f'✅ Restored {restored} state transitions')
    
    db.commit()
    print(f'✅ Successfully imported {imported} repositories')
    
except Exception as e:
    db.rollback()
    print(f'❌ Import failed: {e}')
    sys.exit(1)
finally:
    db.close()
"

# Verify recreation
echo "✅ Database recreation completed!"
echo "📊 New database stats:"
sqlite3 "$DB_FILE" "
    SELECT 'Repositories: ' || COUNT(*) FROM repositories;
    SELECT 'State Transitions: ' || COUNT(*) FROM state_transitions;  
    SELECT 'Processing Logs: ' || COUNT(*) FROM processing_logs;
    SELECT 'States in use: ' || GROUP_CONCAT(DISTINCT current_state) FROM repositories;
"

echo ""
echo "💡 Next steps:"
echo "   - Run: python3 swift_analyzer.py --status"  
echo "   - Run: python3 swift_analyzer.py --analyze"
echo "   - Test frontend: cd frontend && npm run build"
#!/usr/bin/env python3
"""
Reset script for Swift Package Support Data Processing project.
This script will completely reset the project by:
1. Removing the SQLite database
2. Clearing all log files
3. Removing export directories
4. Reinitializing the database with fresh tables
"""

import os
import shutil
import sys
from pathlib import Path

from config import config
from models import Base, engine


def confirm_reset():
    """Ask user for confirmation before proceeding with reset."""
    print("🚨 WARNING: This will permanently delete all data!")
    print("The following will be removed:")
    print(f"  - Database: {config.database_url}")
    print(f"  - Log directory: logs/")
    print(f"  - Export directory: exports/")
    print("  - All processed repository data")
    print()
    
    response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
    return response.lower() == 'yes'


def remove_database():
    """Remove the SQLite database file."""
    db_path = config.database_url.replace('sqlite:///', '')
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✅ Removed database: {db_path}")
    else:
        print(f"ℹ️  Database not found: {db_path}")


def clear_logs():
    """Clear all log files."""
    logs_dir = Path("logs")
    if logs_dir.exists():
        shutil.rmtree(logs_dir)
        print("✅ Removed logs directory")
    else:
        print("ℹ️  Logs directory not found")
    
    # Recreate logs directory
    logs_dir.mkdir(exist_ok=True)
    print("✅ Recreated logs directory")


def clear_exports():
    """Clear all export files and directories."""
    exports_dir = Path("exports")
    if exports_dir.exists():
        shutil.rmtree(exports_dir)
        print("✅ Removed exports directory")
    else:
        print("ℹ️  Exports directory not found")
    
    # Recreate exports directory
    exports_dir.mkdir(exist_ok=True)
    print("✅ Recreated exports directory")


def initialize_database():
    """Initialize fresh database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Initialized fresh database tables")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False
    return True


def main():
    """Main reset function."""
    print("Swift Package Data Processing - Project Reset")
    print("=" * 50)
    
    # Check if --force flag is provided to skip confirmation
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        print("🔥 Force reset mode - skipping confirmation")
    else:
        if not confirm_reset():
            print("❌ Reset cancelled by user")
            return
    
    print("\n🔄 Starting reset process...")
    
    # Remove database
    remove_database()
    
    # Clear logs
    clear_logs()
    
    # Clear exports
    clear_exports()
    
    # Initialize fresh database
    if initialize_database():
        print("\n✅ Project reset completed successfully!")
        print("\nYou can now start fresh with:")
        print("  python main.py fetch-data --batch-size 5 --max-batches 1")
    else:
        print("\n❌ Reset completed with errors. Check database configuration.")
        sys.exit(1)


if __name__ == "__main__":
    main()
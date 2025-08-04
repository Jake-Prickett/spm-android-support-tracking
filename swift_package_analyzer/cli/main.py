#!/usr/bin/env python3
"""
Main CLI script for Swift Package support data processing.
"""
from datetime import datetime
from pathlib import Path

from swift_package_analyzer.core.config import config
from swift_package_analyzer.data.fetcher import DataProcessor
from swift_package_analyzer.core.models import (
    ProcessingLog,
    Repository,
    SessionLocal,
    create_tables,
)


def init_database(args):
    """Initialize the database with required tables."""
    create_tables()
    print("Database initialized")


def show_status(args):
    """Show processing status and statistics."""
    db = SessionLocal()

    # Repository statistics
    total_repos = db.query(Repository).count()
    completed_repos = (
        db.query(Repository).filter(Repository.processing_status == "completed").count()
    )
    error_repos = (
        db.query(Repository).filter(Repository.processing_status == "error").count()
    )
    pending_repos = (
        db.query(Repository).filter(Repository.processing_status == "pending").count()
    )

    print("Repository Processing Status:")
    print(f"  Total repositories: {total_repos}")
    print(f"  Completed: {completed_repos}")
    print(f"  Errors: {error_repos}")
    print(f"  Pending: {pending_repos}")

    if completed_repos > 0:
        # Repository insights
        avg_stars = (
            db.query(Repository)
            .filter(Repository.processing_status == "completed")
            .with_entities(Repository.stars)
            .all()
        )
        avg_stars = sum(r[0] for r in avg_stars if r[0]) / len(
            [r for r in avg_stars if r[0]]
        )

        has_package_swift = (
            db.query(Repository)
            .filter(
                Repository.processing_status == "completed",
                Repository.has_package_swift.is_(True),
            )
            .count()
        )

        print("\nRepository Insights:")
        print(f"  Average stars: {avg_stars:.1f}")
        print(f"  Repositories with Package.swift: {has_package_swift}")
        print(
            f"  Package.swift coverage: {(has_package_swift/completed_repos)*100:.1f}%"
        )

        # Package state statistics
        from swift_package_analyzer.core.models import PACKAGE_STATES

        print("\nPackage Migration States:")
        for state in PACKAGE_STATES.keys():
            count = (
                db.query(Repository)
                .filter(
                    Repository.processing_status == "completed",
                    Repository.current_state == state,
                )
                .count()
            )
            if count > 0:
                percentage = (count / completed_repos) * 100
                print(f"  {state.capitalize()}: {count} ({percentage:.1f}%)")

        # Show migrated vs tracking counts
        migrated_count = (
            db.query(Repository)
            .filter(
                Repository.processing_status == "completed",
                Repository.current_state == "migrated",
            )
            .count()
        )
        tracking_count = (
            db.query(Repository)
            .filter(
                Repository.processing_status == "completed",
                Repository.current_state == "tracking",
            )
            .count()
        )

        print(f"\nMigration Progress:")
        print(f"  Migrated packages: {migrated_count}")
        print(f"  Still tracking: {tracking_count}")
        if migrated_count + tracking_count > 0:
            progress = (migrated_count / (migrated_count + tracking_count)) * 100
            print(f"  Migration progress: {progress:.1f}%")

    # Recent processing logs
    recent_logs = (
        db.query(ProcessingLog).order_by(ProcessingLog.created_at.desc()).limit(5).all()
    )

    if recent_logs:
        print("\nRecent Processing Activity:")
        for log in recent_logs:
            timestamp = log.created_at.strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {timestamp} - {log.action}: {log.status}")

    db.close()


def export_data(args):
    """Export repository data."""
    import json

    import pandas as pd

    db = SessionLocal()

    # Query completed repositories
    repos = (
        db.query(Repository).filter(Repository.processing_status == "completed").all()
    )

    if not repos:
        print("No data available for export")
        return

    # Convert to dictionary format
    data = []
    for repo in repos:
        repo_data = {
            "url": repo.url,
            "owner": repo.owner,
            "name": repo.name,
            "description": repo.description,
            "stars": repo.stars,
            "forks": repo.forks,
            "watchers": repo.watchers,
            "language": repo.language,
            "license_name": repo.license_name,
            "has_package_swift": repo.has_package_swift,
            "swift_tools_version": repo.swift_tools_version,
            "dependencies_count": repo.dependencies_count,
            "linux_compatible": repo.linux_compatible,
            "android_compatible": repo.android_compatible,
            "current_state": repo.current_state,
            "created_at": repo.created_at.isoformat() if repo.created_at else None,
            "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
            "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
            "last_fetched": (
                repo.last_fetched.isoformat() if repo.last_fetched else None
            ),
        }
        data.append(repo_data)

    # Create output directory
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    # Export data
    if args.format == "csv":
        df = pd.DataFrame(data)
        df.to_csv(args.output, index=False)
    elif args.format == "json":
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2, default=str)

    print(f"Exported {len(data)} repositories to {args.output}")
    db.close()


def set_package_state(args):
    """Set the migration state for a package."""
    from swift_package_analyzer.core.models import PACKAGE_STATES

    if args.state not in PACKAGE_STATES:
        print(f"Invalid state: {args.state}")
        print(f"Valid states: {', '.join(PACKAGE_STATES.keys())}")
        return

    db = SessionLocal()
    try:
        # Find repository by URL or owner/name
        if args.url:
            repo = db.query(Repository).filter(Repository.url == args.url).first()
        elif args.owner and args.name:
            repo = (
                db.query(Repository)
                .filter(Repository.owner == args.owner, Repository.name == args.name)
                .first()
            )
        else:
            print("Must specify either --url or both --owner and --name")
            return

        if not repo:
            print("Repository not found")
            return

        old_state, new_state = repo.transition_state(args.state, args.reason, db)
        db.commit()

        print(f"Updated {repo.owner}/{repo.name}")
        print(f"  State: {old_state} → {new_state}")
        if args.reason:
            print(f"  Reason: {args.reason}")

    except Exception as e:
        db.rollback()
        print(f"Error updating state: {e}")
    finally:
        db.close()


def list_states(args):
    """List all available package states."""
    from swift_package_analyzer.core.models import PACKAGE_STATES

    print("Available Package States:")
    print("=" * 50)
    for state, description in PACKAGE_STATES.items():
        print(f"  {state:<12} : {description}")

    # Show current state distribution
    print("\nCurrent State Distribution:")
    print("=" * 50)

    db = SessionLocal()
    try:
        completed_repos = (
            db.query(Repository)
            .filter(Repository.processing_status == "completed")
            .count()
        )

        if completed_repos > 0:
            for state in PACKAGE_STATES.keys():
                count = (
                    db.query(Repository)
                    .filter(
                        Repository.processing_status == "completed",
                        Repository.current_state == state,
                    )
                    .count()
                )
                percentage = (
                    (count / completed_repos) * 100 if completed_repos > 0 else 0
                )
                print(f"  {state:<12} : {count:4d} repos ({percentage:5.1f}%)")
        else:
            print("  No completed repositories found")

    finally:
        db.close()


def show_database_info(args=None):
    """Show database information useful for CI/CD workflows."""
    db_path = Path(config.database_url.replace("sqlite:///", ""))

    print("Database Information:")
    print(f"  Database file: {db_path}")
    print(f"  Exists: {db_path.exists()}")

    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f"  Size: {size_mb:.2f} MB")

        db = SessionLocal()
        try:
            total_repos = db.query(Repository).count()
            completed_repos = (
                db.query(Repository)
                .filter(Repository.processing_status == "completed")
                .count()
            )
            pending_repos = (
                db.query(Repository)
                .filter(Repository.processing_status == "pending")
                .count()
            )
            error_repos = (
                db.query(Repository)
                .filter(Repository.processing_status == "error")
                .count()
            )

            print(f"  Total repositories: {total_repos}")
            print(f"  Completed: {completed_repos}")
            print(f"  Pending: {pending_repos}")
            print(f"  Errors: {error_repos}")

            if total_repos > 0:
                completion_rate = (completed_repos / total_repos) * 100
                print(f"  Completion rate: {completion_rate:.1f}%")

                if completion_rate > 50:
                    print("  ✅ Substantial data - recommended for persistence")
                elif completion_rate > 10:
                    print("  ⚠️  Partial data - consider persistence")
                else:
                    print("  ❌ Minimal data - fresh start recommended")

        except Exception as e:
            print(f"  Error reading database: {e}")
        finally:
            db.close()
    else:
        print("  ❌ Database not found - run init-db command")

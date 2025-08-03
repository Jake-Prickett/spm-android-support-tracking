#!/usr/bin/env python3
"""
Main CLI script for Swift Package support data processing.
"""
import argparse
import sys
import time
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


def _countdown_timer(total_seconds):
    """Display a countdown timer for the specified number of seconds."""
    for remaining in range(total_seconds, 0, -1):
        minutes, seconds = divmod(remaining, 60)
        timer_display = f"\rNext batch in: {minutes:02d}:{seconds:02d}"
        print(timer_display, end="", flush=True)
        time.sleep(1)

    print("\r" + " " * 20 + "\r", end="")


def init_database(args):
    """Initialize the database with required tables."""
    create_tables()
    print("Database initialized")


def fetch_data(args):
    """Fetch repository data from GitHub API."""
    batch_size = args.batch_size
    max_batches = args.max_batches

    print(f"Processing repositories: batch size {batch_size}")

    processor = DataProcessor()
    urls = processor.load_csv_repositories()

    if not urls:
        print("No repositories found in source data")
        return

    total_urls = len(urls)
    processed_count = 0
    batch_count = 0

    print(f"Found {total_urls} repositories to process")

    # Process in batches
    for i in range(0, total_urls, batch_size):
        if max_batches and batch_count >= max_batches:
            break

        batch = urls[i : i + batch_size]
        batch_count += 1

        print(f"\nProcessing batch {batch_count} ({len(batch)} repositories)...")

        results = processor.process_batch(batch)
        processed_count += len(batch)

        print(
            f"Batch {batch_count}: {results['success']} success, {results['error']} errors ({processed_count}/{total_urls})"
        )

        fetched_count = results["success"] + results["error"]
        if (
            i + batch_size < total_urls
            and (not max_batches or batch_count < max_batches)
            and fetched_count > 0
        ):
            _countdown_timer(config.batch_delay_minutes * 60)
        elif fetched_count == 0:
            print("Batch skipped - no new data to fetch")

    final_stats = processor.get_processing_stats()
    processor.close()

    print(f"\nCompleted: {processed_count} repositories, {batch_count} batches")
    print(
        f"Success rate: {final_stats['success_rate']:.1f}% ({final_stats['fetcher_stats']['request_count']} API calls)"
    )
    print(f"Rate: {final_stats['repos_per_minute']:.1f} repos/minute")


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
            "created_at": repo.created_at.isoformat() if repo.created_at else None,
            "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
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

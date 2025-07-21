#!/usr/bin/env python3
"""
Main CLI script for Swift Package support data processing.
"""
import time

import click
import schedule

from config import config
from fetcher import DataProcessor
from models import ProcessingLog, Repository, SessionLocal, create_tables


@click.group()
def cli():
    """Swift Package Support Data Processing CLI."""
    pass


@cli.command()
def init_db():
    """Initialize the database with required tables."""
    click.echo("Initializing database...")
    create_tables()
    click.echo("Database initialized successfully!")


@cli.command()
@click.option(
    "--batch-size", default=10, help="Number of repositories to process in each batch"
)
@click.option(
    "--max-batches", default=None, type=int, help="Maximum number of batches to process"
)
def fetch_data(batch_size, max_batches):
    """Fetch repository data from GitHub API."""
    click.echo(f"Starting data fetch with batch size: {batch_size}")

    processor = DataProcessor()
    urls = processor.load_csv_repositories()

    if not urls:
        click.echo("No URLs found in CSV file!")
        return

    total_urls = len(urls)
    processed_count = 0
    batch_count = 0

    click.echo(f"Found {total_urls} repositories to process")

    # Process in batches
    for i in range(0, total_urls, batch_size):
        if max_batches and batch_count >= max_batches:
            break

        batch = urls[i : i + batch_size]
        batch_count += 1

        click.echo(f"\nProcessing batch {batch_count} ({len(batch)} repositories)...")

        results = processor.process_batch(batch)
        processed_count += len(batch)

        click.echo(
            f"Batch {batch_count} complete: {results['success']} success, {results['error']} errors"
        )
        click.echo(f"Progress: {processed_count}/{total_urls} repositories processed")

        # Wait between batches (except for the last batch)
        if i + batch_size < total_urls and (
            not max_batches or batch_count < max_batches
        ):
            click.echo(
                f"Waiting {config.batch_delay_minutes} minutes before next batch..."
            )
            time.sleep(config.batch_delay_minutes * 60)

    processor.close()
    click.echo(
        f"\nData fetch complete! Processed {processed_count} repositories in {batch_count} batches."
    )


@cli.command()
def status():
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

    click.echo("Repository Processing Status:")
    click.echo(f"  Total repositories: {total_repos}")
    click.echo(f"  Completed: {completed_repos}")
    click.echo(f"  Errors: {error_repos}")
    click.echo(f"  Pending: {pending_repos}")

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

        click.echo("\nRepository Insights:")
        click.echo(f"  Average stars: {avg_stars:.1f}")
        click.echo(f"  Repositories with Package.swift: {has_package_swift}")
        click.echo(
            f"  Package.swift coverage: {(has_package_swift/completed_repos)*100:.1f}%"
        )

    # Recent processing logs
    recent_logs = (
        db.query(ProcessingLog).order_by(ProcessingLog.created_at.desc()).limit(5).all()
    )

    if recent_logs:
        click.echo("\nRecent Processing Activity:")
        for log in recent_logs:
            timestamp = log.created_at.strftime("%Y-%m-%d %H:%M:%S")
            click.echo(f"  {timestamp} - {log.action}: {log.status}")

    db.close()


@cli.command()
@click.option(
    "--format", type=click.Choice(["csv", "json"]), default="csv", help="Export format"
)
@click.option("--output", default="exports/repositories.csv", help="Output file path")
def export(format, output):
    """Export repository data."""
    import json
    from pathlib import Path

    import pandas as pd

    db = SessionLocal()

    # Query completed repositories
    repos = (
        db.query(Repository).filter(Repository.processing_status == "completed").all()
    )

    if not repos:
        click.echo("No completed repositories found to export!")
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
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    # Export data
    if format == "csv":
        df = pd.DataFrame(data)
        df.to_csv(output, index=False)
    elif format == "json":
        with open(output, "w") as f:
            json.dump(data, f, indent=2, default=str)

    click.echo(f"Exported {len(data)} repositories to {output}")
    db.close()


@cli.command()
def schedule_runner():
    """Run the scheduled batch processing."""
    click.echo("Starting scheduled runner...")
    click.echo(
        f"Will process {config.repositories_per_batch} repositories every {config.batch_delay_minutes} minutes"
    )

    def run_batch():
        processor = DataProcessor()
        urls = processor.load_csv_repositories()

        # Get pending repositories
        db = SessionLocal()
        processed_urls = {repo.url for repo in db.query(Repository.url).all()}
        pending_urls = [url for url in urls if url not in processed_urls]
        db.close()

        if pending_urls:
            batch = pending_urls[: config.repositories_per_batch]
            click.echo(f"Processing batch of {len(batch)} repositories...")
            results = processor.process_batch(batch)
            click.echo(
                f"Batch complete: {results['success']} success, {results['error']} errors"
            )
        else:
            click.echo("No pending repositories to process")

        processor.close()

    # Schedule the batch processing
    schedule.every(config.batch_delay_minutes).minutes.do(run_batch)

    # Run indefinitely
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    cli()

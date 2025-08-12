#!/usr/bin/env python3
"""
Main CLI script for Swift Package support data processing.
"""
from datetime import datetime
from pathlib import Path

from src.config import config
from src.fetcher import DataProcessor
from src.models import (
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
        from src.models import PACKAGE_STATES

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

    # Add status change transactions metadata
    from src.models import StateTransition

    status_transactions = db.query(StateTransition).all()

    transactions_metadata = None
    if status_transactions:
        github_transactions = [t for t in status_transactions if t.issue_number]
        transactions_metadata = {
            "total_transactions": len(status_transactions),
            "github_issue_transactions": len(github_transactions),
            "status_breakdown": {},
            "recent_transactions": [],
        }

        for transition in status_transactions:
            status = transition.to_state
            if status not in transactions_metadata["status_breakdown"]:
                transactions_metadata["status_breakdown"][status] = 0
            transactions_metadata["status_breakdown"][status] += 1

            # Get repository info
            repo = (
                db.query(Repository)
                .filter(Repository.id == transition.repository_id)
                .first()
            )
            if repo:
                transaction_data = {
                    "owner": repo.owner,
                    "name": repo.name,
                    "from_state": transition.from_state,
                    "to_state": transition.to_state,
                    "reason": transition.reason,
                    "changed_by": transition.changed_by,
                    "date": (
                        transition.created_at.isoformat()
                        if transition.created_at
                        else None
                    ),
                }

                # Add GitHub issue metadata if present
                if transition.issue_number:
                    transaction_data["github_issue"] = transition.issue_number

                transactions_metadata["recent_transactions"].append(transaction_data)

    # Export data
    if args.format == "csv":
        df = pd.DataFrame(data)
        df.to_csv(args.output, index=False)
    elif args.format == "json":
        export_data = {
            "repositories": data,
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "total_repositories": len(data),
            },
        }

        # Add status change transactions if any
        if transactions_metadata:
            export_data["status_transactions"] = transactions_metadata

        with open(args.output, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

    print(f"Exported {len(data)} repositories to {args.output}")
    if transactions_metadata:
        print(
            f"Included {transactions_metadata['total_transactions']} status change transactions ({transactions_metadata['github_issue_transactions']} from GitHub issues)"
        )
    db.close()


def set_package_state(args):
    """Set the migration state for a package."""
    from src.models import PACKAGE_STATES

    # Process GitHub issues if requested
    if hasattr(args, "process_issues") and args.process_issues:
        return process_github_issues(args)

    # Process single GitHub issue if requested
    if hasattr(args, "process_issue") and args.process_issue:
        return process_single_github_issue(args)

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

        # Check if this is a status change from GitHub issue (has issue number)
        changed_by = None
        issue_number = None
        if hasattr(args, "issue_number") and args.issue_number:
            issue_number = str(args.issue_number)
            changed_by = getattr(args, "changed_by", "cli")
            print(f"Creating status change transaction from issue #{args.issue_number}")

        old_state, new_state = repo.transition_state(
            args.state,
            reason=args.reason,
            changed_by=changed_by,
            issue_number=issue_number,
            session=db,
        )
        db.commit()

        print(f"Updated {repo.owner}/{repo.name}")
        print(f"  State: {old_state} → {new_state}")
        if args.reason:
            print(f"  Reason: {args.reason}")
        if hasattr(args, "issue_number") and args.issue_number:
            print(f"  Source: GitHub issue #{args.issue_number}")

    except Exception as e:
        db.rollback()
        print(f"Error updating state: {e}")
    finally:
        db.close()


def process_github_issues(args):
    """Process GitHub issues for repository status updates."""
    from src.community_input import TransactionProcessor

    processor = TransactionProcessor()
    try:
        if args.dry_run:
            print("Running in dry-run mode - no changes will be made")

        results = processor.process_status_update_issues(
            repo_name=getattr(args, "repo", None), dry_run=args.dry_run
        )

        print(f"\nStatus Update Processing Results:")
        print(f"  Total issues processed: {results['processed']}")
        print(f"  Successful transactions: {results['successful']}")
        print(f"  Failed transactions: {results['failed']}")

        if results["details"]:
            print("\nDetailed Results:")
            for detail in results["details"]:
                status_icon = (
                    "✅"
                    if detail["status"] == "success"
                    else "❌" if detail["status"] == "failed" else "🔍"
                )
                print(
                    f"  {status_icon} Issue #{detail['issue_number']} - {detail['repository']}: {detail['message']}"
                )

        # Show transactions summary
        if not args.dry_run and results["successful"] > 0:
            print("\nUpdated Transaction Summary:")
            summary = processor.get_transactions_summary()
            if "error" not in summary:
                print(f"  Total transactions: {summary['total_transactions']}")
                print(
                    f"  GitHub issue transactions: {summary['github_issue_transactions']}"
                )
                for status, repos in summary["status_breakdown"].items():
                    print(f"  {status.capitalize()}: {len(repos)} transitions")

    except Exception as e:
        print(f"Error processing status updates: {e}")
    finally:
        processor.close()


def process_single_github_issue(args):
    """Process a single GitHub issue for repository status update."""
    from src.community_input import GitHubIssueParser, TransactionProcessor

    issue_number = args.process_issue
    repo_name = getattr(args, "repo", None)

    print(f"Processing GitHub issue #{issue_number}...")

    parser = GitHubIssueParser()
    processor = TransactionProcessor()

    try:
        # Get the specific issue
        if not repo_name:
            repo_name = config.github_repo

        github_repo = parser.github.get_repo(repo_name)
        issue = github_repo.get_issue(issue_number)

        print(f"Found issue: {issue.title}")

        # Parse the issue body
        parsed_data = parser.parse_issue_body(issue.body)
        if not parsed_data:
            print(f"❌ Could not parse issue #{issue_number} - invalid format")
            return False

        # Add issue metadata
        parsed_data["issue_number"] = issue.number
        parsed_data["issue_title"] = issue.title
        parsed_data["issue_url"] = issue.html_url
        parsed_data["created_at"] = issue.created_at
        parsed_data["author"] = issue.user.login

        # Validate repository exists in dataset
        if not parser.validate_repository_exists(
            parsed_data["repository_owner"], parsed_data["repository_name"]
        ):
            print(
                f"❌ Repository {parsed_data['repository_owner']}/{parsed_data['repository_name']} not found in dataset"
            )
            return False

        # Create the transaction
        success, message = processor.create_status_transaction(parsed_data)

        if success:
            print(f"✅ Successfully processed issue #{issue_number}")
            print(
                f"   Repository: {parsed_data['repository_owner']}/{parsed_data['repository_name']}"
            )
            print(f"   Status: {parsed_data['new_status']}")
            print(f"   Reason: {parsed_data['status_reason']}")

            # Export the updated data
            import argparse

            export_args = argparse.Namespace(
                format="json", output="docs/swift_packages.json"
            )
            export_data(export_args)
            print("✅ Updated JSON export")

        else:
            print(f"❌ Failed to process issue #{issue_number}: {message}")
            return False

    except Exception as e:
        print(f"❌ Error processing issue #{issue_number}: {e}")
        return False
    finally:
        processor.close()

    return success


def list_states(args):
    """List all available package states."""
    from src.models import PACKAGE_STATES

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

            # Show status change transactions summary
            from src.models import StateTransition

            all_transitions = db.query(StateTransition).all()
            github_transitions = [t for t in all_transitions if t.issue_number]

            if all_transitions:
                print(f"\nStatus Change Transactions:")
                print(f"  Total transactions: {len(all_transitions)}")
                print(f"  GitHub issue transactions: {len(github_transitions)}")

                # Show breakdown by new status
                status_breakdown = {}
                for transition in all_transitions:
                    status = transition.to_state
                    if status not in status_breakdown:
                        status_breakdown[status] = 0
                    status_breakdown[status] += 1

                for status, count in status_breakdown.items():
                    print(f"    {status.capitalize()}: {count} transactions")
        else:
            print("  No completed repositories found")

    finally:
        db.close()

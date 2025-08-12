#!/usr/bin/env python3
"""
Transaction-based Status Updates for Swift Package Analysis
Processes GitHub issues to create status change transactions with metadata.
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from github import Github, GithubException

from src.config import config
from src.models import Repository, SessionLocal, PackageState, ValidationError

logger = logging.getLogger(__name__)


class GitHubIssueParser:
    """Parses GitHub issues for repository status update requests."""

    def __init__(self):
        self.github = Github(config.github_token) if config.github_token else Github()

    def parse_issue_body(self, issue_body: str) -> Optional[Dict]:
        """Parse issue body to extract repository status update information."""
        try:
            # Extract form data from issue body
            data = {}

            # Parse repository owner
            owner_match = re.search(r"### Repository Owner\s*\n\s*(.+)", issue_body)
            if owner_match:
                data["repository_owner"] = owner_match.group(1).strip()

            # Parse repository name
            name_match = re.search(r"### Repository Name\s*\n\s*(.+)", issue_body)
            if name_match:
                data["repository_name"] = name_match.group(1).strip()

            # Parse new status
            status_match = re.search(r"### New Status\s*\n\s*(.+)", issue_body)
            if status_match:
                data["new_status"] = status_match.group(1).strip().lower()

            # Parse status reason
            reason_match = re.search(
                r"### Reason for Status Change\s*\n\s*(.+)", issue_body
            )
            if reason_match:
                data["status_reason"] = reason_match.group(1).strip()

            # Parse additional context
            context_match = re.search(
                r"### Additional Context\s*\n\s*(.+?)(?=\n###|\n---|\Z)",
                issue_body,
                re.DOTALL,
            )
            if context_match:
                context = context_match.group(1).strip()
                if context and context != "_No response_":
                    data["additional_context"] = context

            # Validate required fields
            required_fields = [
                "repository_owner",
                "repository_name",
                "new_status",
                "status_reason",
            ]
            if not all(field in data for field in required_fields):
                logger.warning(
                    f"Missing required fields in issue. Found: {list(data.keys())}"
                )
                return None

            # Validate status is valid
            if data["new_status"] not in PackageState.values():
                logger.warning(
                    f"Invalid status: {data['new_status']}. Valid states: {PackageState.values()}"
                )
                return None

            return data

        except Exception as e:
            logger.error(f"Error parsing issue body: {e}")
            return None

    def validate_repository_exists(self, owner: str, name: str) -> bool:
        """Check if repository exists in our dataset."""
        db = SessionLocal()
        try:
            repo = (
                db.query(Repository)
                .filter(Repository.owner == owner, Repository.name == name)
                .first()
            )
            return repo is not None
        finally:
            db.close()

    def get_status_update_issues(self, repo_name: str = None) -> List[Dict]:
        """Get all open issues with status-update label."""
        try:
            if not repo_name:
                # Use repository from config
                repo_name = config.github_repo

            repo = self.github.get_repo(repo_name)
            issues = repo.get_issues(labels=["status-update"], state="open")

            parsed_issues = []
            for issue in issues:
                logger.info(f"Processing issue #{issue.number}: {issue.title}")

                parsed_data = self.parse_issue_body(issue.body)
                if parsed_data:
                    parsed_data["issue_number"] = issue.number
                    parsed_data["issue_title"] = issue.title
                    parsed_data["issue_url"] = issue.html_url
                    parsed_data["created_at"] = issue.created_at
                    parsed_data["author"] = issue.user.login
                    parsed_issues.append(parsed_data)
                else:
                    logger.warning(f"Could not parse issue #{issue.number}")

            return parsed_issues

        except GithubException as e:
            if e.status == 404:
                logger.error(f"Repository not found: {repo_name}")
            elif e.status == 403:
                logger.error(
                    f"Access denied to repository: {repo_name}. Check GitHub token permissions."
                )
            else:
                logger.error(f"GitHub API error ({e.status}): {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching issues: {e}")
            return []


class TransactionProcessor:
    """Processes status update transactions with metadata."""

    def __init__(self):
        self.db = SessionLocal()
        self.parser = GitHubIssueParser()

    def create_status_transaction(self, issue_data: Dict) -> Tuple[bool, str]:
        """Create a status change transaction with metadata."""
        try:
            owner = issue_data["repository_owner"]
            name = issue_data["repository_name"]
            new_status = issue_data["new_status"]
            reason = issue_data["status_reason"]
            issue_number = issue_data["issue_number"]
            author = issue_data.get("author", "unknown")
            issue_url = issue_data.get("issue_url")

            # Find repository
            repo = (
                self.db.query(Repository)
                .filter(Repository.owner == owner, Repository.name == name)
                .first()
            )

            if not repo:
                return False, f"Repository {owner}/{name} not found in dataset"

            # Create transaction with metadata
            old_status, new_state = repo.transition_state(
                new_status,
                reason=reason,
                changed_by=author,
                issue_number=str(issue_number),
                session=self.db,
            )

            # Add GitHub issue URL to the transaction log for reference
            if issue_url:
                from src.models import StateTransition

                latest_transition = (
                    self.db.query(StateTransition)
                    .filter(StateTransition.repository_id == repo.id)
                    .order_by(StateTransition.created_at.desc())
                    .first()
                )
                if latest_transition and latest_transition.issue_number == str(
                    issue_number
                ):
                    # Store the issue URL in the reason field along with the original reason
                    latest_transition.reason = f"{reason} | GitHub Issue: {issue_url}"

            self.db.commit()

            logger.info(
                f"Transaction created: {owner}/{name}: {old_status} → {new_state} (issue #{issue_number} by {author})"
            )
            return (
                True,
                f"Successfully created transaction for {owner}/{name} status change to {new_state}",
            )

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating status transaction: {e}")
            return False, f"Transaction error: {str(e)}"

    def process_status_update_issues(
        self, repo_name: str = None, dry_run: bool = False
    ) -> Dict:
        """Process all open status update issues and create transactions."""
        issues = self.parser.get_status_update_issues(repo_name)

        results = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "details": [],
        }

        for issue_data in issues:
            results["processed"] += 1

            # Validate repository exists in dataset
            if not self.parser.validate_repository_exists(
                issue_data["repository_owner"], issue_data["repository_name"]
            ):
                result = {
                    "issue_number": issue_data["issue_number"],
                    "repository": f"{issue_data['repository_owner']}/{issue_data['repository_name']}",
                    "status": "failed",
                    "message": "Repository not found in dataset",
                }
                results["details"].append(result)
                results["failed"] += 1
                continue

            if dry_run:
                result = {
                    "issue_number": issue_data["issue_number"],
                    "repository": f"{issue_data['repository_owner']}/{issue_data['repository_name']}",
                    "status": "dry_run",
                    "message": f"Would create transaction for status: {issue_data['new_status']}",
                }
                results["details"].append(result)
                results["successful"] += 1
            else:
                # Create the transaction
                success, message = self.create_status_transaction(issue_data)

                result = {
                    "issue_number": issue_data["issue_number"],
                    "repository": f"{issue_data['repository_owner']}/{issue_data['repository_name']}",
                    "status": "success" if success else "failed",
                    "message": message,
                }
                results["details"].append(result)

                if success:
                    results["successful"] += 1
                else:
                    results["failed"] += 1

        return results

    def get_transactions_summary(self) -> Dict:
        """Get summary of all status change transactions."""
        try:
            from src.models import StateTransition

            # Get all state transitions with metadata
            transactions = self.db.query(StateTransition).all()

            # Separate GitHub issue-based transactions from others
            github_transactions = [t for t in transactions if t.issue_number]
            total_transactions = len(transactions)
            github_transaction_count = len(github_transactions)

            # Group by new status
            status_breakdown = {}
            for transition in transactions:
                status = transition.to_state
                if status not in status_breakdown:
                    status_breakdown[status] = []

                # Get repository info
                repo = (
                    self.db.query(Repository)
                    .filter(Repository.id == transition.repository_id)
                    .first()
                )

                transaction_data = {
                    "repository_url": transition.repository_url,
                    "from_state": transition.from_state,
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

                # Add repository details if available
                if repo:
                    transaction_data["owner"] = repo.owner
                    transaction_data["name"] = repo.name

                status_breakdown[status].append(transaction_data)

            return {
                "total_transactions": total_transactions,
                "github_issue_transactions": github_transaction_count,
                "status_breakdown": status_breakdown,
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating transactions summary: {e}")
            return {"error": str(e)}

    def close(self):
        """Close database connection."""
        self.db.close()

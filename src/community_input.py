#!/usr/bin/env python3
"""
Community Input Processing for Swift Package Analysis
Processes GitHub issues to update repository status based on community feedback.
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
from github import Github, GithubException

from src.config import config
from src.models import Repository, SessionLocal, PACKAGE_STATES

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
            if data["new_status"] not in PACKAGE_STATES:
                logger.warning(f"Invalid status: {data['new_status']}")
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
                # Use current repository - extract from git remote or config
                repo_name = (
                    "Jake-Prickett/spm-android-support-tracking"  # Default fallback
                )

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
            logger.error(f"GitHub API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching issues: {e}")
            return []


class CommunityStatusProcessor:
    """Processes community input to update repository status."""

    def __init__(self):
        self.db = SessionLocal()
        self.parser = GitHubIssueParser()

    def update_repository_status(self, issue_data: Dict) -> Tuple[bool, str]:
        """Update repository status based on community input."""
        try:
            owner = issue_data["repository_owner"]
            name = issue_data["repository_name"]
            new_status = issue_data["new_status"]
            reason = issue_data["status_reason"]
            issue_number = issue_data["issue_number"]

            # Find repository
            repo = (
                self.db.query(Repository)
                .filter(Repository.owner == owner, Repository.name == name)
                .first()
            )

            if not repo:
                return False, f"Repository {owner}/{name} not found in dataset"

            # Check if already has community status
            if repo.community_status:
                return (
                    False,
                    f"Repository {owner}/{name} already has community status: {repo.community_status} (issue #{repo.marked_by_issue})",
                )

            # Update repository with community input
            old_status = repo.current_state
            repo.community_status = new_status
            repo.marked_by_issue = str(issue_number)
            repo.status_reason = reason
            repo.marked_date = datetime.utcnow()

            # Also update the current_state to reflect community input
            repo.current_state = new_status

            self.db.commit()

            logger.info(
                f"Updated {owner}/{name}: {old_status} → {new_status} (issue #{issue_number})"
            )
            return True, f"Successfully updated {owner}/{name} status to {new_status}"

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating repository status: {e}")
            return False, f"Database error: {str(e)}"

    def process_status_update_issues(
        self, repo_name: str = None, dry_run: bool = False
    ) -> Dict:
        """Process all open status update issues."""
        issues = self.parser.get_status_update_issues(repo_name)

        results = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
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
                    "message": f"Would update to: {issue_data['new_status']}",
                }
                results["details"].append(result)
                results["successful"] += 1
            else:
                # Process the update
                success, message = self.update_repository_status(issue_data)

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

    def get_community_contributions_summary(self) -> Dict:
        """Get summary of all community contributions."""
        try:
            # Count repositories with community status
            total_community_updates = (
                self.db.query(Repository)
                .filter(Repository.community_status.isnot(None))
                .count()
            )

            # Group by community status
            status_counts = {}
            community_repos = (
                self.db.query(Repository)
                .filter(Repository.community_status.isnot(None))
                .all()
            )

            for repo in community_repos:
                status = repo.community_status
                if status not in status_counts:
                    status_counts[status] = []

                status_counts[status].append(
                    {
                        "owner": repo.owner,
                        "name": repo.name,
                        "reason": repo.status_reason,
                        "issue": repo.marked_by_issue,
                        "date": repo.marked_date.isoformat()
                        if repo.marked_date
                        else None,
                    }
                )

            return {
                "total_community_updates": total_community_updates,
                "status_breakdown": status_counts,
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error generating community summary: {e}")
            return {"error": str(e)}

    def close(self):
        """Close database connection."""
        self.db.close()

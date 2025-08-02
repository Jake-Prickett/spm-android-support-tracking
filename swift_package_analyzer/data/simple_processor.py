"""
Simplified data processor with timestamp-based chunked refresh.
No checkpoints or complex resume logic - just process oldest 250 repositories.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from swift_package_analyzer.core.models import Repository, SessionLocal
from swift_package_analyzer.data.fetcher import DataProcessor

logger = logging.getLogger(__name__)


class SimpleChunkedProcessor(DataProcessor):
    """Simplified processor that refreshes repositories in 250-repo chunks based on staleness."""
    
    def get_repositories_for_refresh(self, all_urls: List[str], chunk_size: int = 250) -> List[str]:
        """Get the oldest repositories that need refreshing, up to chunk_size."""
        db = SessionLocal()
        try:
            # Get repositories ordered by staleness (never fetched first, then oldest first)
            stale_repos = (
                db.query(Repository)
                .filter(Repository.url.in_(all_urls))
                .order_by(
                    Repository.last_fetched.asc().nullsfirst(),  # Never fetched first
                    Repository.updated_at.asc().nullsfirst()     # Then oldest updates
                )
                .limit(chunk_size)
                .all()
            )
            
            stale_urls = [repo.url for repo in stale_repos]
            
            # Add any new URLs that aren't in the database yet
            existing_urls = {repo.url for repo in db.query(Repository.url).all()}
            new_urls = [url for url in all_urls if url not in existing_urls]
            
            # Combine new URLs with stale URLs, limiting to chunk_size
            urls_to_process = new_urls + stale_urls
            urls_to_process = urls_to_process[:chunk_size]
            
            logger.info(f"Selected {len(urls_to_process)} repositories for refresh "
                       f"({len(new_urls)} new, {len(stale_urls)} existing)")
            
            return urls_to_process
            
        finally:
            db.close()
    
    def process_chunk(self, all_urls: List[str], chunk_size: int = 250) -> dict:
        """Process a chunk of repositories (up to chunk_size) that need refreshing."""
        
        # Get repositories that need refreshing
        urls_to_process = self.get_repositories_for_refresh(all_urls, chunk_size)
        
        if not urls_to_process:
            logger.info("No repositories need refreshing at this time")
            return {'success': 0, 'error': 0, 'skipped': len(all_urls)}
        
        logger.info(f"Processing {len(urls_to_process)} repositories in chunk")
        
        # Process the chunk using parent class method
        results = self.process_batch(urls_to_process)
        
        logger.info(f"Chunk completed: {results['success']} success, {results['error']} errors")
        
        return {
            'success': results['success'],
            'error': results['error'],
            'processed': len(urls_to_process),
            'total_available': len(all_urls)
        }
    
    def get_refresh_status(self) -> dict:
        """Get status of repositories by freshness."""
        db = SessionLocal()
        try:
            total_repos = db.query(Repository).count()
            
            # Count by staleness
            now = datetime.utcnow()
            one_day_ago = now - timedelta(days=1)
            one_week_ago = now - timedelta(days=7)
            
            fresh_repos = (
                db.query(Repository)
                .filter(Repository.last_fetched > one_day_ago)
                .count()
            )
            
            recent_repos = (
                db.query(Repository)
                .filter(
                    Repository.last_fetched <= one_day_ago,
                    Repository.last_fetched > one_week_ago
                )
                .count()
            )
            
            stale_repos = (
                db.query(Repository)
                .filter(Repository.last_fetched <= one_week_ago)
                .count()
            )
            
            never_fetched = (
                db.query(Repository)
                .filter(Repository.last_fetched.is_(None))
                .count()
            )
            
            completed_repos = (
                db.query(Repository)
                .filter(Repository.processing_status == 'completed')
                .count()
            )
            
            return {
                'total_repositories': total_repos,
                'completed_repositories': completed_repos,
                'freshness': {
                    'fresh_1_day': fresh_repos,
                    'recent_1_week': recent_repos, 
                    'stale_older': stale_repos,
                    'never_fetched': never_fetched
                }
            }
            
        finally:
            db.close()
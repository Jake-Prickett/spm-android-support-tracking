"""
Enhanced data processor with smart resume and incremental update capabilities.
"""

import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from swift_package_analyzer.core.config import config
from swift_package_analyzer.core.models import (
    ProcessingCheckpoint, 
    ProcessingLog, 
    Repository, 
    SessionLocal
)
from swift_package_analyzer.data.fetcher import DataProcessor

logger = logging.getLogger(__name__)


class IncrementalDataProcessor(DataProcessor):
    """Enhanced DataProcessor with smart resume and checkpoint management."""
    
    def __init__(self):
        super().__init__()
        self.session_id = str(uuid.uuid4())
        self.current_checkpoint = None
        self.start_time = datetime.utcnow()
        
    def should_update_repository(self, repo_url: str) -> bool:
        """Determine if a repository needs updating based on staleness criteria."""
        db = SessionLocal()
        try:
            repo = db.query(Repository).filter(Repository.url == repo_url).first()
            
            if not repo:
                # New repository, needs processing
                return True
                
            if repo.processing_status in ['pending', 'error']:
                # Failed or incomplete processing
                return True
                
            if not repo.last_fetched:
                # Never been fetched
                return True
                
            # Check staleness based on repository activity and configuration
            staleness_threshold = timedelta(days=config.staleness_threshold_days)
            
            # More frequent updates for popular repositories
            if repo.stars and repo.stars > config.popular_repo_threshold_stars:
                staleness_threshold = timedelta(days=config.popular_repo_staleness_days)
            elif repo.stars and repo.stars > (config.popular_repo_threshold_stars // 10):
                staleness_threshold = timedelta(days=config.popular_repo_staleness_days + 2)
                
            time_since_update = datetime.utcnow() - repo.last_fetched
            should_update = time_since_update > staleness_threshold
            
            if should_update:
                logger.debug(f"Repository {repo_url} needs update (last fetched {time_since_update.days} days ago)")
            
            return should_update
            
        finally:
            db.close()
    
    def get_repositories_for_incremental_update(self, all_urls: List[str], batch_size: int) -> List[str]:
        """Get list of repositories that need updating, prioritizing by staleness and importance."""
        urls_needing_update = []
        
        for url in all_urls:
            if self.should_update_repository(url):
                urls_needing_update.append(url)
                
        # Sort by priority: new repos first, then by staleness
        def priority_key(url):
            db = SessionLocal()
            try:
                repo = db.query(Repository).filter(Repository.url == url).first()
                if not repo:
                    return (0, 0)  # New repos get highest priority
                
                staleness_days = 0
                if repo.last_fetched:
                    staleness_days = (datetime.utcnow() - repo.last_fetched).days
                    
                # Prioritize popular repos that are stale
                popularity_score = (repo.stars or 0) + (repo.forks or 0) * 2
                return (1, -staleness_days, -popularity_score)  # Sort ascending
                
            finally:
                db.close()
        
        urls_needing_update.sort(key=priority_key)
        
        logger.info(f"Found {len(urls_needing_update)} repositories needing updates out of {len(all_urls)} total")
        return urls_needing_update[:batch_size * 10]  # Return reasonable subset
        
    def find_last_checkpoint(self) -> Optional[ProcessingCheckpoint]:
        """Find the most recent interrupted processing session to resume."""
        db = SessionLocal()
        try:
            # Look for interrupted sessions from the last 24 hours
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            checkpoint = (
                db.query(ProcessingCheckpoint)
                .filter(
                    ProcessingCheckpoint.status == 'active',
                    ProcessingCheckpoint.processing_started_at > cutoff_time
                )
                .order_by(ProcessingCheckpoint.processing_started_at.desc())
                .first()
            )
            
            if checkpoint:
                logger.info(f"Found resumable session {checkpoint.session_id} with {checkpoint.repositories_processed} repositories processed")
                
            return checkpoint
            
        finally:
            db.close()
    
    def create_checkpoint(self, batch_number: int, total_repositories: int, batch_size: int) -> ProcessingCheckpoint:
        """Create a new processing checkpoint."""
        db = SessionLocal()
        try:
            checkpoint = ProcessingCheckpoint(
                session_id=self.session_id,
                batch_number=batch_number,
                batch_size=batch_size,
                total_repositories=total_repositories,
                status='active'
            )
            
            db.add(checkpoint)
            db.commit()
            db.refresh(checkpoint)
            
            self.current_checkpoint = checkpoint
            logger.info(f"Created checkpoint for session {self.session_id}, batch {batch_number}")
            
            return checkpoint
            
        finally:
            db.close()
    
    def update_checkpoint(self, repositories_processed: int, last_processed_url: str, 
                         success_count: int, error_count: int, api_requests: int):
        """Update the current checkpoint with progress information."""
        if not self.current_checkpoint:
            return
            
        db = SessionLocal()
        try:
            checkpoint = db.query(ProcessingCheckpoint).filter(
                ProcessingCheckpoint.id == self.current_checkpoint.id
            ).first()
            
            if checkpoint:
                checkpoint.repositories_processed = repositories_processed
                checkpoint.last_processed_url = last_processed_url
                checkpoint.success_count = success_count
                checkpoint.error_count = error_count
                checkpoint.api_requests_made = api_requests
                
                # Estimate remaining time
                elapsed_time = (datetime.utcnow() - checkpoint.processing_started_at).total_seconds() / 60
                if repositories_processed > 0:
                    rate = repositories_processed / elapsed_time
                    remaining_repos = checkpoint.total_repositories - repositories_processed
                    checkpoint.estimated_remaining_time = remaining_repos / rate if rate > 0 else None
                
                db.commit()
                
        finally:
            db.close()
    
    def complete_checkpoint(self):
        """Mark the current checkpoint as completed."""
        if not self.current_checkpoint:
            return
            
        db = SessionLocal()
        try:
            checkpoint = db.query(ProcessingCheckpoint).filter(
                ProcessingCheckpoint.id == self.current_checkpoint.id
            ).first()
            
            if checkpoint:
                checkpoint.status = 'completed'
                checkpoint.processing_ended_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"Completed checkpoint for session {self.session_id}")
                
        finally:
            db.close()
    
    def cleanup_old_checkpoints(self):
        """Clean up old checkpoint records to prevent database bloat."""
        db = SessionLocal()
        try:
            # Remove checkpoints older than configured days
            cutoff_time = datetime.utcnow() - timedelta(days=config.checkpoint_cleanup_days)
            
            deleted_count = (
                db.query(ProcessingCheckpoint)
                .filter(ProcessingCheckpoint.processing_started_at < cutoff_time)
                .delete()
            )
            
            if deleted_count > 0:
                db.commit()
                logger.info(f"Cleaned up {deleted_count} old checkpoint records")
                
        finally:
            db.close()
    
    def process_incremental_batch(self, urls: List[str], batch_size: int, 
                                 max_batches: Optional[int] = None,
                                 resume_from_checkpoint: bool = True) -> Dict[str, int]:
        """Process repositories incrementally with smart resume capability."""
        
        # Clean up old checkpoints first
        self.cleanup_old_checkpoints()
        
        # Check for resumable session
        resume_checkpoint = None
        if resume_from_checkpoint:
            resume_checkpoint = self.find_last_checkpoint()
        
        # Get repositories that need updating
        repositories_to_process = self.get_repositories_for_incremental_update(urls, batch_size * (max_batches or 50))
        
        if not repositories_to_process:
            logger.info("No repositories need updating at this time")
            return {'success': 0, 'error': 0, 'skipped': len(urls)}
        
        total_repositories = len(repositories_to_process)
        processed_count = 0
        batch_count = 0
        total_success = 0
        total_errors = 0
        
        # Resume from checkpoint if available
        if resume_checkpoint:
            batch_count = resume_checkpoint.batch_number
            processed_count = resume_checkpoint.repositories_processed
            total_success = resume_checkpoint.success_count
            total_errors = resume_checkpoint.error_count
            self.current_checkpoint = resume_checkpoint
            
            # Skip already processed repositories
            repositories_to_process = repositories_to_process[processed_count:]
            logger.info(f"Resuming from checkpoint: batch {batch_count}, {processed_count} repositories already processed")
        
        logger.info(f"Processing {len(repositories_to_process)} repositories in incremental mode")
        
        # Process in batches
        for i in range(0, len(repositories_to_process), batch_size):
            if max_batches and batch_count >= max_batches:
                logger.info(f"Reached maximum batch limit of {max_batches}")
                break
                
            batch = repositories_to_process[i:i + batch_size]
            batch_count += 1
            
            # Create or update checkpoint
            if not self.current_checkpoint:
                self.create_checkpoint(batch_count, total_repositories, batch_size)
            
            logger.info(f"Processing incremental batch {batch_count} ({len(batch)} repositories)...")
            
            # Process the batch using parent class method
            batch_results = self.process_batch(batch)
            
            # Update counters
            batch_processed = len(batch)
            processed_count += batch_processed
            total_success += batch_results['success']
            total_errors += batch_results['error']
            
            # Update checkpoint
            last_url = batch[-1] if batch else None
            self.update_checkpoint(
                processed_count, 
                last_url, 
                total_success, 
                total_errors,
                self.github_fetcher.request_count
            )
            
            logger.info(f"Batch {batch_count}: {batch_results['success']} success, {batch_results['error']} errors "
                       f"({processed_count}/{total_repositories} total)")
            
            # Rate limiting delay between batches
            if i + batch_size < len(repositories_to_process) and (not max_batches or batch_count < max_batches):
                logger.info(f"Waiting {config.batch_delay_minutes} minutes before next batch...")
                time.sleep(config.batch_delay_minutes * 60)
        
        # Complete the checkpoint
        self.complete_checkpoint()
        
        return {
            'success': total_success,
            'error': total_errors,
            'processed': processed_count,
            'batches': batch_count
        }
    
    def get_processing_status(self) -> Dict:
        """Get comprehensive processing status including checkpoint information."""
        status = super().get_processing_stats()
        
        # Add checkpoint information
        db = SessionLocal()
        try:
            # Active checkpoints
            active_checkpoints = (
                db.query(ProcessingCheckpoint)
                .filter(ProcessingCheckpoint.status == 'active')
                .count()
            )
            
            # Recent activity
            recent_checkpoint = (
                db.query(ProcessingCheckpoint)
                .order_by(ProcessingCheckpoint.processing_started_at.desc())
                .first()
            )
            
            status['checkpoint_info'] = {
                'active_sessions': active_checkpoints,
                'last_session_id': recent_checkpoint.session_id if recent_checkpoint else None,
                'last_session_progress': {
                    'repositories_processed': recent_checkpoint.repositories_processed if recent_checkpoint else 0,
                    'estimated_remaining_minutes': recent_checkpoint.estimated_remaining_time if recent_checkpoint else None,
                    'started_at': recent_checkpoint.processing_started_at.isoformat() if recent_checkpoint else None
                } if recent_checkpoint else None
            }
            
            return status
            
        finally:
            db.close()
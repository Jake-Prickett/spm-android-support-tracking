'use client';

import { useState, useMemo } from 'react';
import { Repository } from '@/types/repository';
import RepositoryCard from './RepositoryCard';

interface RepositoryListProps {
  repositories: Repository[];
}

export default function RepositoryList({ repositories }: RepositoryListProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredRepositories = useMemo(() => {
    if (!searchQuery.trim()) {
      return repositories;
    }

    const query = searchQuery.toLowerCase();
    return repositories.filter(repo => 
      repo.name.toLowerCase().includes(query) ||
      repo.owner.toLowerCase().includes(query) ||
      repo.description?.toLowerCase().includes(query) 
    );
  }, [repositories, searchQuery]);

  return (
    <section className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="relative max-w-md flex-1">
          <label htmlFor="search" className="sr-only">
            Search packages
          </label>
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-4 w-4" style={{ color: 'var(--text-tertiary)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            type="text"
            id="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search packages..."
            aria-label="Search packages by name, owner, or description"
            className="w-full pl-10 pr-4 py-2.5 rounded-lg border transition-colors duration-200 focus:outline-none focus:ring-2 text-sm"
            style={{ 
              backgroundColor: 'var(--surface)',
              borderColor: 'var(--border)',
              color: 'var(--text-primary)'
            }}
          />
        </div>
        <div className="text-sm" style={{ color: 'var(--text-secondary)' }} aria-live="polite">
          {filteredRepositories.length} of {repositories.length} packages
        </div>
      </div>

      <div className="space-y-3" role="list">
        {filteredRepositories.map((repo) => (
          <RepositoryCard key={repo.url} repository={repo} />
        ))}
      </div>

      {filteredRepositories.length === 0 && searchQuery.trim() && (
        <div className="text-center py-12" role="status" aria-live="polite">
          <div className="text-4xl mb-4" aria-hidden="true">📦</div>
          <h3 className="text-lg font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
            No packages found
          </h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            Try adjusting your search criteria
          </p>
        </div>
      )}
    </section>
  );
}
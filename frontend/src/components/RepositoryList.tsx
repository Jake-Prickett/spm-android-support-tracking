'use client';

import { Repository } from '@/types/repository';
import RepositoryCard from './RepositoryCard';
import { useState, useMemo } from 'react';

interface RepositoryListProps {
  repositories: Repository[];
}

type SortOption = 'name' | 'stars' | 'updated' | 'pushed';
type FilterOption = 'all' | 'android-compatible' | 'android-incompatible';

export default function RepositoryList({ repositories }: RepositoryListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortOption>('stars');
  const [filterBy, setFilterBy] = useState<FilterOption>('all');

  const filteredAndSortedRepositories = useMemo(() => {
    let filtered = repositories;

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(repo => 
        repo.name.toLowerCase().includes(query) ||
        repo.owner.toLowerCase().includes(query) ||
        (repo.description?.toLowerCase().includes(query) ?? false)
      );
    }

    // Apply status filter
    if (filterBy !== 'all') {
      filtered = filtered.filter(repo => {
        if (filterBy === 'android-compatible') return repo.android_compatible;
        if (filterBy === 'android-incompatible') return !repo.android_compatible;
        return true;
      });
    }

    // Apply sorting
    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'stars':
          return b.stars - a.stars;
        case 'updated':
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
        case 'pushed':
          const aPushed = a.pushed_at ? new Date(a.pushed_at).getTime() : 0;
          const bPushed = b.pushed_at ? new Date(b.pushed_at).getTime() : 0;
          return bPushed - aPushed;
        default:
          return 0;
      }
    });

    return sorted;
  }, [repositories, searchQuery, sortBy, filterBy]);

  return (
    <section className="space-y-5">
      {/* Search and Filter Controls */}
      <div className="space-y-4">
        {/* Search Input */}
        <div className="relative">
          <input
            type="text"
            placeholder="Search repositories by name, owner, or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-3 pr-10 rounded-lg border text-sm"
            style={{ 
              backgroundColor: 'var(--surface)',
              borderColor: 'var(--border)',
              color: 'var(--text-primary)'
            }}
          />
          <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
            <svg className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        {/* Filter and Sort Controls */}
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Status Filter */}
          <label className="flex items-center gap-2">
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              Status:
            </span>
            <select
              value={filterBy}
              onChange={(e) => setFilterBy(e.target.value as FilterOption)}
              className="px-3 py-2 rounded-md border text-sm"
              style={{ 
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border)',
                color: 'var(--text-primary)'
              }}
            >
              <option value="all">All packages</option>
              <option value="android-compatible">Android compatible</option>
              <option value="android-incompatible">Android incompatible</option>
            </select>
          </label>

          {/* Sort Options */}
          <label className="flex items-center gap-2">
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              Sort by:
            </span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="px-3 py-2 rounded-md border text-sm"
              style={{ 
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border)',
                color: 'var(--text-primary)'
              }}
            >
              <option value="stars">Stars (high to low)</option>
              <option value="name">Name (A to Z)</option>
              <option value="updated">Recently updated</option>
              <option value="pushed">Recently pushed</option>
            </select>
          </label>
        </div>
      </div>

      {/* Results Count */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          {filteredAndSortedRepositories.length} of {repositories.length} packages
          {searchQuery && ` matching "${searchQuery}"`}
        </div>
      </div>

      {/* Repository List */}
      <div className="space-y-3" role="list">
        {filteredAndSortedRepositories.length > 0 ? (
          filteredAndSortedRepositories.map((repo) => (
            <RepositoryCard key={repo.url} repository={repo} />
          ))
        ) : (
          <div className="text-center py-12">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-lg font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
              No packages found
            </h3>
            <p style={{ color: 'var(--text-secondary)' }}>
              Try adjusting your search query or filters
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
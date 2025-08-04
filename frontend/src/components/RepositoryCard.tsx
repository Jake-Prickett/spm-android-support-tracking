'use client';

import { useState } from 'react';
import { Repository } from '@/types/repository';
import { formatRelativeDate } from '@/utils/dateUtils';
import StatusTag from '@/components/StatusTag';
import AndroidStatusTag from '@/components/AndroidStatusTag';

interface RepositoryCardProps {
  repository: Repository;
}

export default function RepositoryCard({ repository }: RepositoryCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <article
      className="rounded-lg border transition-all duration-200 hover:shadow-sm"
      style={{ 
        backgroundColor: 'var(--surface)',
        borderColor: 'var(--border)'
      }}
      role="listitem"
    >
      <div className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-base font-semibold truncate">
                <a
                  href={repository.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="transition-colors duration-200"
                  style={{ 
                    color: isHovered ? 'var(--accent)' : 'var(--text-primary)',
                    textDecoration: 'none'
                  }}
                  onMouseEnter={() => setIsHovered(true)}
                  onMouseLeave={() => setIsHovered(false)}
                  aria-label={`Visit ${repository.owner}/${repository.name} on GitHub`}
                >
                  {repository.owner}/{repository.name}
                </a>
              </h3>
            </div>
            {repository.description && (
              <p className="text-sm mb-3 line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
                {repository.description}
              </p>
            )}
            
            <div className="flex items-center gap-4 text-xs flex-wrap" style={{ color: 'var(--text-tertiary)' }}>
              <div className="flex items-center gap-1" title={`${repository.stars?.toLocaleString() || '0'} stars`}>
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                <span aria-label={`${repository.stars?.toLocaleString() || '0'} stars`}>
                  {repository.stars?.toLocaleString() || '0'}
                </span>
              </div>
              <div className="flex items-center gap-1" title={`${repository.forks?.toLocaleString() || '0'} forks`}>
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path fillRule="evenodd" d="M7.707 3.293a1 1 0 010 1.414L5.414 7H11a7 7 0 017 7v2a1 1 0 11-2 0v-2a5 5 0 00-5-5H5.414l2.293 2.293a1 1 0 11-1.414 1.414L2.586 7a2 2 0 010-2.828l3.707-3.707a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                <span aria-label={`${repository.forks?.toLocaleString() || '0'} forks`}>
                  {repository.forks?.toLocaleString() || '0'}
                </span>
              </div>
              {repository.language && (
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--accent)' }} aria-hidden="true"></span>
                  {repository.language}
                </span>
              )}
              {repository.swift_tools_version && (
                <span>Swift {repository.swift_tools_version}</span>
              )}
              {repository.dependencies_count > 0 && (
                <span>{repository.dependencies_count} deps</span>
              )}
              <span title={`Last updated: ${repository.updated_at}`}>
                Updated {formatRelativeDate(repository.updated_at)}
              </span>
              {repository.pushed_at && (
                <span title={`Last pushed: ${repository.pushed_at}`}>
                  Pushed {formatRelativeDate(repository.pushed_at)}
                </span>
              )}
            </div>
          </div>
          
          <div className="flex gap-2 ml-4 flex-shrink-0">
            <StatusTag repository={repository} />
            <AndroidStatusTag repository={repository} />
          </div>
        </div>
      </div>
    </article>
  );
}
'use client';

import { Repository } from '@/types/repository';

interface StatusTagProps {
  repository: Repository;
}

export default function StatusTag({ repository }: StatusTagProps) {
  const getStatusColor = (state: string) => {
    switch (state.toLowerCase()) {
      case 'android_supported':
      case 'supported':
      case 'complete':
        return 'var(--success)';
      case 'in_progress':
      case 'in-progress':
      case 'tracking':
      case 'pending':
        return 'var(--warning)';
      case 'blocked':
      case 'archived':
      case 'irrelevant':
      case 'unsupported':
      case 'failed':
        return 'var(--error)';
      case 'dependency':
        return 'var(--info, #3b82f6)';
      case 'unknown':
      default:
        return 'var(--text-tertiary)';
    }
  };

  return (
    <span 
      className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium"
      style={{ 
        backgroundColor: getStatusColor(repository.current_state),
        color: 'white'
      }}
    >
      {repository.current_state}
    </span>
  );
}
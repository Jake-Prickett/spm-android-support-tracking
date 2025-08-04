'use client';

import { Repository } from '@/types/repository';

interface StatusTagProps {
  repository: Repository;
}

export default function StatusTag({ repository }: StatusTagProps) {
  const getStatusColor = (state: string) => {
    switch (state.toLowerCase()) {
      case 'ready':
      case 'complete':
      case 'supported':
        return 'var(--success)';
      case 'in-progress':
      case 'pending':
        return 'var(--warning)';
      case 'blocked':
      case 'unsupported':
      case 'failed':
        return 'var(--error)';
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
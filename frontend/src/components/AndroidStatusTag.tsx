'use client';

import { Repository } from '@/types/repository';

interface AndroidStatusTagProps {
  repository: Repository;
}

export default function AndroidStatusTag({ repository }: AndroidStatusTagProps) {
  if (repository.android_compatible) {
    return (
      <span 
        className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium"
        style={{ 
          backgroundColor: 'var(--success)',
          color: 'white'
        }}
      >
        Android
      </span>
    );
  }

  return (
    <span 
      className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium"
      style={{ 
        backgroundColor: 'var(--error)',
        color: 'white'
      }}
    >
      Android
    </span>
  );
}
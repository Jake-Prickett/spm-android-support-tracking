import { Repository } from '@/types/repository';
import RepositoryCard from './RepositoryCard';

interface RepositoryListProps {
  repositories: Repository[];
}

export default function RepositoryList({ repositories }: RepositoryListProps) {
  return (
    <section className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          {repositories.length} packages
        </div>
      </div>

      <div className="space-y-3" role="list">
        {repositories.map((repo) => (
          <RepositoryCard key={repo.url} repository={repo} />
        ))}
      </div>
    </section>
  );
}
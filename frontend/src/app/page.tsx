import RepositoryList from '@/components/RepositoryList';
import { Repository } from '@/types/repository';
import { promises as fs } from 'fs';
import path from 'path';

async function getRepositories(): Promise<Repository[]> {
  try {
    const jsonPath = path.join(process.cwd(), '..', 'docs', 'swift_packages.json');
    const fileContents = await fs.readFile(jsonPath, 'utf8');
    return JSON.parse(fileContents);
  } catch (error) {
    console.error('Error loading repositories:', error);
    return [];
  }
}

export default async function Home() {
  try {
    const repositories = await getRepositories();

    return (
      <div className="min-h-screen" style={{ backgroundColor: 'var(--surface-secondary)' }}>
        <header className="border-b" style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)' }}>
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: 'var(--accent)' }} aria-hidden="true">
                <span className="text-white font-bold text-sm">SPM</span>
              </div>
              <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>
                Swift Package Manager
              </h1>
            </div>
            <h2 className="text-lg font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
              Android Support Tracking
            </h2>
            <p style={{ color: 'var(--text-secondary)' }} className="text-sm">
              Linux-compatible Swift packages that lack Android support • {repositories.length} packages
            </p>
          </div>
        </header>

        <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <RepositoryList repositories={repositories} />
        </main>
      </div>
    );
  } catch {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--surface-secondary)' }}>
        <div className="text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h1 className="text-xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
            Unable to Load Repository Data
          </h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Please ensure the data file exists and try refreshing the page.
          </p>
        </div>
      </div>
    );
  }
}

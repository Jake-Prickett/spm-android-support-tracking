import RepositoryList from '@/components/RepositoryList';
import { Repository } from '@/types/repository';
import { promises as fs } from 'fs';
import path from 'path';

async function getRepositories(): Promise<Repository[]> {
  try {
    const jsonPath = path.join(process.cwd(), 'public', 'swift_packages.json');
    const fileContents = await fs.readFile(jsonPath, 'utf8');
    const data = JSON.parse(fileContents);
    
    // Extract repositories from the new data structure
    if (data.all_repositories && Array.isArray(data.all_repositories)) {
      return data.all_repositories;
    } else if (data.priority_repositories && Array.isArray(data.priority_repositories)) {
      return data.priority_repositories;
    } else if (Array.isArray(data)) {
      return data;
    }
    
    console.warn('Unexpected data structure:', Object.keys(data));
    return [];
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
              <div className="w-8 h-8 flex items-center justify-center" aria-hidden="true">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" className="w-8 h-8">
                  <path fill="#f05138" d="M126.33 34.06a39.32 39.32 0 00-.79-7.83 28.78 28.78 0 00-2.65-7.58 28.84 28.84 0 00-4.76-6.32 23.42 23.42 0 00-6.62-4.55 27.27 27.27 0 00-7.68-2.53c-2.65-.51-5.56-.51-8.21-.76H30.25a45.46 45.46 0 00-6.09.51 21.82 21.82 0 00-5.82 1.52c-.53.25-1.32.51-1.85.76a33.82 33.82 0 00-5 3.28c-.53.51-1.06.76-1.59 1.26a22.41 22.41 0 00-4.76 6.32 23.61 23.61 0 00-2.65 7.58 78.5 78.5 0 00-.79 7.83v60.39a39.32 39.32 0 00.79 7.83 28.78 28.78 0 002.65 7.58 28.84 28.84 0 004.76 6.32 23.42 23.42 0 006.62 4.55 27.27 27.27 0 007.68 2.53c2.65.51 5.56.51 8.21.76h63.22a45.08 45.08 0 008.21-.76 27.27 27.27 0 007.68-2.53 30.13 30.13 0 006.62-4.55 22.41 22.41 0 004.76-6.32 23.61 23.61 0 002.65-7.58 78.49 78.49 0 00.79-7.83V34.06z"/>
                  <path fill="#fefefe" d="M85 96.5c-11.11 6.13-26.38 6.76-41.75.47A64.53 64.53 0 0113.84 73a50 50 0 0010.85 6.32c15.87 7.1 31.73 6.61 42.9 0-15.9-11.66-29.4-26.82-39.46-39.2a43.47 43.47 0 01-5.29-6.82c12.16 10.61 31.5 24 38.38 27.79a271.77 271.77 0 01-27-32.34 266.8 266.8 0 0044.47 34.87c.71.38 1.26.7 1.7 1a32.7 32.7 0 001.21-3.51c3.71-12.89-.53-27.54-9.79-39.67C93.25 33.81 106 57.05 100.66 76.51c-.14.53-.29 1-.45 1.55l.19.22c10.59 12.63 7.68 26 6.35 23.5C101 91 90.37 94.33 85 96.5z"/>
                </svg>
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

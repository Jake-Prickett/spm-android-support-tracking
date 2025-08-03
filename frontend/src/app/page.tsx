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
  const repositories = await getRepositories();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Swift Package Manager - Android Support Tracking
          </h1>
          <p className="mt-2 text-gray-600">
            Linux-compatible Swift packages that lack Android support
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <RepositoryList repositories={repositories} />
      </main>
    </div>
  );
}

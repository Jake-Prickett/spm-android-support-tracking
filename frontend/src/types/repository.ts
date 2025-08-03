export interface Repository {
  url: string;
  owner: string;
  name: string;
  description: string | null;
  stars: number;
  forks: number;
  watchers: number;
  language: string;
  license_name: string | null;
  has_package_swift: boolean;
  swift_tools_version: string;
  dependencies_count: number;
  linux_compatible: boolean;
  android_compatible: boolean;
  current_state: string;
  created_at: string;
  updated_at: string;
  last_fetched: string;
}
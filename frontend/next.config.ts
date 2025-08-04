import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  distDir: '../docs',
  basePath: '/spm-android-support-tracking',
  assetPrefix: '/spm-android-support-tracking',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;

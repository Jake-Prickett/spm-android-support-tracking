import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  basePath: '/spm-android-support-tracking/docs',
  assetPrefix: '/spm-android-support-tracking/docs',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;

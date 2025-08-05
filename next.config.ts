import type {NextConfig} from 'next';

const nextConfig: NextConfig = {
  /* config options here */
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'placehold.co',
        port: '',
        pathname: '/**',
      },
    ],
  },
  webpack: (config, { isServer }) => {
    // Aliasing pdf-parse to its browser-specific build
    // to prevent server-side modules like 'fs' from being bundled on the client.
    config.resolve.alias['pdf-parse'] = 'pdf-parse/lib/pdf-parse.js';
    return config;
  },
  experimental: {
    serverActions: {
      allowedOrigins: [
        'localhost:3000',
        '*.app.github.dev',
        '*',
        'http://10.88.0.3:3000'
      ],
    },
  },
};

export default nextConfig;

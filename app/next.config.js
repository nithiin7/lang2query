/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker
  output: "standalone",

  // API rewrites for backend communication
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },

  // WebSocket rewrites for real-time communication
  async rewrites() {
    return [
      {
        source: "/ws/:path*",
        destination: `${process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws"}/:path*`,
      },
    ];
  },

  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws",
  },

  // Experimental features
  experimental: {
    serverComponentsExternalPackages: [],
  },

  // Image optimization
  images: {
    unoptimized: true, // Disable for Docker builds
  },
};

module.exports = nextConfig;

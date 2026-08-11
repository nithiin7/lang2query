/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker
  output: "standalone",

  // API rewrites for backend communication.
  // WebSocket connections are opened directly by the client (see src/lib/websocket.ts) —
  // Next.js rewrites don't support ws:// destinations, so there's no rewrite for /ws here.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },

  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws",
  },

  // Externalize server-only packages from bundling
  serverExternalPackages: [],

  // Image optimization
  images: {
    unoptimized: true, // Disable for Docker builds
  },
};

module.exports = nextConfig;

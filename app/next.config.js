/** @type {import('next').NextConfig} */
const nextConfig = {
    async rewrites() {
      return [
        {
          source: "/api/:path*",
          destination: "http://localhost:8000/api/:path*", // Python backend URL
        },
      ];
    },
  };
  
module.exports = nextConfig;
  
import type { NextConfig } from "next";

/** Server-side proxy target (Compose service name, or localhost for dev). */
const backend =
  process.env.BACKEND_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    proxyTimeout: 1_200_000, // 20 minutes (ms)
    proxyClientMaxBodySize: "50mb",
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/:path*`,
      },
    ];
  },
};

export default nextConfig;

import type { NextConfig } from "next";

const apiUrl = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Same-origin proxy: the browser talks only to this site, so the API's session cookie
  // (SameSite=Lax) works without CORS, and the API URL is not baked into client code.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/:path*` }];
  },
};

export default nextConfig;

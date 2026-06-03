/**
 * JARVIS Next.js Config
 * En desarrollo → proxy a localhost:8010
 * En Railway → proxy a backend-production
 */
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_URL ||
  process.env.BACKEND_URL ||
  (process.env.NODE_ENV === 'production'
    ? 'https://backend-production-cabf.up.railway.app'
    : 'http://localhost:8001')


const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      { source: '/api/:path*', destination: `${API_BASE}/api/v1/:path*` },
      { source: '/auth/:path*', destination: `${API_BASE}/auth/:path*` },
      { source: '/health', destination: `${API_BASE}/health` },
      { source: '/brain.stl', destination: `${API_BASE}/brain.stl` },
    ]
  },
  images: { unoptimized: true },
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: false },
  poweredByHeader: false,
}

export default nextConfig

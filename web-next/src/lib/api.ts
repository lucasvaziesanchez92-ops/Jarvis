const BACKEND_URL =
  (typeof window !== 'undefined' && window.location.hostname === 'localhost')
    ? 'http://localhost:8001'
    : 'https://backend-production-cabf.up.railway.app'

function resolveApiBase(): string {
  const env = process.env.NEXT_PUBLIC_API_URL
  if (env && env.includes('2522d')) {
    return BACKEND_URL
  }
  return env || BACKEND_URL
}

export const API_BASE = resolveApiBase()


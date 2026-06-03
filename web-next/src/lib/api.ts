// API_BASE auto-detecta local vs producción
export const API_BASE =
  typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? 'http://localhost:8001'
    : 'https://backend-production-2522d.up.railway.app'

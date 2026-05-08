import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Explicit env-var injection. Vite normally inlines `import.meta.env.VITE_*`
// from .env files + process.env at build time. Railway's railpack build
// environment was not propagating VITE_REVENUECAT_IOS_KEY into Vite's
// substitution despite the variable being correctly set in the service's
// Variables tab. Forcing the substitution via `define` guarantees the
// value lands in the bundle regardless of how the build env is wired.
//
// loadEnv reads .env files when present (local dev). process.env fallback
// covers Railway / any CI where the var is set as a real env var rather
// than a .env file.

export default defineConfig(({ mode }) => {
  const fileEnv = loadEnv(mode, process.cwd(), 'VITE_');
  const rcKey = fileEnv.VITE_REVENUECAT_IOS_KEY
    || process.env.VITE_REVENUECAT_IOS_KEY
    || '';
  if (!rcKey) {
    console.warn('[vite.config] WARNING: VITE_REVENUECAT_IOS_KEY is empty. iOS IAP will not work in this build.');
  } else {
    console.log(`[vite.config] VITE_REVENUECAT_IOS_KEY resolved (${rcKey.length} chars, prefix=${rcKey.slice(0, 8)}…)`);
  }
  return {
    plugins: [react()],
    define: {
      'import.meta.env.VITE_REVENUECAT_IOS_KEY': JSON.stringify(rcKey),
    },
    server: {
      host: '0.0.0.0',
      port: 5000,
      allowedHosts: true,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          headers: {
            'X-Forwarded-Proto': 'https'
          }
        },
        '/auth': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          headers: {
            'X-Forwarded-Proto': 'https'
          }
        },
        '/legal': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          headers: {
            'X-Forwarded-Proto': 'https'
          }
        }
      }
    }
  };
})

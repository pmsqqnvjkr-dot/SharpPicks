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
  // Fail loud when building for iOS without a RevenueCat key. A bundle
  // without VITE_REVENUECAT_IOS_KEY silently ships an iOS app whose
  // paywall can't load IAP products, which is the 2.1(b) Apple
  // rejection we've already eaten twice. The previous behavior here
  // was console.warn + empty string, which made it possible to ship
  // the broken bundle whenever a build process was missing the var.
  //
  // Only fires when BUILD_TARGET=ios is set, since web builds (Railway
  // deploys app.sharppicks.ai) use Stripe for paywall and don't need
  // the RevenueCat key at all. Cap-sync workflow should use
  // `npm run build:ios` which sets this flag automatically.
  if (process.env.BUILD_TARGET === 'ios' && !rcKey) {
    throw new Error(
      '[vite.config] VITE_REVENUECAT_IOS_KEY is empty and BUILD_TARGET=ios. '
      + 'iOS IAP will not load products with this bundle. Set the variable '
      + 'in .env (local) or in the build environment, then rerun. Refusing '
      + 'to produce a broken iOS bundle.'
    );
  }
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

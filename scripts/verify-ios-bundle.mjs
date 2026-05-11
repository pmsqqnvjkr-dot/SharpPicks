#!/usr/bin/env node
// Post-build assertion for iOS bundles. Runs between `vite build` and
// `cap sync ios` in the build:ios npm script. Greps dist/assets/*.js
// for a RevenueCat iOS API key (appl_*) and fails the build if absent.
//
// What this catches that the vite.config build-time throw doesn't:
//   - revenuecat.js refactored to no longer reference import.meta.env
//   - vite.config define block removed or wrong key name
//   - Bundle splitting that lands the key in a chunk that doesn't ship
//   - Any future build-config change that breaks the inlining path
//
// What this does NOT catch:
//   - Key present but invalid (expired, typo, wrong project). RevenueCat
//     SDK will return empty offerings at runtime; we don't hit the RC
//     API at build time.
//   - RevenueCat dashboard misconfiguration (offering removed, products
//     unmapped). Same runtime-only signal.

import { readdirSync, readFileSync } from 'fs';
import { join } from 'path';

const dir = 'dist/assets';
const KEY_PATTERN = /appl_[A-Za-z0-9_-]{20,}/;

let assets;
try {
  assets = readdirSync(dir).filter((f) => f.endsWith('.js'));
} catch (err) {
  console.error(`[verify-ios-bundle] FATAL: cannot read ${dir} (${err.message})`);
  console.error('  Did `vite build` actually run? Check the earlier step.');
  process.exit(1);
}

if (assets.length === 0) {
  console.error(`[verify-ios-bundle] FATAL: no .js files in ${dir}`);
  process.exit(1);
}

const found = assets.some((f) => KEY_PATTERN.test(readFileSync(join(dir, f), 'utf8')));

if (!found) {
  console.error('[verify-ios-bundle] FATAL: no RevenueCat key (appl_*) found in dist/.');
  console.error('  The build succeeded but the key was not inlined into the bundle.');
  console.error('  Likely causes:');
  console.error('    - vite.config.js define block removed or renamed');
  console.error('    - revenuecat.js refactored to no longer read import.meta.env.VITE_REVENUECAT_IOS_KEY');
  console.error('    - Bundle splitting moved the key into a chunk that is not in dist/assets/');
  console.error('  Fix: restore the import.meta.env reference and the define block, then rebuild.');
  process.exit(1);
}

console.log('[verify-ios-bundle] OK: RevenueCat key present in dist bundle');

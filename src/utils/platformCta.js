import { Capacitor } from '@capacitor/core';

// Centralized helpers for trial / upgrade CTA copy. iOS uses Apple IAP (no
// card up front, Apple holds the payment method) so the friction line drops
// "Card required". Android (Stripe via WebView) and the web app both take
// a real card to start the trial, so the friction line includes it.
//
// Why the helper exists: this string appears under every trial CTA across
// the app (DailyTopSignalCard, FreePickNotice, trial banner, paywall
// screens). When iOS guidelines change or we run a card-required A/B,
// flipping the logic in one place keeps every surface in sync.
//
// MIGRATION_CHECKLIST.md P1.4.2.

export function isIOSPlatform() {
  return Capacitor.getPlatform() === 'ios';
}

export function getTrialCtaSubtext() {
  return isIOSPlatform() ? 'Cancel anytime' : 'Card required · Cancel anytime';
}

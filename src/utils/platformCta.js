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
  // Capacitor's native bridge is the source of truth inside the iOS app.
  // Outside the bridge (Safari / standalone PWA on iPhone, or any iPad
  // browser an Apple reviewer might use) we fall back to the user-agent
  // string. We must hide "Card required" copy on every iOS surface
  // regardless of whether the user is in the WebView or in mobile
  // Safari, since either path can be how App Review evaluates the
  // experience.
  try {
    if (Capacitor && typeof Capacitor.getPlatform === 'function' && Capacitor.getPlatform() === 'ios') {
      return true;
    }
  } catch { /* fall through to UA */ }
  if (typeof navigator !== 'undefined' && navigator.userAgent) {
    const ua = navigator.userAgent;
    if (/iPad|iPhone|iPod/.test(ua)) return true;
    // iPadOS 13+ reports as Macintosh; touch support disambiguates from a Mac.
    if (/Macintosh/.test(ua) && typeof navigator.maxTouchPoints === 'number' && navigator.maxTouchPoints > 1) {
      return true;
    }
  }
  return false;
}

export function getTrialCtaSubtext() {
  return isIOSPlatform() ? 'Cancel anytime' : 'Card required · Cancel anytime';
}

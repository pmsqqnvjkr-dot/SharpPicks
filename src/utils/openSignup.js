import { Capacitor } from '@capacitor/core';

export default async function openSignup() {
  // Both iOS and Android route through the in-app AuthModal so the
  // signup completes inside the Capacitor WebView (same cookie jar as
  // the rest of the app). Previously Android opened Chrome Custom Tab
  // via Browser.open, which set the session cookie in a separate
  // cookie store that didn't carry back to the app. The Android
  // manifest also has no intent-filter for app.sharppicks.ai, so the
  // Stripe Checkout success URL would stay in Chrome rather than
  // reopening the app via deep link. Keeping the flow in-process
  // avoids both problems.
  if (Capacitor.isNativePlatform()) {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('sharppicks:open-auth', {
        detail: { intent: 'signup' },
      }));
    }
    return;
  }
  window.location.href = '/subscribe';
}

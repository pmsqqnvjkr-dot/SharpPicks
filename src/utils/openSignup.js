import { Capacitor } from '@capacitor/core';

const SIGNUP_URL = 'https://app.sharppicks.ai/signup';

export default async function openSignup() {
  if (Capacitor.getPlatform() === 'ios') {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('sharppicks:open-auth', {
        detail: { intent: 'signup' },
      }));
    }
    return;
  }
  if (Capacitor.isNativePlatform()) {
    const { Browser } = await import('@capacitor/browser');
    await Browser.open({ url: SIGNUP_URL });
  } else {
    window.location.href = '/subscribe';
  }
}

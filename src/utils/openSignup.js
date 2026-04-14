import { Capacitor } from '@capacitor/core';

const SIGNUP_URL = 'https://app.sharppicks.ai/signup';

export default async function openSignup() {
  if (Capacitor.getPlatform() === 'ios') {
    window.location.href = '/subscribe';
    return;
  }
  if (Capacitor.isNativePlatform()) {
    const { Browser } = await import('@capacitor/browser');
    await Browser.open({ url: SIGNUP_URL });
  } else {
    window.location.href = '/subscribe';
  }
}

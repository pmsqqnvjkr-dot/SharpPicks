import { Capacitor } from '@capacitor/core';

const isIOS = Capacitor.getPlatform() === 'ios';
const RC_IOS_KEY = import.meta.env.VITE_REVENUECAT_IOS_KEY || '';
let _configured = false;

async function _getPurchases() {
  const { Purchases } = await import('@revenuecat/purchases-capacitor');
  return Purchases;
}

export async function initializeRevenueCat(userId) {
  if (!isIOS || !RC_IOS_KEY || _configured) return _configured;
  try {
    const Purchases = await _getPurchases();
    await Purchases.configure({ apiKey: RC_IOS_KEY, appUserID: userId || null });
    _configured = true;
  } catch (e) {
    console.error('[RC] configure failed:', e);
  }
  return _configured;
}

export function isRevenueCatConfigured() {
  return _configured;
}

export async function rcLogin(userId) {
  if (!isIOS || !userId) return;
  const ready = await initializeRevenueCat(String(userId));
  if (!ready) return;
  try {
    const Purchases = await _getPurchases();
    await Purchases.logIn({ appUserID: String(userId) });
  } catch (e) {
    console.error('[RC] logIn failed:', e);
  }
}

export async function rcLogout() {
  if (!isIOS || !_configured) return;
  try {
    const Purchases = await _getPurchases();
    await Purchases.logOut();
  } catch (e) {
    console.error('[RC] logOut failed:', e);
  }
}

export async function getOfferings() {
  if (!isIOS) return null;
  const ready = await initializeRevenueCat();
  if (!ready) return null;
  try {
    const Purchases = await _getPurchases();
    const offerings = await Purchases.getOfferings();
    return offerings?.current || null;
  } catch (e) {
    console.error('[RC] getOfferings failed:', e);
    return null;
  }
}

export async function purchasePackage(pkg) {
  const ready = await initializeRevenueCat();
  if (!isIOS || !ready) throw new Error('RevenueCat not available');
  const Purchases = await _getPurchases();
  const result = await Purchases.purchasePackage({ aPackage: pkg });
  return result.customerInfo;
}

export async function restorePurchases() {
  if (!isIOS) return null;
  const ready = await initializeRevenueCat();
  if (!ready) return null;
  try {
    const Purchases = await _getPurchases();
    const { customerInfo } = await Purchases.restorePurchases();
    return customerInfo;
  } catch (e) {
    console.error('[RC] restore failed:', e);
    throw e;
  }
}

export async function checkProEntitlement() {
  if (!isIOS) return false;
  const ready = await initializeRevenueCat();
  if (!ready) return false;
  try {
    const Purchases = await _getPurchases();
    const { customerInfo } = await Purchases.getCustomerInfo();
    return !!customerInfo?.entitlements?.active?.pro;
  } catch (e) {
    console.error('[RC] entitlement check failed:', e);
    return false;
  }
}

export function isPurchaseCancelled(error) {
  if (!error) return false;
  const code = error?.code ?? error?.underlyingErrorMessage ?? '';
  return code === 1 || code === '1' ||
    String(code).includes('PURCHASE_CANCELLED') ||
    String(error?.message || '').includes('cancelled') ||
    String(error?.message || '').includes('canceled');
}

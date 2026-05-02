import { Capacitor } from '@capacitor/core';

const isIOS = Capacitor.getPlatform() === 'ios';
const RC_IOS_KEY = import.meta.env.VITE_REVENUECAT_IOS_KEY || '';
let _configured = false;

async function _getPurchases() {
  const { Purchases } = await import('@revenuecat/purchases-capacitor');
  return Purchases;
}

export async function initializeRevenueCat(userId) {
  if (!isIOS) return false;
  if (!RC_IOS_KEY) {
    console.warn('[RC] No iOS API key set (VITE_REVENUECAT_IOS_KEY). Subscriptions will not work.');
    return false;
  }
  if (_configured) return true;
  try {
    const Purchases = await _getPurchases();
    // Omit appUserID entirely when we don't have one — passing null caused
    // the SDK to silently reject configure(), which left getOfferings()
    // throwing 'Purchases must be configured before calling this function'
    // for anonymous users on app boot.
    const config = { apiKey: RC_IOS_KEY };
    if (userId) config.appUserID = String(userId);
    await Purchases.configure(config);
    _configured = true;
    console.log('[RC] RevenueCat configured successfully', userId ? '(identified)' : '(anonymous)');
  } catch (e) {
    console.error('[RC] configure failed:', e?.message || e, 'code:', e?.code);
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
  if (!ready) {
    console.warn('[RC] getOfferings called but RevenueCat not configured');
    return null;
  }
  try {
    const Purchases = await _getPurchases();
    const offerings = await Purchases.getOfferings();
    const current = offerings?.current || null;
    if (!current) {
      console.warn('[RC] No current offering returned. Check RevenueCat dashboard configuration.');
    } else {
      console.log('[RC] Offerings loaded:', current.identifier, '- annual:', !!current.annual, '- monthly:', !!current.monthly);
    }
    return current;
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

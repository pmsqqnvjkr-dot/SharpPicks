import { Capacitor } from '@capacitor/core';

const isIOS = Capacitor.getPlatform() === 'ios';
const RC_IOS_KEY = import.meta.env.VITE_REVENUECAT_IOS_KEY || '';
let _configured = false;

// Use the raw Capacitor plugin instead of the @revenuecat/purchases-capacitor
// JS wrapper. The wrapper's Purchases export is a Capacitor plugin proxy
// that forwards any unknown method call (including .then) to native. When
// our previous _getPurchases() async function returned the proxy, JS's
// promise-resolution machinery tried to unwrap the return value by calling
// .then() on it, which the iOS native plugin rejected with
// 'Purchases.then() is not implemented on ios'. The result was that
// initializeRevenueCat() always threw and offerings never loaded.
// The native plugin is still installed via the npm package's iOS pod, so
// Capacitor.Plugins.Purchases is available without the JS wrapper.
function _getPurchases() {
  return Capacitor.Plugins?.Purchases || null;
}

export async function initializeRevenueCat(userId) {
  if (!isIOS) return false;
  if (!RC_IOS_KEY) {
    console.warn('[RC] No iOS API key set (VITE_REVENUECAT_IOS_KEY). Subscriptions will not work.');
    return false;
  }
  if (_configured) return true;
  const Purchases = _getPurchases();
  if (!Purchases) {
    console.error('[RC] Purchases plugin not registered (native binding missing)');
    return false;
  }
  try {
    // Omit appUserID entirely when we don't have one — passing null caused
    // the SDK to silently reject configure(), which left getOfferings()
    // throwing 'Purchases must be configured before calling this function'
    // for anonymous users on app boot.
    const config = { apiKey: RC_IOS_KEY };
    if (userId) config.appUserID = String(userId);
    await Purchases.configure(config);
    _configured = true;
    console.log('[RC] RevenueCat configured successfully', userId ? '(identified)' : '(anonymous)');
    if (userId) {
      await _setSharppicksUserAttribute(userId);
    }
  } catch (e) {
    console.error('[RC] configure failed:', e?.message || e, 'code:', e?.code);
  }
  return _configured;
}

export function isRevenueCatConfigured() {
  return _configured;
}

// Stamp the SharpPicks user id as a custom RC subscriber attribute. This
// travels with every webhook event the way appUserID does, but unlike the
// appUserID it survives RC's anonymous-vs-aliased state. On 2026-06-04
// Nathan DeSilva's INITIAL_PURCHASE fired with app_user_id=$RCAnonymousID:
// <hex> because his rcLogin hadn't aliased yet at purchase time. The
// webhook had no way to map that anonymous id back to his SharpPicks
// user.id. With this attribute on the customer record, the webhook can
// read event.subscriber_attributes.sharppicksUserId.value and resolve
// the right user regardless of alias state.
async function _setSharppicksUserAttribute(userId) {
  if (!isIOS || !userId) return;
  const Purchases = _getPurchases();
  if (!Purchases) return;
  try {
    await Purchases.setAttributes({
      attributes: { sharppicksUserId: String(userId) },
    });
  } catch (e) {
    console.error('[RC] setAttributes failed:', e);
  }
}

export async function rcLogin(userId) {
  if (!isIOS || !userId) return false;
  const ready = await initializeRevenueCat(String(userId));
  if (!ready) return false;
  const Purchases = _getPurchases();
  if (!Purchases) return false;
  try {
    await Purchases.logIn({ appUserID: String(userId) });
    await _setSharppicksUserAttribute(userId);
    return true;
  } catch (e) {
    console.error('[RC] logIn failed:', e);
    return false;
  }
}

export async function rcLogout() {
  if (!isIOS || !_configured) return;
  const Purchases = _getPurchases();
  if (!Purchases) return;
  try {
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
  const Purchases = _getPurchases();
  if (!Purchases) return null;
  try {
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
  const Purchases = _getPurchases();
  if (!Purchases) throw new Error('RevenueCat not available');
  const result = await Purchases.purchasePackage({ aPackage: pkg });
  return result.customerInfo;
}

export async function restorePurchases() {
  if (!isIOS) return null;
  const ready = await initializeRevenueCat();
  if (!ready) return null;
  const Purchases = _getPurchases();
  if (!Purchases) return null;
  try {
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
  const Purchases = _getPurchases();
  if (!Purchases) return false;
  try {
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

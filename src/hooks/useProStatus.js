import { useState, useEffect, useCallback } from 'react';
import { Capacitor } from '@capacitor/core';
import { checkProEntitlement } from '../lib/revenuecat';

const isIOS = Capacitor.getPlatform() === 'ios';

export function useProStatus(user) {
  const backendPro = !!user?.is_premium;
  const [rcPro, setRcPro] = useState(null);
  const [loading, setLoading] = useState(isIOS);

  const refresh = useCallback(async () => {
    if (!isIOS) return;
    setLoading(true);
    try {
      const entitled = await checkProEntitlement();
      setRcPro(entitled);
    } catch {
      setRcPro(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isIOS) return;
    refresh();

    const handleVisibility = () => {
      if (document.visibilityState === 'visible') refresh();
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [refresh]);

  if (!isIOS) {
    return { isPro: backendPro, isLoading: false, refresh };
  }

  return {
    isPro: rcPro ?? backendPro,
    isLoading: loading,
    refresh,
  };
}

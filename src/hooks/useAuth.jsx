import { useState, useEffect, createContext, useContext } from 'react';
import { apiPost, apiGet, setAuthToken } from './useApi';
import { requestNotificationPermission, getNotificationPermissionStatus, getNativePermissionStatus, isNative } from '../firebase';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pushStatus, setPushStatus] = useState('default');

  useEffect(() => {
    checkAuth();
    (async () => {
      const status = await getNativePermissionStatus();
      setPushStatus(status);
    })();
  }, []);

  useEffect(() => {
    if (!user || pushStatus !== 'granted') return;
    requestNotificationPermission().then(token => {
      if (token) console.log("[Push] token refreshed on visit");
    }).catch(() => {});
  }, [user, pushStatus]);

  const enablePush = async () => {
    const token = await requestNotificationPermission();
    const status = await getNativePermissionStatus();
    setPushStatus(status);
    return !!token;
  };

  const checkAuth = async () => {
    try {
      const data = await apiGet('/auth/user');
      if (data && data.authenticated && data.user) {
        if (data.token) setAuthToken(data.token);
        setUser(data.user);
      } else if (data && data.id) {
        setUser(data);
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const data = await apiPost('/auth/login', { email, password });
      if (data.success && data.user) {
        if (data.token) setAuthToken(data.token);
        setUser(data.user);
        return { success: true };
      } else if (data.id) {
        setUser(data);
        return { success: true };
      }
      return { success: false, error: data.error || 'Login failed' };
    } catch {
      return { success: false, error: 'Something went wrong. Please try again.' };
    }
  };

  const register = async (email, password, firstName, accountType = 'trial') => {
    try {
      const data = await apiPost('/auth/register', { email, password, first_name: firstName, account_type: accountType });
      if (data.success && data.user) {
        if (data.token) setAuthToken(data.token);
        setUser(data.user);
        return { success: true, needs_verification: data.needs_verification };
      } else if (data.id) {
        setUser(data);
        return { success: true };
      }
      return { success: false, error: data.error || 'Registration failed' };
    } catch {
      return { success: false, error: 'Something went wrong. Please try again.' };
    }
  };

  const resendVerification = async () => {
    try {
      const data = await apiPost('/auth/resend-verification', {});
      return data;
    } catch {
      return { error: 'Failed to resend. Please try again.' };
    }
  };

  const logout = async () => {
    await apiPost('/auth/logout', {});
    setAuthToken(null);
    setUser(null);
  };

  const setUnitSize = async (size) => {
    const val = Math.max(1, Math.round(size));
    try {
      await apiPost('/auth/unit-size', { unit_size: val });
      setUser(prev => prev ? { ...prev, unit_size: val } : prev);
    } catch {}
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, checkAuth, resendVerification, enablePush, pushStatus, setUnitSize }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

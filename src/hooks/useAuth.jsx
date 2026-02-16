import { useState, useEffect, createContext, useContext } from 'react';
import { apiPost, apiGet, setAuthToken } from './useApi';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

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
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    setAuthToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, checkAuth, resendVerification }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

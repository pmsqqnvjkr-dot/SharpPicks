import { useState, useEffect, createContext, useContext } from 'react';
import { apiPost, apiGet } from './useApi';

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
    const data = await apiPost('/auth/login', { email, password });
    if (data.success && data.user) {
      setUser(data.user);
      return { success: true };
    } else if (data.id) {
      setUser(data);
      return { success: true };
    }
    return { success: false, error: data.error || 'Login failed' };
  };

  const register = async (email, password, firstName) => {
    const data = await apiPost('/auth/register', { email, password, first_name: firstName });
    if (data.success && data.user) {
      setUser(data.user);
      return { success: true };
    } else if (data.id) {
      setUser(data);
      return { success: true };
    }
    return { success: false, error: data.error || 'Registration failed' };
  };

  const logout = async () => {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

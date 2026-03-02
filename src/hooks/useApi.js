import { useState, useEffect, useCallback, useRef } from 'react';
import { Capacitor } from '@capacitor/core';

const PROD_URL = 'https://app.sharppicks.ai';
const API_BASE = Capacitor.isNativePlatform() ? PROD_URL + '/api' : '/api';
const TOKEN_KEY = 'sp_auth_token';

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY) || '';
}

function authHeaders(extra = {}) {
  const token = getAuthToken();
  const headers = { ...extra };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

export function useApi(endpoint, options = {}) {
  const { pollInterval, skip } = options;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  const fetchData = useCallback(async (silent) => {
    try {
      if (!silent) setLoading(true);
      const res = await fetch(`${API_BASE}${endpoint}`, {
        credentials: 'include',
        headers: authHeaders(),
        cache: 'no-store',
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const json = await res.json();
      if (json.token) setAuthToken(json.token);
      if (mountedRef.current) {
        setData(json);
        setError(null);
      }
    } catch (err) {
      if (mountedRef.current) setError(err.message);
    } finally {
      if (mountedRef.current && !silent) setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    mountedRef.current = true;
    if (!skip) fetchData();
    return () => { mountedRef.current = false; };
  }, [fetchData, skip]);

  useEffect(() => {
    if (!pollInterval || skip) return;
    const id = setInterval(() => fetchData(true), pollInterval);
    return () => clearInterval(id);
  }, [pollInterval, fetchData, skip]);

  return { data, loading, error, refetch: fetchData };
}

export async function apiPost(endpoint, body) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      credentials: 'include',
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    const json = await res.json();
    if (json.token) setAuthToken(json.token);
    return json;
  } catch (err) {
    if (err.name === 'AbortError') {
      return { error: 'Request timed out. Please try again.' };
    }
    return { error: 'Network error. Please check your connection.' };
  } finally {
    clearTimeout(timeout);
  }
}

export async function apiGet(endpoint) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      credentials: 'include',
      headers: authHeaders(),
      signal: controller.signal,
      cache: 'no-store',
    });
    const json = await res.json();
    if (json.token) setAuthToken(json.token);
    return json;
  } catch (err) {
    if (err.name === 'AbortError') {
      return { error: 'Request timed out. Please try again.' };
    }
    return { error: 'Network error. Please check your connection.' };
  } finally {
    clearTimeout(timeout);
  }
}

export async function apiDelete(endpoint) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'DELETE',
      credentials: 'include',
      headers: authHeaders(),
      signal: controller.signal,
    });
    return res.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      return { error: 'Request timed out. Please try again.' };
    }
    return { error: 'Network error. Please check your connection.' };
  } finally {
    clearTimeout(timeout);
  }
}

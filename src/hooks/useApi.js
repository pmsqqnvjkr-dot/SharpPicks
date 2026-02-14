import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE = '/api';

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
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const json = await res.json();
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
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
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

export async function apiGet(endpoint) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      credentials: 'include',
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

export async function apiDelete(endpoint) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'DELETE',
      credentials: 'include',
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

import { Capacitor } from '@capacitor/core';
import { apiPost } from '../hooks/useApi';

function generateSessionId() {
  return 'ses_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 10);
}

const FLUSH_INTERVAL_MS = 30000;
const MAX_QUEUE_SIZE = 20;
const SESSION_TIMEOUT_MS = 30 * 60 * 1000;

class EventTracker {
  constructor() {
    this.queue = [];
    this.sessionId = generateSessionId();
    this.sessionStart = Date.now();
    this.lastActivity = Date.now();
    this.currentPage = null;
    this.flushing = false;

    this.flushTimer = setInterval(() => this.flush(), FLUSH_INTERVAL_MS);

    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
          this.track('session_end', {
            duration_seconds: Math.round((Date.now() - this.sessionStart) / 1000),
          });
          this.flush();
        } else if (document.visibilityState === 'visible') {
          this._maybeNewSession();
        }
      });
    }

    if (Capacitor.isNativePlatform()) {
      import('@capacitor/app').then(({ App }) => {
        App.addListener('appStateChange', ({ isActive }) => {
          if (!isActive) {
            this.track('session_end', {
              duration_seconds: Math.round((Date.now() - this.sessionStart) / 1000),
            });
            this.flush();
          } else {
            this._maybeNewSession();
          }
        });
      }).catch(() => {});
    }

    this.track('session_start', {
      platform: Capacitor.isNativePlatform() ? Capacitor.getPlatform() : 'web',
    });
  }

  _maybeNewSession() {
    const gap = Date.now() - this.lastActivity;
    if (gap > SESSION_TIMEOUT_MS) {
      this.sessionId = generateSessionId();
      this.sessionStart = Date.now();
      this.track('session_start', {
        platform: Capacitor.isNativePlatform() ? Capacitor.getPlatform() : 'web',
      });
    }
    this.lastActivity = Date.now();
  }

  track(eventType, eventData = {}, page = null) {
    this.lastActivity = Date.now();
    this.queue.push({
      event_type: eventType,
      event_data: eventData,
      page: page || this.currentPage,
      session_id: this.sessionId,
      timestamp: new Date().toISOString(),
    });
    if (this.queue.length >= MAX_QUEUE_SIZE) {
      this.flush();
    }
  }

  setPage(page) {
    const prev = this.currentPage;
    this.currentPage = page;
    if (page !== prev) {
      this.track('page_view', { page, referrer: prev });
    }
  }

  async flush() {
    if (this.queue.length === 0 || this.flushing) return;
    this.flushing = true;
    const batch = [...this.queue];
    this.queue = [];
    try {
      const result = await apiPost('/events', { events: batch });
      if (result.error) {
        this.queue = [...batch, ...this.queue].slice(-100);
      }
    } catch {
      this.queue = [...batch, ...this.queue].slice(-100);
    } finally {
      this.flushing = false;
    }
  }

  destroy() {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
    this.flush();
  }
}

let _instance = null;

export function getTracker() {
  if (!_instance) {
    _instance = new EventTracker();
  }
  return _instance;
}

export function trackEvent(eventType, eventData = {}, page = null) {
  getTracker().track(eventType, eventData, page);
}

export function trackPageView(page) {
  getTracker().setPage(page);
}

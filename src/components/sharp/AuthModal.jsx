import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiGet, setAuthToken } from '../../hooks/useApi';
import { Capacitor } from '@capacitor/core';

const PROD_URL = 'https://app.sharppicks.ai';
const API_BASE = Capacitor.isNativePlatform() ? PROD_URL + '/api' : '/api';
const isNative = Capacitor.isNativePlatform();
const isIOS = Capacitor.getPlatform() === 'ios';

export default function AuthModal({ onClose, initialMode, initialAccountType }) {
  const [mode, setMode] = useState(initialMode || 'login');
  const [accountView, setAccountView] = useState(initialAccountType || 'trial');
  const [firstName, setFirstName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { login, register, checkAuth } = useAuth();

  useEffect(() => {
    if (mode !== 'verify') return;
    const poll = setInterval(async () => {
      try {
        const data = await apiGet('/check-verification-status');
        if (data?.verified) { await checkAuth(); onClose(); }
      } catch { /* ignore */ }
    }, 4000);
    return () => clearInterval(poll);
  }, [mode]);

  const handleSubmit = async (e, accountType) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSubmitting(true);

    if (mode === 'forgot') {
      try {
        const res = await fetch(`${API_BASE}/auth/forgot-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email }),
        });
        const data = await res.json();
        if (data.success) {
          setSuccess('If that email exists, a password reset link has been sent.');
        } else {
          setError(data.error || 'Something went wrong.');
        }
      } catch {
        setError('Network error. Please try again.');
      }
      setSubmitting(false);
      return;
    }

    if (mode === 'login') {
      const result = await login(email, password);
      if (result.success) {
        onClose();
      } else {
        setError(result.error);
      }
      setSubmitting(false);
      return;
    }

    const type = accountType || 'trial';
    const result = await register(email, password, firstName.trim(), type);

    if (result.success) {
      if (result.needs_verification) {
        setMode('verify');
        setSuccess(type === 'trial'
          ? 'Check your email for a verification link. After verifying, you\'ll be taken to set up your trial.'
          : 'Check your email for a verification link to activate your account.');
        setError('');
      } else {
        onClose();
      }
    } else {
      setError(result.error);
    }
    setSubmitting(false);
  };

  const isFreeView = accountView === 'free';
  const pollRef = useRef(null);

  const handleOAuth = async (provider) => {
    const plan = isFreeView ? 'free' : 'trial';
    if (isNative) {
      const nonce = Math.random().toString(36).slice(2) + Date.now().toString(36);
      const url = `${PROD_URL}/auth/${provider}?plan=${plan}&nonce=${nonce}`;
      const { Browser } = await import('@capacitor/browser');
      await Browser.open({ url });

      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/auth/nonce-exchange?nonce=${nonce}`);
          if (res.ok) {
            const data = await res.json();
            if (data.success && data.token) {
              clearInterval(pollRef.current);
              pollRef.current = null;
              setAuthToken(data.token);
              await checkAuth();
              try { const { Browser: B } = await import('@capacitor/browser'); B.close(); } catch {}
              onClose();
            }
          }
        } catch {}
      }, 2000);
      setTimeout(() => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } }, 120000);
    } else {
      window.location.href = `/auth/${provider}?plan=${plan}`;
    }
  };

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const titles = {
    login: 'Welcome back',
    register: isFreeView ? 'Create free account' : 'Start your 14-day trial',
    forgot: 'Reset password',
    verify: 'Verify your email',
  };

  const subtitles = {
    login: 'Sign in to access your picks',
    register: isFreeView
      ? 'No card needed. See the model at work.'
      : 'Card required to start. $0 for 14 days, then $149.99/year. Cancel anytime.',
    forgot: 'Enter your email to receive a reset link',
    verify: 'We sent a verification link to your email',
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 100,
      padding: '20px',
    }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: 'var(--surface-1)',
          borderRadius: '20px',
          padding: '32px 24px',
          width: '100%',
          maxWidth: '400px',
          border: '1px solid var(--stroke-subtle)',
        }}
        onClick={e => e.stopPropagation()}
      >
        <h2 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '24px',
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: '8px',
          textAlign: 'center',
        }}>
          {titles[mode]}
        </h2>
        <p style={{
          fontSize: '14px',
          color: 'var(--text-secondary)',
          textAlign: 'center',
          marginBottom: '24px',
        }}>
          {subtitles[mode]}
        </p>

        {error && (
          <div style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: '10px',
            padding: '12px 16px',
            marginBottom: '16px',
            fontSize: '13px',
            color: 'var(--red-loss)',
          }}>
            {error}
          </div>
        )}

        {success && (
          <div style={{
            backgroundColor: 'rgba(52, 211, 153, 0.1)',
            border: '1px solid rgba(52, 211, 153, 0.2)',
            borderRadius: '10px',
            padding: '12px 16px',
            marginBottom: '16px',
            fontSize: '13px',
            color: 'var(--green-profit)',
          }}>
            {success}
          </div>
        )}

        {(mode === 'login' || mode === 'register') && (
          <>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
              {!isIOS && (
                <button
                  type="button"
                  onClick={() => handleOAuth('google')}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                    width: '100%', padding: '12px', borderRadius: 8,
                    fontFamily: 'var(--font-sans)', fontSize: 13, fontWeight: 500,
                    color: 'var(--text-primary)', background: 'var(--surface-2)',
                    border: '1px solid var(--stroke-muted)', cursor: 'pointer',
                  }}
                >
                  <svg width="18" height="18" viewBox="0 0 18 18"><path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/><path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/><path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/><path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/></svg>
                  Continue with Google
                </button>
              )}
              <button
                type="button"
                onClick={() => handleOAuth('apple')}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                  width: '100%', padding: '12px', borderRadius: 8,
                  fontFamily: 'var(--font-sans)', fontSize: 13, fontWeight: 500,
                  color: 'var(--text-primary)', background: 'var(--surface-2)',
                  border: '1px solid var(--stroke-muted)', cursor: 'pointer',
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24"><path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.52-3.23 0-1.44.64-2.2.52-3.06-.4C3.79 16.17 4.36 9.96 8.9 9.7c1.26.07 2.13.72 2.87.76.99-.2 1.94-.78 3-.84 1.28-.07 2.25.38 2.88 1.2-2.64 1.58-2.01 5.07.37 6.04-.5 1.3-.73 1.88-1.37 3.03-.58 1.04-1.4 2.08-2.6 2.39zM12.03 9.6C11.86 7.69 13.38 6.1 15.18 5.95c.27 2.15-1.94 3.76-3.15 3.65z" fill="#fff"/></svg>
                Continue with Apple
              </button>
            </div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16,
            }}>
              <div style={{ flex: 1, height: 1, background: 'var(--stroke-muted)' }} />
              <span style={{
                fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 500,
                letterSpacing: '0.08em', textTransform: 'uppercase',
                color: 'var(--text-tertiary)', whiteSpace: 'nowrap',
              }}>or use email</span>
              <div style={{ flex: 1, height: 1, background: 'var(--stroke-muted)' }} />
            </div>
          </>
        )}

        {mode === 'verify' ? (
          <div style={{ textAlign: 'center', padding: '16px 0' }}>
            <div style={{
              width: '64px', height: '64px', borderRadius: '50%',
              backgroundColor: 'rgba(79,134,247,0.1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 20px',
              fontSize: '28px',
            }}>
              &#9993;
            </div>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '24px' }}>
              Check <strong style={{ color: 'var(--text-primary)' }}>{email}</strong> for a verification link.
              Once verified, you'll complete setup to activate your account.
            </p>
            <button
              type="button"
              onClick={async () => {
                setSubmitting(true);
                try {
                  const res = await fetch(`${API_BASE}/auth/resend-verification`, { method: 'POST', credentials: 'include' });
                  const data = await res.json();
                  if (data.success) setSuccess('Verification email resent!');
                  else setError(data.error || 'Failed to resend');
                } catch { setError('Network error'); }
                setSubmitting(false);
              }}
              disabled={submitting}
              style={{
                padding: '12px 24px',
                backgroundColor: 'transparent',
                border: '1px solid var(--stroke-subtle)',
                borderRadius: '10px',
                color: 'var(--text-secondary)',
                fontSize: '14px',
                cursor: 'pointer',
                fontFamily: 'var(--font-sans)',
                opacity: submitting ? 0.5 : 1,
              }}
            >
              {submitting ? 'Sending...' : 'Resend verification email'}
            </button>
          </div>
        ) : (
        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div style={{ marginBottom: '12px' }}>
              <label style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: '6px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}>
                First Name
              </label>
              <input
                type="text"
                value={firstName}
                onChange={e => setFirstName(e.target.value)}
                placeholder="What should we call you?"
                required
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  backgroundColor: 'var(--surface-2)',
                  border: '1px solid var(--stroke-muted)',
                  borderRadius: '10px',
                  color: 'var(--text-primary)',
                  fontSize: '15px',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
          )}

          <div style={{ marginBottom: '12px' }}>
            <label style={{
              display: 'block',
              fontSize: '12px',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              marginBottom: '6px',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              style={{
                width: '100%',
                padding: '12px 16px',
                backgroundColor: 'var(--surface-2)',
                border: '1px solid var(--stroke-muted)',
                borderRadius: '10px',
                color: 'var(--text-primary)',
                fontSize: '15px',
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          {mode !== 'forgot' && (
            <div style={{ marginBottom: '20px' }}>
              <label style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                marginBottom: '6px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}>
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  minLength={6}
                  style={{
                    width: '100%',
                    padding: '12px 44px 12px 16px',
                    backgroundColor: 'var(--surface-2)',
                    border: '1px solid var(--stroke-muted)',
                    borderRadius: '10px',
                    color: 'var(--text-primary)',
                    fontSize: '15px',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  style={{
                    position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', padding: '4px', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: 'var(--text-tertiary)',
                  }}
                >
                  {showPassword ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                      <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                  )}
                </button>
              </div>
            </div>
          )}

          {mode === 'login' && (
            <div style={{ textAlign: 'right', marginBottom: '16px' }}>
              <button
                type="button"
                onClick={() => { setMode('forgot'); setError(''); setSuccess(''); }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-tertiary)',
                  fontSize: '12px',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-sans)',
                }}
              >
                Forgot password?
              </button>
            </div>
          )}

          {mode === 'register' ? (
            <>
              <button
                type="button"
                disabled={submitting}
                onClick={(e) => handleSubmit(e, isFreeView ? 'free' : 'trial')}
                style={{
                  width: '100%',
                  padding: '14px',
                  backgroundColor: '#5A9E72',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '10px',
                  fontSize: '15px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  opacity: submitting ? 0.7 : 1,
                  fontFamily: 'var(--font-sans)',
                }}
              >
                {submitting ? 'Please wait...' : isFreeView ? 'Create Free Account' : 'Start 14-Day Trial'}
              </button>
              <p style={{
                textAlign: 'center',
                fontSize: '11px',
                color: 'var(--text-tertiary)',
                marginTop: '6px',
                fontFamily: 'var(--font-sans)',
              }}>
                {isFreeView ? 'No card needed · Limited access · Upgrade anytime' : 'Card required · $0 for 14 days · Cancel anytime'}
              </p>

              <button
                type="button"
                onClick={() => setAccountView(isFreeView ? 'trial' : 'free')}
                style={{
                  display: 'block',
                  margin: '16px auto 0',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-tertiary)',
                  fontSize: '12px',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-sans)',
                }}
              >
                {isFreeView ? 'or start a 14-day trial instead' : 'or create a free account instead'}
              </button>
            </>
          ) : (
            <button
              type="submit"
              disabled={submitting}
              style={{
                width: '100%',
                padding: '14px',
                backgroundColor: '#5A9E72',
                color: '#0A0D14',
                border: 'none',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                opacity: submitting ? 0.7 : 1,
                fontFamily: 'var(--font-sans)',
                marginTop: mode === 'forgot' ? '8px' : '0',
              }}
            >
              {submitting ? 'Please wait...'
                : mode === 'login' ? 'Sign In'
                : 'Send Reset Link'}
            </button>
          )}
        </form>
        )}

        <div style={{
          textAlign: 'center',
          marginTop: '16px',
        }}>
          {mode === 'forgot' ? (
            <button
              onClick={() => { setMode('login'); setError(''); setSuccess(''); }}
              style={{
                background: 'none',
                border: 'none',
                color: '#5A9E72',
                fontSize: '13px',
                cursor: 'pointer',
                fontFamily: 'var(--font-sans)',
              }}
            >
              Back to sign in
            </button>
          ) : (
            <button
              onClick={() => {
                setMode(mode === 'login' ? 'register' : 'login');
                setError('');
                setSuccess('');
              }}
              style={{
                background: 'none',
                border: 'none',
                color: '#5A9E72',
                fontSize: '13px',
                cursor: 'pointer',
                fontFamily: 'var(--font-sans)',
              }}
            >
              {mode === 'login' ? 'Need an account? Sign up' : 'Already have an account? Sign in'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

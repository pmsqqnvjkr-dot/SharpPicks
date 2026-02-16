import { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';

const API_BASE = '/api';

export default function AuthModal({ onClose, initialMode }) {
  const [mode, setMode] = useState(initialMode || 'login');
  const [firstName, setFirstName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
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

    const result = mode === 'login'
      ? await login(email, password)
      : await register(email, password, firstName.trim());

    if (result.success) {
      if (result.needs_verification) {
        setMode('verify');
        setSuccess('Check your email for a verification link to activate your account.');
        setError('');
      } else {
        onClose();
      }
    } else {
      setError(result.error);
    }
    setSubmitting(false);
  };

  const titles = {
    login: 'Welcome back',
    register: 'Create account',
    forgot: 'Reset password',
    verify: 'Verify your email',
  };

  const subtitles = {
    login: 'Sign in to access your picks',
    register: 'Start your 14-day free trial',
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
              Once verified, you can start your 14-day free trial.
            </p>
            <button
              type="button"
              onClick={async () => {
                setSubmitting(true);
                try {
                  const res = await fetch('/api/auth/resend-verification', { method: 'POST', credentials: 'include' });
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
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                minLength={6}
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

          <button
            type="submit"
            disabled={submitting}
            style={{
              width: '100%',
              padding: '14px',
              backgroundColor: 'var(--blue-primary)',
              color: '#fff',
              border: 'none',
              borderRadius: '10px',
              fontSize: '15px',
              fontWeight: 600,
              cursor: 'pointer',
              opacity: submitting ? 0.7 : 1,
              fontFamily: 'var(--font-sans)',
              marginTop: mode === 'forgot' ? '8px' : '0',
            }}
          >
            {submitting ? 'Please wait...'
              : mode === 'login' ? 'Sign In'
              : mode === 'register' ? 'Create Account'
              : 'Send Reset Link'}
          </button>
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
                color: 'var(--blue-primary)',
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
                color: 'var(--blue-primary)',
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

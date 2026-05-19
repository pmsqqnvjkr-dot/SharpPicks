import { useEffect, useState } from 'react';
import { apiPost } from '../../hooks/useApi';

// Android rating prompt soft-prompt + feedback form. Internal state
// machine drives three paths: 'soft' (initial) -> 'feedback' (Path B)
// or close (Path A / Path C). Parent owns the open/close lifecycle and
// the native In-App Review trigger.

const SIGNAL_BLUE = '#4F86F7';

function logEvent(name, data) {
  try {
    apiPost('/rating-prompt/event', { event: name, data: data || {} });
  } catch {
    // Analytics is best-effort; never block UX on it.
  }
}

export default function RatingPrompt({ open, onPositive, onClose }) {
  const [stage, setStage] = useState('soft');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open) return;
    setStage('soft');
    setSubmitting(false);
    setSubmitted(false);
    setMessage('');
    setError(null);
    logEvent('shown');
  }, [open]);

  if (!open) return null;

  const handlePositive = () => {
    logEvent('tapped_positive');
    onClose && onClose();
    setTimeout(() => {
      onPositive && onPositive();
    }, 500);
  };

  const handleNegative = () => {
    logEvent('tapped_negative');
    setStage('feedback');
  };

  const handleDismiss = (source) => {
    logEvent('dismissed', { source });
    onClose && onClose();
  };

  const handleSkipFeedback = () => {
    logEvent('feedback_skipped');
    onClose && onClose();
  };

  const handleSubmitFeedback = async () => {
    const trimmed = message.trim();
    if (trimmed.length < 5) {
      setError('Add a sentence or two so we can act on it.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const platform = (window?.Capacitor?.getPlatform?.() || 'web');
      const appVersion = window?.SharpPicksAppVersion || '';
      const res = await apiPost('/rating-prompt/feedback', {
        message: trimmed.slice(0, 2000),
        platform,
        app_version: appVersion,
      });
      if (res?.error) {
        setError('Could not submit. Try emailing support@sharppicks.ai directly.');
        setSubmitting(false);
        return;
      }
      setSubmitted(true);
      setSubmitting(false);
    } catch {
      setError('Could not submit. Try emailing support@sharppicks.ai directly.');
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(2px)',
        WebkitBackdropFilter: 'blur(2px)',
        display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
      }}
      onClick={() => {
        if (submitting) return;
        if (submitted) { onClose && onClose(); return; }
        if (stage === 'soft') handleDismiss('backdrop');
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%', maxWidth: '440px',
          background: 'var(--surface-1)',
          borderRadius: '24px 24px 0 0',
          borderTop: '1px solid var(--stroke-subtle)',
          boxShadow: '0 -8px 32px rgba(0, 0, 0, 0.3)',
          animation: 'sp-slide-up 0.25s ease-out',
        }}
      >
        <div style={{
          width: '40px', height: '4px',
          background: 'var(--stroke-muted)',
          borderRadius: '2px',
          margin: '12px auto 0',
        }} />

        {submitted ? (
          <SubmittedPanel onDone={() => onClose && onClose()} />
        ) : stage === 'soft' ? (
          <SoftPanel
            onPositive={handlePositive}
            onNegative={handleNegative}
            onMaybeLater={() => handleDismiss('maybe_later')}
          />
        ) : (
          <FeedbackPanel
            message={message}
            setMessage={setMessage}
            submitting={submitting}
            error={error}
            onSubmit={handleSubmitFeedback}
            onSkip={handleSkipFeedback}
          />
        )}
      </div>

      <style>{`
        @keyframes sp-slide-up {
          from { transform: translateY(24px); opacity: 0; }
          to   { transform: translateY(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
}


function SignalMark() {
  return (
    <div style={{ marginTop: '14px', marginBottom: '18px', textAlign: 'center' }}>
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: '4px',
      }}>
        <div style={{ width: '4px', height: '22px', background: 'var(--text-primary)', borderRadius: '1px' }} />
        <div style={{ width: '4px', height: '22px', background: 'var(--text-primary)', borderRadius: '1px' }} />
      </div>
      <div style={{ width: '28px', height: '2px', background: '#5A9E72', margin: '4px auto 0' }} />
    </div>
  );
}


function SoftPanel({ onPositive, onNegative, onMaybeLater }) {
  return (
    <div style={{ padding: '0 24px 28px', textAlign: 'center' }}>
      <SignalMark />
      <h2 style={{
        fontFamily: 'var(--font-serif)',
        fontSize: '20px', fontWeight: 500,
        color: 'var(--text-primary)',
        letterSpacing: '-0.005em', lineHeight: 1.3,
        marginBottom: '8px',
      }}>How is SharpPicks working for you?</h2>
      <p style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '13px', color: 'var(--text-secondary)',
        lineHeight: 1.5, marginBottom: '24px', padding: '0 8px',
      }}>
        A few weeks in. Honest feedback helps us improve the model.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '12px' }}>
        <button
          onClick={onPositive}
          style={{
            width: '100%', padding: '14px 20px',
            border: 'none', borderRadius: '10px',
            background: SIGNAL_BLUE, color: '#FFFFFF',
            fontFamily: 'var(--font-sans)', fontSize: '14px', fontWeight: 600,
            cursor: 'pointer',
          }}
        >It's working</button>
        <button
          onClick={onNegative}
          style={{
            width: '100%', padding: '14px 20px',
            background: 'transparent',
            color: 'var(--text-secondary)',
            border: '1px solid var(--stroke-muted)', borderRadius: '10px',
            fontFamily: 'var(--font-sans)', fontSize: '14px', fontWeight: 600,
            cursor: 'pointer',
          }}
        >Not yet</button>
      </div>

      <button
        onClick={onMaybeLater}
        style={{
          background: 'transparent', border: 'none',
          color: 'var(--text-tertiary)',
          fontFamily: 'var(--font-sans)', fontSize: '12px', fontWeight: 500,
          padding: '8px', cursor: 'pointer',
        }}
      >Maybe later</button>
    </div>
  );
}


function FeedbackPanel({ message, setMessage, submitting, error, onSubmit, onSkip }) {
  const charCount = message.length;
  const overLimit = charCount > 2000;
  return (
    <div>
      <div style={{
        padding: '20px 24px 14px',
        borderBottom: '1px solid var(--stroke-subtle)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <h3 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '19px', fontWeight: 500,
          color: 'var(--text-primary)',
          letterSpacing: '-0.005em',
        }}>What's not working?</h3>
        <button
          onClick={onSkip}
          aria-label="Close"
          style={{
            background: 'transparent', border: 'none',
            color: 'var(--text-tertiary)', cursor: 'pointer',
            padding: '4px', display: 'flex',
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div style={{ padding: '18px 24px 8px' }}>
        <p style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '13px', color: 'var(--text-secondary)',
          lineHeight: 1.5, marginBottom: '16px',
        }}>
          Your feedback goes directly to <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>the founder</strong>. Every message is read.
        </p>

        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Tell us what's not landing. The model output, the interface, the pace of signals, whatever isn't working."
          rows={6}
          maxLength={2000}
          style={{
            width: '100%', minHeight: '160px',
            background: 'var(--surface-2, var(--surface-1))',
            border: `1px solid ${overLimit ? '#C4868A' : 'var(--stroke-muted)'}`,
            borderRadius: '10px', padding: '14px',
            fontFamily: 'var(--font-sans)',
            fontSize: '14px', color: 'var(--text-primary)',
            lineHeight: 1.5, resize: 'none', outline: 'none',
            boxSizing: 'border-box',
          }}
        />

        <div style={{
          marginTop: '8px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          fontFamily: 'var(--font-mono)', fontSize: '10px',
          color: 'var(--text-tertiary)', letterSpacing: '0.04em',
        }}>
          <span>Sent to support@sharppicks.ai</span>
          <span style={{ color: overLimit ? '#C4868A' : 'var(--text-tertiary)' }}>
            {charCount} / 2000
          </span>
        </div>

        {error && (
          <div style={{
            marginTop: '12px',
            fontFamily: 'var(--font-sans)', fontSize: '12px',
            color: '#C4868A', lineHeight: 1.4,
          }}>{error}</div>
        )}
      </div>

      <div style={{ padding: '12px 24px 24px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <button
          onClick={onSubmit}
          disabled={submitting || message.trim().length < 5 || overLimit}
          style={{
            width: '100%', padding: '14px 20px',
            border: 'none', borderRadius: '10px',
            background: SIGNAL_BLUE, color: '#FFFFFF',
            fontFamily: 'var(--font-sans)', fontSize: '14px', fontWeight: 600,
            cursor: submitting ? 'wait' : 'pointer',
            opacity: (submitting || message.trim().length < 5 || overLimit) ? 0.5 : 1,
          }}
        >{submitting ? 'Sending...' : 'Send feedback'}</button>
        <button
          onClick={onSkip}
          disabled={submitting}
          style={{
            background: 'transparent', border: 'none',
            color: 'var(--text-tertiary)',
            fontFamily: 'var(--font-sans)', fontSize: '12px', fontWeight: 500,
            padding: '8px', cursor: 'pointer',
          }}
        >Skip</button>
      </div>
    </div>
  );
}


function SubmittedPanel({ onDone }) {
  useEffect(() => {
    const t = setTimeout(() => onDone && onDone(), 2400);
    return () => clearTimeout(t);
  }, [onDone]);
  return (
    <div style={{ padding: '32px 24px 36px', textAlign: 'center' }}>
      <div style={{
        width: '48px', height: '48px', borderRadius: '50%',
        background: 'rgba(90, 158, 114, 0.15)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 18px',
      }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#5A9E72" strokeWidth="3">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>
      <div style={{
        fontFamily: 'var(--font-serif)',
        fontSize: '18px', fontWeight: 500,
        color: 'var(--text-primary)', marginBottom: '6px',
      }}>Thanks. We read every message.</div>
      <div style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5,
      }}>A reply usually arrives within 24 hours.</div>
    </div>
  );
}

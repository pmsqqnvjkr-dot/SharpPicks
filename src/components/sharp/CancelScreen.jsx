import { useState } from 'react';
import { apiPost } from '../../hooks/useApi';

export default function CancelScreen({ onBack, user }) {
  const [selectedReasons, setSelectedReasons] = useState([]);
  const [cancelling, setCancelling] = useState(false);
  const [cancelled, setCancelled] = useState(false);

  const reasons = [
    'Not enough picks',
    'Too expensive',
    'Taking a break from betting',
    'Missing features I need',
    'Other',
  ];

  const toggleReason = (r) => {
    setSelectedReasons(prev =>
      prev.includes(r) ? prev.filter(x => x !== r) : [...prev, r]
    );
  };

  const handleCancel = async () => {
    setCancelling(true);
    try {
      const data = await apiPost('/subscriptions/cancel', { reasons: selectedReasons });
      if (data.success) {
        setCancelled(true);
      } else {
        alert(data.error || 'Unable to cancel. Please try again.');
      }
    } catch (e) {
      alert('Unable to cancel. Please try again.');
    } finally {
      setCancelling(false);
    }
  };

  if (cancelled) {
    return (
      <div style={{ padding: '0', paddingBottom: '100px' }}>
        <div style={{ padding: '16px 20px' }}>
          <button onClick={onBack} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-secondary)', padding: '4px',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
          </button>
        </div>
        <div style={{ padding: '40px 20px', textAlign: 'center' }}>
          <div style={{
            width: '64px', height: '64px', borderRadius: '16px',
            backgroundColor: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 20px',
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5">
              <path d="M9 11l3 3L22 4"/>
              <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
            </svg>
          </div>
          <h2 style={{
            fontFamily: 'var(--font-serif)', fontSize: '22px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '12px',
          }}>Subscription cancelled</h2>
          <p style={{
            fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
            maxWidth: '300px', margin: '0 auto',
          }}>
            You'll keep Pro access through the end of your billing period. You can re-subscribe anytime.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>
      <div style={{
        padding: '16px 20px',
        display: 'flex', alignItems: 'center', gap: '12px',
      }}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-secondary)', padding: '4px',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </button>
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: '16px', fontWeight: 600,
          color: 'var(--text-primary)',
        }}>Cancel Pro</span>
      </div>

      <div style={{ padding: '0 20px' }}>
        <p style={{
          fontSize: '15px', color: 'var(--text-secondary)', lineHeight: '1.6',
          marginBottom: '28px',
        }}>
          Sharp Picks is built for long-term discipline. If it's not the right time, we understand.
        </p>

        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
          letterSpacing: '2px', textTransform: 'uppercase',
          color: 'var(--text-tertiary)', marginBottom: '12px',
        }}>Optional: why are you leaving?</div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '32px' }}>
          {reasons.map(r => (
            <button key={r} onClick={() => toggleReason(r)} style={{
              padding: '10px 16px', borderRadius: '10px',
              backgroundColor: selectedReasons.includes(r) ? 'rgba(79, 134, 247, 0.15)' : 'var(--surface-1)',
              border: selectedReasons.includes(r) ? '1px solid var(--blue-primary)' : '1px solid var(--stroke-subtle)',
              color: selectedReasons.includes(r) ? 'var(--blue-primary)' : 'var(--text-secondary)',
              fontSize: '13px', fontWeight: 500, cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
            }}>
              {r}
            </button>
          ))}
        </div>

        <button
          onClick={handleCancel}
          disabled={cancelling}
          style={{
            width: '100%', padding: '16px',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '14px',
            color: '#EF4444', fontSize: '15px', fontWeight: 600,
            cursor: 'pointer', fontFamily: 'var(--font-sans)',
            marginBottom: '10px',
            opacity: cancelling ? 0.6 : 1,
          }}
        >
          {cancelling ? 'Cancelling...' : 'Confirm cancellation'}
        </button>

        <button onClick={onBack} style={{
          width: '100%', padding: '14px',
          backgroundColor: 'var(--surface-2)',
          border: '1px solid var(--stroke-muted)',
          borderRadius: '12px',
          color: 'var(--text-secondary)', fontSize: '14px', fontWeight: 600,
          cursor: 'pointer', fontFamily: 'var(--font-sans)',
          marginBottom: '10px',
        }}>
          Keep Pro
        </button>

        <p style={{
          fontSize: '12px', color: 'var(--text-tertiary)', lineHeight: '1.6',
          textAlign: 'center', padding: '12px 0',
        }}>
          You'll keep Pro access through the end of your billing period. Cancel anytime — no fees, no questions.
          {user?.founding_member && (
            <span style={{ display: 'block', marginTop: '8px', color: 'var(--gold-pro)' }}>
              Note: if you cancel a founding rate plan, the rate cannot be restored.
            </span>
          )}
        </p>
      </div>
    </div>
  );
}

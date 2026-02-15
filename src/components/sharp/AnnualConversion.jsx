import { useState } from 'react';
import { apiPost } from '../../hooks/useApi';

export default function AnnualConversion({ onBack, user, onDismiss }) {
  const [loading, setLoading] = useState(false);

  const monthsOnMonthly = user?.months_subscribed || 2;
  const monthlySpent = monthsOnMonthly * 29;
  const projectedAnnual = 12 * 29;
  const annualCost = user?.founding_member ? 99 : 149;
  const savings = projectedAnnual - annualCost;

  const userRecord = user?.record || '6-3';
  const userROI = user?.roi || '+11.2';
  const userProfit = user?.net_profit || '+$134';

  const handleSwitch = async () => {
    setLoading(true);
    try {
      const plan = user?.founding_member ? 'founding' : 'annual';
      const data = await apiPost('/subscriptions/create-checkout', { plan });
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else if (data.error) {
        alert(data.error);
      }
    } catch (e) {
      alert('Unable to start checkout. Please try again.');
    } finally {
      setLoading(false);
    }
  };

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
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
          letterSpacing: '2px', textTransform: 'uppercase',
          color: 'var(--text-tertiary)', marginBottom: '20px',
        }}>You've been on Monthly for {monthsOnMonthly} months</div>

        <div style={{ textAlign: 'center', marginBottom: '8px' }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '56px', fontWeight: 800,
            color: 'var(--green-profit)', lineHeight: '1',
          }}>${savings}</div>
          <div style={{
            fontSize: '14px', color: 'var(--text-secondary)', marginTop: '8px',
          }}>You'd save per year by switching</div>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '12px', marginTop: '24px',
        }}>
          <h3 style={{
            fontFamily: 'var(--font-sans)', fontSize: '15px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '16px',
          }}>Your Spending</h3>

          <ConvertRow label={`Monthly so far (${monthsOnMonthly} mo)`} value={`$${monthlySpent}`} color="var(--red-loss)" />
          <ConvertRow label="Projected 12 months" value={`$${projectedAnnual}`} color="var(--red-loss)" />
          <ConvertRow label="Annual plan cost" value={`$${annualCost}`} color="var(--green-profit)" />
          <ConvertRow label="Your savings" value={`$${savings}/year`} color="var(--green-profit)" last />
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '24px',
        }}>
          <h3 style={{
            fontFamily: 'var(--font-sans)', fontSize: '15px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '16px',
          }}>Your Results</h3>

          <ConvertRow label="Record" value={userRecord} />
          <ConvertRow label="ROI" value={userROI + '%'} color="var(--green-profit)" />
          <ConvertRow label="Net profit" value={userProfit} color="var(--green-profit)" last />
        </div>

        <button
          onClick={handleSwitch}
          disabled={loading}
          style={{
            width: '100%', padding: '16px',
            background: 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))',
            border: 'none', borderRadius: '14px',
            color: '#fff', fontSize: '15px', fontWeight: 700,
            cursor: 'pointer', fontFamily: 'var(--font-sans)',
            marginBottom: '10px',
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? 'Opening checkout...' : `Switch to Annual — $${annualCost}/yr`}
        </button>

        <button onClick={onDismiss || onBack} style={{
          width: '100%', padding: '12px',
          backgroundColor: 'transparent',
          border: '1px solid var(--stroke-muted)',
          borderRadius: '12px',
          color: 'var(--text-tertiary)', fontSize: '13px', fontWeight: 600,
          cursor: 'pointer', fontFamily: 'var(--font-sans)',
        }}>Not now</button>

        <p style={{
          fontSize: '11px', color: 'var(--text-tertiary)', lineHeight: '1.5',
          textAlign: 'center', padding: '12px 0',
        }}>
          Switch takes effect at your next billing cycle. No double charge.
        </p>
      </div>
    </div>
  );
}

function ConvertRow({ label, value, color, last }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '10px 0',
      borderBottom: last ? 'none' : '1px solid var(--stroke-subtle)',
    }}>
      <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>{label}</span>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600,
        color: color || 'var(--text-primary)',
      }}>{value}</span>
    </div>
  );
}

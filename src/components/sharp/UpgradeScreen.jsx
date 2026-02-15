import { useState } from 'react';
import { useApi, apiPost } from '../../hooks/useApi';

export default function UpgradeScreen({ onBack }) {
  const { data: foundingData } = useApi('/public/founding-count');
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  const handleSubscribe = async (plan) => {
    setCheckoutLoading(true);
    try {
      const data = await apiPost('/subscriptions/create-checkout', { plan });
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else if (data.error) {
        alert(data.error);
      }
    } catch (e) {
      alert('Unable to start checkout. Please try again.');
    } finally {
      setCheckoutLoading(false);
    }
  };

  const isFoundingOpen = foundingData?.open;
  const annualPrice = isFoundingOpen ? '$99' : '$149';
  const annualLabel = isFoundingOpen ? 'Founding Rate' : 'Standard';

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
        }}>Upgrade to Pro</span>
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          textAlign: 'center', padding: '20px 0 30px',
        }}>
          <div style={{
            width: '72px', height: '72px', borderRadius: '18px',
            background: 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 20px',
          }}>
            <svg viewBox="0 0 40 40" width="40" height="40" fill="none">
              <path d="M20 4L6 10v10c0 9.2 6 17.4 14 20 8-2.6 14-10.8 14-20V10L20 4z" stroke="white" strokeWidth="1.8" fill="none"/>
              <rect x="12" y="24" width="3" height="6" rx="1" fill="rgba(255,255,255,0.3)"/>
              <rect x="17" y="20" width="3" height="10" rx="1" fill="rgba(255,255,255,0.4)"/>
              <rect x="22" y="22" width="3" height="8" rx="1" fill="rgba(255,255,255,0.35)"/>
              <path d="M11 22L17 16L22 19L30 11" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M26 11h4v4" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <h1 style={{
            fontFamily: 'var(--font-serif)', fontSize: '24px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '8px',
          }}>Sharp Picks Pro</h1>
          <p style={{
            fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
            maxWidth: '320px', margin: '0 auto',
          }}>
            Full access to every qualified pick. The model runs daily — Pro sees the complete decision.
          </p>
        </div>

        {isFoundingOpen && (
          <div style={{
            backgroundColor: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.2)',
            borderRadius: '12px', padding: '14px 18px', marginBottom: '16px',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <div style={{
                fontSize: '13px', color: 'var(--gold-pro)', fontWeight: 600,
              }}>Founding member spots</div>
              <div style={{
                fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '2px',
              }}>Lock in $99/yr — rate preserved forever</div>
            </div>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '16px',
              color: 'var(--gold-pro)', fontWeight: 700,
            }}>{foundingData?.remaining}/500</span>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
          <PricingCard
            name="Monthly"
            price="$29"
            period="/mo"
            description="Full access, cancel anytime"
            cta="Subscribe Monthly"
            onSelect={() => handleSubscribe('monthly')}
            loading={checkoutLoading}
          />
          <PricingCard
            name={annualLabel}
            price={annualPrice}
            period="/yr"
            description={isFoundingOpen ? 'Founding rate locked forever' : 'Save vs monthly'}
            cta={isFoundingOpen ? 'Claim Founding Rate' : 'Subscribe Annually'}
            onSelect={() => handleSubscribe(isFoundingOpen ? 'founding' : 'annual')}
            loading={checkoutLoading}
            highlight
          />
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '16px',
        }}>
          <SectionLabel>What Changes</SectionLabel>
          <FeatureRow icon="unlock" text="Full pick details — side, line, edge %" />
          <FeatureRow icon="chart" text="Quantified performance dashboard" />
          <FeatureRow icon="bell" text="Real-time pick notifications" />
          <FeatureRow icon="track" text="Pick-linked bet tracking" />
          <FeatureRow icon="history" text="Complete pick history with analysis" />
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '16px',
        }}>
          <SectionLabel>What Doesn't Change</SectionLabel>
          <FeatureRow icon="same" text="Same model, same edge threshold" />
          <FeatureRow icon="same" text="Still max one pick per day" />
          <FeatureRow icon="same" text="Quiet days are still the product" />
          <FeatureRow icon="same" text="No hype, no FOMO, no volume plays" />
        </div>

        <div style={{
          textAlign: 'center', padding: '12px 0',
        }}>
          <p style={{
            fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6',
          }}>Cancel anytime — no fees, no questions.</p>
        </div>

        <p style={{
          fontSize: '11px', color: 'var(--text-tertiary)', lineHeight: '1.5',
          textAlign: 'center', padding: '8px 0 16px',
        }}>
          Sharp Picks provides statistical analysis, not betting advice.
        </p>
      </div>
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <div style={{
      fontFamily: 'var(--font-mono)',
      fontSize: '10px', fontWeight: 600,
      letterSpacing: '2px', textTransform: 'uppercase',
      color: 'var(--text-tertiary)',
      marginBottom: '14px',
    }}>{children}</div>
  );
}

function PricingCard({ name, price, period, description, cta, onSelect, loading, highlight }) {
  return (
    <div style={{
      padding: '20px', borderRadius: '16px',
      backgroundColor: 'var(--surface-1)',
      border: highlight ? '2px solid var(--blue-primary)' : '1px solid var(--stroke-subtle)',
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: '4px',
      }}>
        <span style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
          {name}
        </span>
        <span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '24px',
            fontWeight: 700, color: 'var(--text-primary)',
          }}>{price}</span>
          <span style={{ fontSize: '13px', color: 'var(--text-tertiary)' }}>{period}</span>
        </span>
      </div>
      <p style={{
        fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px',
      }}>{description}</p>
      <button
        onClick={onSelect}
        disabled={loading}
        style={{
          width: '100%', padding: '14px',
          background: highlight ? 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))' : 'transparent',
          border: highlight ? 'none' : '1px solid var(--stroke-muted)',
          borderRadius: '12px',
          color: highlight ? '#fff' : 'var(--text-primary)',
          fontSize: '14px', fontWeight: 600, cursor: 'pointer',
          fontFamily: 'var(--font-sans)',
          opacity: loading ? 0.6 : 1,
        }}
      >
        {loading ? 'Opening checkout...' : cta}
      </button>
    </div>
  );
}

function FeatureRow({ icon, text }) {
  const iconElement = icon === 'same' ? (
    <span style={{ color: 'var(--text-tertiary)', fontSize: '12px' }}>—</span>
  ) : (
    <span style={{ color: 'var(--green-profit)', fontSize: '12px' }}>&#10003;</span>
  );

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '10px',
      padding: '6px 0',
    }}>
      {iconElement}
      <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>{text}</span>
    </div>
  );
}

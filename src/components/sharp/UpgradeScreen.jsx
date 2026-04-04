import { useState } from 'react';
import { useApi, apiPost } from '../../hooks/useApi';
import { Capacitor } from '@capacitor/core';

const isNative = Capacitor.isNativePlatform();
const WEB_BILLING_URL = 'https://app.sharppicks.ai/upgrade';

export default function UpgradeScreen({ onBack, user }) {
  const { data: foundingData } = useApi('/public/founding-count');
  const { data: statsData } = useApi('/public/stats');
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  const handleSubscribe = async (plan) => {
    if (isNative) {
      const { Browser } = await import('@capacitor/browser');
      await Browser.open({ url: WEB_BILLING_URL });
      return;
    }
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
  const annualLabel = isFoundingOpen ? 'Founding Member' : 'Annual';
  const spotsRemaining = foundingData?.remaining || 0;
  const isTrial = user?.subscription_status === 'trial';

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
          textAlign: 'center', padding: '20px 0 24px',
        }}>
          <div style={{ margin: '0 auto 20px' }}>
            <svg width="44" height="44" viewBox="0 0 500 500">
              <rect x="150" y="100" width="60" height="300" rx="30" fill="#FFFFFF" />
              <rect x="290" y="100" width="60" height="300" rx="30" fill="#FFFFFF" />
              <rect x="150" y="420" width="200" height="20" rx="10" fill="#5A9E72" />
            </svg>
          </div>
          <h1 style={{
            fontFamily: 'var(--font-serif)', fontSize: '24px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '8px',
          }}>Sharp Picks Pro</h1>
          <p style={{
            fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
            maxWidth: '300px', margin: '0 auto',
          }}>
            Full access to every qualified decision. Not more picks. More transparency.
          </p>
          <p style={{
            fontSize: '12px', color: 'var(--text-tertiary)', lineHeight: '1.5',
            maxWidth: '300px', margin: '8px auto 0',
          }}>
            This is how disciplined bettors compound.
          </p>
        </div>

        {isTrial && (
          <div style={{
            textAlign: 'center',
            padding: '10px 16px 14px',
            marginBottom: '16px',
            borderRadius: '10px',
            background: 'rgba(10,13,20,0.6)',
            border: '1px solid rgba(255,255,255,0.06)',
          }}>
            <span style={{
              fontFamily: 'var(--font-sans)',
              fontSize: '13px',
              color: 'var(--text-secondary)',
              lineHeight: 1.5,
            }}>When your trial ends, the full decision disappears.</span>
          </div>
        )}

        {(statsData?.pnl != null || statsData?.roi != null || statsData?.selectivity != null) && (
          <div style={{
            display: 'flex', justifyContent: 'center', gap: '24px',
            padding: '14px 0', marginBottom: '16px',
            borderRadius: '12px',
            background: 'rgba(10,13,20,0.5)',
            border: '1px solid rgba(255,255,255,0.05)',
          }}>
            {statsData?.pnl != null && (
              <div style={{ textAlign: 'center' }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700,
                  color: 'var(--green-profit)',
                }}>{statsData.pnl > 0 ? '+' : ''}{statsData.pnl}u</div>
                <div style={{
                  fontFamily: 'var(--font-sans)', fontSize: '10px',
                  color: 'var(--text-tertiary)', textTransform: 'uppercase',
                  letterSpacing: '0.08em', marginTop: '2px',
                }}>Model-Only Perf.</div>
              </div>
            )}
            {statsData?.roi != null && (
              <div style={{ textAlign: 'center' }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700,
                  color: 'var(--green-profit)',
                }}>{statsData.roi}%</div>
                <div style={{
                  fontFamily: 'var(--font-sans)', fontSize: '10px',
                  color: 'var(--text-tertiary)', textTransform: 'uppercase',
                  letterSpacing: '0.08em', marginTop: '2px',
                }}>ROI</div>
              </div>
            )}
            {statsData?.selectivity != null && (
              <div style={{ textAlign: 'center' }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700,
                  color: 'var(--text-primary)',
                }}>{statsData.selectivity}%</div>
                <div style={{
                  fontFamily: 'var(--font-sans)', fontSize: '10px',
                  color: 'var(--text-tertiary)', textTransform: 'uppercase',
                  letterSpacing: '0.08em', marginTop: '2px',
                }}>Select. (vs 78% avg)</div>
              </div>
            )}
          </div>
        )}

        {!isNative && isFoundingOpen && (
          <div style={{
            backgroundColor: 'rgba(245, 158, 11, 0.06)',
            border: '1px solid rgba(245, 158, 11, 0.18)',
            borderRadius: '12px', padding: '14px 18px', marginBottom: '16px',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <div style={{
                fontSize: '13px', color: 'var(--gold-pro)', fontWeight: 600,
              }}>Founding rate closes at 50 members.</div>
              <div style={{
                fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '3px',
              }}>{spotsRemaining} remaining.</div>
            </div>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '18px',
              color: 'var(--gold-pro)', fontWeight: 700,
            }}>{spotsRemaining}</span>
          </div>
        )}

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '12px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '16px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
            letterSpacing: '1.5px', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '12px',
          }}>YOUR PLAN: FREE</div>
          <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 20px 0' }}>
            {['See if a pick exists today', 'Public model record access', 'Daily Market Brief', 'Sharp Journal access', 'Full game slate with edges'].map(f => (
              <li key={f} style={{ fontSize: '12px', color: 'var(--text-secondary)', padding: '4px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: 'var(--green-profit)', fontSize: '10px' }}>&#10003;</span>{f}
              </li>
            ))}
          </ul>

          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
            letterSpacing: '1.5px', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '12px',
            paddingTop: '16px', borderTop: '1px solid var(--stroke-subtle)',
          }}>PRO INCLUDES EVERYTHING ABOVE, PLUS:</div>
          <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 20px 0' }}>
            {['Full signal details (side, line, edge, sizing)', 'Quant reasoning and model analysis', 'Personal bet tracking with CLV', 'Equity curve and P&L history', 'Discipline scoring with benchmarks', 'Real-time push notifications', 'Priority support'].map(f => (
              <li key={f} style={{ fontSize: '12px', color: 'var(--text-secondary)', padding: '4px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: 'var(--green-profit)', fontSize: '10px' }}>&#10003;</span>{f}
              </li>
            ))}
          </ul>

          <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', textAlign: 'center', marginBottom: '14px', lineHeight: '1.5' }}>
            Pricing and subscription options<br />available at sharppicks.ai
          </div>

          <button onClick={() => window.open('https://sharppicks.ai/#pricing', '_blank')} style={{
            width: '100%', padding: '12px', borderRadius: '6px',
            background: '#5A9E72', border: 'none',
            color: '#0A0D14', fontFamily: 'var(--font-mono)',
            fontSize: '12px', fontWeight: 600, letterSpacing: '1px',
            cursor: 'pointer', textAlign: 'center',
          }}>View Plans</button>

          <div style={{ textAlign: 'center', marginTop: '10px', fontSize: '11px', color: 'var(--text-tertiary)', lineHeight: '1.5' }}>
            14-day free trial available. Cancel anytime.
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '16px',
        }}>
          <SectionLabel>What Changes</SectionLabel>
          <FeatureRow icon="unlock" text="Full pick transparency: side, line, edge %" />
          <FeatureRow icon="chart" text="Quantified performance dashboard" />
          <FeatureRow icon="bell" text="Real-time pick alerts" />
          <FeatureRow icon="track" text="Pick-linked tracking" />
          <FeatureRow icon="history" text="Complete historical analysis" />
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '16px',
        }}>
          <SectionLabel>What Doesn't Change</SectionLabel>
          <FeatureRow icon="same" text="Same model. Same thresholds." />
          <FeatureRow icon="same" text="Max one pick per day." />
          <FeatureRow icon="same" text="Quiet days are intentional." />
          <FeatureRow icon="same" text="No hype. No FOMO. No volume plays." />
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

function PricingCard({ name, price, period, description, cta, onSelect, loading, highlight, badge, savings, secondary }) {
  return (
    <div style={{
      padding: secondary ? '16px 20px' : '20px', borderRadius: '16px',
      backgroundColor: highlight ? 'rgba(79,134,247,0.04)' : 'var(--surface-1)',
      border: highlight ? '2px solid var(--blue-primary)' : `1px solid ${secondary ? 'var(--stroke-subtle)' : 'var(--stroke-subtle)'}`,
      position: 'relative',
      ...(highlight ? { boxShadow: '0 0 20px rgba(79,134,247,0.08)' } : {}),
      ...(secondary ? { opacity: 0.75 } : {}),
    }}>
      {badge && (
        <div style={{
          position: 'absolute', top: '-10px', right: '16px',
          background: 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))',
          color: '#fff', fontSize: '10px', fontWeight: 700,
          padding: '3px 10px', borderRadius: '6px',
          fontFamily: 'var(--font-sans)',
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
        }}>{badge}</div>
      )}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        marginBottom: '4px',
      }}>
        <span style={{ fontSize: secondary ? '14px' : '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
          {name}
        </span>
        <span>
          {price && <span style={{
            fontFamily: 'var(--font-mono)', fontSize: secondary ? '20px' : '24px',
            fontWeight: 700, color: 'var(--text-primary)',
          }}>{price}</span>}
          <span style={{ fontSize: '13px', color: 'var(--text-tertiary)' }}>{period}</span>
        </span>
      </div>
      <p style={{
        fontSize: '13px', color: 'var(--text-secondary)', marginBottom: savings ? '4px' : secondary ? '12px' : '16px',
      }}>{description}</p>
      {savings && (
        <p style={{
          fontSize: '11px', color: 'var(--green-profit)', marginBottom: '14px',
          fontFamily: 'var(--font-mono)',
        }}>{savings}</p>
      )}
      <button
        onClick={onSelect}
        disabled={loading}
        style={{
          width: '100%', padding: secondary ? '11px' : '14px',
          background: highlight ? 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))' : 'transparent',
          border: highlight ? 'none' : '1px solid var(--stroke-muted)',
          borderRadius: '12px',
          color: highlight ? '#fff' : 'var(--text-secondary)',
          fontSize: secondary ? '13px' : '14px', fontWeight: 600, cursor: 'pointer',
          fontFamily: 'var(--font-sans)',
          opacity: loading ? 0.6 : 1,
          ...(highlight ? { boxShadow: '0 0 16px rgba(79,134,247,0.2)' } : {}),
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

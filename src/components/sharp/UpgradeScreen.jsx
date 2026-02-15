import { useState } from 'react';
import { useApi, apiPost } from '../../hooks/useApi';

export default function UpgradeScreen({ onBack, user }) {
  const { data: foundingData } = useApi('/public/founding-count');
  const { data: statsData } = useApi('/public/stats');
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
  const spotsRemaining = foundingData?.remaining || 0;
  const annualPrice = isFoundingOpen ? '$99' : '$149';
  const annualLabel = isFoundingOpen ? 'Founding Rate' : 'Standard';

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
            maxWidth: '320px', margin: '0 auto 0',
          }}>
            Full access to every qualified pick. The model runs daily — Pro sees the complete decision.
          </p>
          <p style={{
            fontSize: '13px', color: 'var(--text-tertiary)', lineHeight: '1.5',
            maxWidth: '320px', margin: '10px auto 0',
            fontStyle: 'italic',
          }}>
            This is not more picks. It's full transparency.
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
            }}>When your trial ends, edge visibility narrows.</span>
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
                }}>Model-Only</div>
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
                }}>Selectivity</div>
              </div>
            )}
          </div>
        )}

        {isFoundingOpen && (
          <div style={{
            backgroundColor: 'rgba(245, 158, 11, 0.06)',
            border: '1px solid rgba(245, 158, 11, 0.18)',
            borderRadius: '12px', padding: '14px 18px', marginBottom: '16px',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <div style={{
                fontSize: '13px', color: 'var(--gold-pro)', fontWeight: 600,
              }}>Founding Members: {spotsRemaining} / {foundingData?.total || 500} Remaining</div>
              <div style={{
                fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '3px',
              }}>{spotsRemaining <= 20
                ? `Only ${spotsRemaining} ${spotsRemaining === 1 ? 'spot' : 'spots'} left at this price.`
                : 'Lock in $99/yr — rate preserved forever'
              }</div>
            </div>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '18px',
              color: 'var(--gold-pro)', fontWeight: 700,
            }}>{spotsRemaining}</span>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
          {isFoundingOpen && (
            <PricingCard
              name={annualLabel}
              price={annualPrice}
              period="/yr"
              description="Founding rate locked forever"
              cta="Claim Founding Rate"
              onSelect={() => handleSubscribe('founding')}
              loading={checkoutLoading}
              highlight
              badge="Best Value"
              savings="Save $249 vs monthly"
            />
          )}
          <PricingCard
            name="Monthly"
            price="$29"
            period="/mo"
            description="Full access, cancel anytime"
            cta="Subscribe Monthly"
            onSelect={() => handleSubscribe('monthly')}
            loading={checkoutLoading}
            secondary
          />
          {!isFoundingOpen && (
            <PricingCard
              name={annualLabel}
              price={annualPrice}
              period="/yr"
              description="Save vs monthly"
              cta="Subscribe Annually"
              onSelect={() => handleSubscribe('annual')}
              loading={checkoutLoading}
              highlight
              savings="Save $199 vs monthly"
            />
          )}
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
          }}>Cancel anytime. No hidden fees. No auto price increases.</p>
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
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: secondary ? '20px' : '24px',
            fontWeight: 700, color: 'var(--text-primary)',
          }}>{price}</span>
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

import { useState, useEffect } from 'react';
import { useApi, apiPost } from '../../hooks/useApi';
import { useAuth } from '../../hooks/useAuth';
import { Capacitor } from '@capacitor/core';
import { getOfferings, purchasePackage, restorePurchases, isPurchaseCancelled } from '../../lib/revenuecat';

const platform = Capacitor.getPlatform();
const isIOS = platform === 'ios';
const isNative = Capacitor.isNativePlatform();
const WEB_BILLING_URL = 'https://app.sharppicks.ai/signup';

export default function UpgradeScreen({ onBack, user }) {
  const { data: foundingData } = useApi('/public/founding-count');
  const { data: statsData } = useApi('/public/stats');
  const { checkAuth } = useAuth();
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [iapOffering, setIapOffering] = useState(null);
  const [selectedPlan, setSelectedPlan] = useState('yearly');
  const [iapError, setIapError] = useState('');
  const [iapSuccess, setIapSuccess] = useState('');
  const [restoringPurchases, setRestoringPurchases] = useState(false);
  const [loadingOfferings, setLoadingOfferings] = useState(isIOS);

  const loadOfferings = async () => {
    if (!isIOS) return;
    setLoadingOfferings(true);
    setIapError('');
    try {
      const offering = await getOfferings();
      if (offering) {
        setIapOffering(offering);
        return;
      }
      setIapOffering(null);
      setIapError('Unable to load App Store products. Please try again.');
    } catch (e) {
      setIapOffering(null);
      setIapError('Unable to load App Store products. Please try again.');
    } finally {
      setLoadingOfferings(false);
    }
  };

  useEffect(() => {
    if (!isIOS) return;
    loadOfferings();
  }, []);

  // Open a legal URL via the Capacitor in-app browser when running
  // inside the WebView (iOS, Android), or a new tab on the web. Used
  // for the Privacy Policy and Terms of Use links required by 3.1.2(c).
  const openLegal = async (url) => {
    try {
      const { Browser } = await import('@capacitor/browser');
      await Browser.open({ url });
    } catch {
      try { window.open(url, '_blank', 'noopener,noreferrer'); } catch { /* swallow */ }
    }
  };

  // Apple doesn't let us cancel subscriptions in-app. Send already-pro
  // users to App Store account settings. Same path the PaymentFailedGate
  // uses (SharpPicksApp.jsx:32). Trial users also have is_premium=true
  // and need this surface so they can cancel before being charged.
  const isAlreadyPro = !!user?.is_premium;
  const openManageSubscriptions = async () => {
    try {
      const { Browser } = await import('@capacitor/browser');
      await Browser.open({ url: 'https://apps.apple.com/account/subscriptions' });
    } catch {
      try { window.open('https://apps.apple.com/account/subscriptions', '_blank', 'noopener,noreferrer'); } catch { /* swallow */ }
    }
  };

  const handleStripeSubscribe = async (plan) => {
    if (isNative) {
      const { Browser } = await import('@capacitor/browser');
      await Browser.open({ url: WEB_BILLING_URL });
      return;
    }
    setCheckoutLoading(true);
    try {
      const data = await apiPost('/subscriptions/create-checkout', { plan });
      if (data.checkout_url) {
        if (Capacitor.getPlatform() === 'android') {
          const { Browser } = await import('@capacitor/browser');
          await Browser.open({ url: data.checkout_url });
        } else {
          window.location.href = data.checkout_url;
        }
      } else if (data.error) {
        alert(data.error);
      }
    } catch (e) {
      alert('Unable to start checkout. Please try again.');
    } finally {
      setCheckoutLoading(false);
    }
  };

  const handleIAPPurchase = async () => {
    if (!iapOffering) return;
    const pkg = selectedPlan === 'yearly'
      ? iapOffering.annual
      : iapOffering.monthly;
    if (!pkg) return;

    setCheckoutLoading(true);
    setIapError('');
    try {
      const customerInfo = await purchasePackage(pkg);
      const isPro = !!customerInfo?.entitlements?.active?.pro;
      if (isPro) {
        const expires = customerInfo.entitlements.active.pro.expirationDate;
        const trialEnd = expires ? new Date(expires).toLocaleDateString() : '';
        setIapSuccess(trialEnd ? `Pro activated. Trial ends ${trialEnd}.` : 'Pro activated.');
        if (checkAuth) checkAuth();
      }
    } catch (e) {
      if (!isPurchaseCancelled(e)) {
        setIapError(e?.message || 'Purchase failed. Please try again.');
      }
    } finally {
      setCheckoutLoading(false);
    }
  };

  const handleRestore = async () => {
    setRestoringPurchases(true);
    setIapError('');
    try {
      const customerInfo = await restorePurchases();
      if (customerInfo?.entitlements?.active?.pro) {
        setIapSuccess('Purchases restored. Pro is active.');
        if (checkAuth) checkAuth();
      } else {
        setIapError('No active subscription found.');
      }
    } catch (e) {
      setIapError('Restore failed. Please try again.');
    } finally {
      setRestoringPurchases(false);
    }
  };

  const isFoundingOpen = foundingData?.open;
  const spotsRemaining = foundingData?.remaining || 0;
  const isTrial = user?.subscription_status === 'trial';

  const yearlyPkg = iapOffering?.annual;
  const monthlyPkg = iapOffering?.monthly;
  const yearlyPrice = yearlyPkg?.product?.priceString || '';
  const monthlyPrice = monthlyPkg?.product?.priceString || '';

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
          }}>SharpPicks Pro</h1>
          <p style={{
            fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6',
            maxWidth: '300px', margin: '0 auto',
          }}>
            Full access to every qualified signal. Selective by design.
          </p>
          <p style={{
            fontSize: '12px', color: 'var(--text-tertiary)', lineHeight: '1.5',
            maxWidth: '300px', margin: '8px auto 0',
          }}>
            Discipline is the edge.
          </p>
        </div>

        {isIOS && (
          <div style={{
            display: 'flex', alignItems: 'flex-start', gap: '12px',
            padding: '14px 16px',
            marginBottom: '16px',
            borderRadius: '12px',
            background: 'rgba(10,13,20,0.6)',
            border: '1px solid rgba(79, 134, 247, 0.25)',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4F86F7" strokeWidth="2" style={{ flexShrink: 0, marginTop: '2px' }}>
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div style={{ minWidth: 0 }}>
              <div style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '10px', fontWeight: 600,
                letterSpacing: '0.16em', textTransform: 'uppercase',
                color: 'var(--text-tertiary)',
                marginBottom: '4px',
              }}>Subscription notice</div>
              <div style={{
                fontFamily: 'var(--font-sans)',
                fontSize: '14px', lineHeight: 1.5,
                color: 'var(--text-primary)',
              }}>
                If in-app purchases fail to load, sign up directly at{' '}
                <a
                  href="https://sharppicks.ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    fontFamily: 'var(--font-mono)',
                    color: '#4F86F7', textDecoration: 'none', fontWeight: 500,
                  }}
                >sharppicks.ai</a>
              </div>
            </div>
          </div>
        )}

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

        {!isIOS && isFoundingOpen && (
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

        {iapSuccess && (
          <div style={{
            backgroundColor: 'rgba(90, 158, 114, 0.1)',
            border: '1px solid rgba(90, 158, 114, 0.2)',
            borderRadius: '10px', padding: '12px 16px', marginBottom: '16px',
            fontSize: '13px', color: 'var(--green-profit)', textAlign: 'center',
          }}>{iapSuccess}</div>
        )}

        {iapError && (
          <div style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: '10px', padding: '12px 16px', marginBottom: '16px',
            fontSize: '13px', color: 'var(--red-loss)', textAlign: 'center',
          }}>{iapError}</div>
        )}

        {isIOS ? (
          <>
            {!iapOffering && (
              <div style={{
                border: '1px solid rgba(255,255,255,0.08)',
                backgroundColor: 'rgba(10, 13, 20, 0.55)',
                borderRadius: '12px',
                padding: '12px',
                marginBottom: '16px',
                textAlign: 'center',
              }}>
                <div style={{
                  fontSize: '12px',
                  color: 'var(--text-tertiary)',
                  marginBottom: '8px',
                }}>
                  {loadingOfferings ? 'Loading App Store products...' : 'Products unavailable right now.'}
                </div>
                <button
                  type="button"
                  onClick={loadOfferings}
                  disabled={loadingOfferings}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--stroke-muted)',
                    background: 'var(--surface-2)',
                    color: 'var(--text-primary)',
                    fontSize: '12px',
                    cursor: loadingOfferings ? 'default' : 'pointer',
                    opacity: loadingOfferings ? 0.6 : 1,
                  }}
                >
                  {loadingOfferings ? 'Loading...' : 'Retry'}
                </button>
              </div>
            )}

            {!isAlreadyPro && (
              <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
                <PlanToggle
                  label="Annual"
                  price={yearlyPrice}
                  duration="year"
                  selected={selectedPlan === 'yearly'}
                  onSelect={() => setSelectedPlan('yearly')}
                  badge="14-day trial"
                />
                <PlanToggle
                  label="Monthly"
                  price={monthlyPrice}
                  duration="month"
                  selected={selectedPlan === 'monthly'}
                  onSelect={() => setSelectedPlan('monthly')}
                />
              </div>
            )}

            <button
              onClick={isAlreadyPro ? openManageSubscriptions : handleIAPPurchase}
              disabled={!isAlreadyPro && (checkoutLoading || !iapOffering)}
              style={{
                width: '100%', padding: '16px',
                background: 'linear-gradient(135deg, #5A9E72, #4A8E62)',
                border: 'none', borderRadius: '14px',
                color: '#fff', fontSize: '16px', fontWeight: 700,
                cursor: 'pointer', fontFamily: 'var(--font-sans)',
                opacity: (!isAlreadyPro && (checkoutLoading || !iapOffering)) ? 0.6 : 1,
                marginBottom: '12px',
              }}
            >
              {isAlreadyPro
                ? 'Manage Subscription'
                : (checkoutLoading ? 'Processing...' : 'Subscribe with Apple')}
            </button>

            {/* Apple-required auto-renewal disclosure (3.1.2(c)). Only
                shown pre-purchase; an already-subscribed user doesn't
                need the renewal terms again. */}
            {!isAlreadyPro && (
              <p style={{
                fontFamily: 'var(--font-sans)', fontSize: '11px',
                lineHeight: 1.5, color: 'var(--text-tertiary)',
                textAlign: 'left', margin: '0 0 12px',
              }}>
                Payment will be charged to your Apple ID account at confirmation of purchase. Subscription automatically renews unless canceled at least 24 hours before the end of the current period. Your account will be charged for renewal within 24 hours prior to the end of the current period. You can manage and cancel your subscriptions in your App Store account settings after purchase.
              </p>
            )}

            <button
              onClick={handleRestore}
              disabled={restoringPurchases}
              style={{
                display: 'block', width: '100%', padding: '8px',
                background: 'none', border: 'none',
                color: 'var(--text-tertiary)', fontSize: '11px',
                cursor: 'pointer', fontFamily: 'var(--font-sans)',
                textAlign: 'center', marginBottom: '12px',
                opacity: restoringPurchases ? 0.5 : 1,
              }}
            >
              {restoringPurchases ? 'Restoring...' : 'Restore Purchase'}
            </button>

            {/* Required legal links (3.1.2(c)). Privacy on the
                SharpPicks domain, Terms uses Apple's standard EULA URL. */}
            <div style={{
              display: 'flex', justifyContent: 'center', alignItems: 'center',
              gap: '8px', marginBottom: '4px',
              fontFamily: 'var(--font-sans)', fontSize: '12px',
              color: 'var(--text-tertiary)',
            }}>
              <button
                type="button"
                onClick={() => openLegal('https://sharppicks.ai/privacy')}
                style={{
                  background: 'none', border: 'none', padding: 0,
                  color: 'var(--text-tertiary)', fontSize: '12px',
                  fontFamily: 'var(--font-sans)', cursor: 'pointer',
                  textDecoration: 'underline',
                }}
              >Privacy Policy</button>
              <span aria-hidden="true">·</span>
              <button
                type="button"
                onClick={() => openLegal('https://www.apple.com/legal/internet-services/itunes/dev/stdeula/')}
                style={{
                  background: 'none', border: 'none', padding: 0,
                  color: 'var(--text-tertiary)', fontSize: '12px',
                  fontFamily: 'var(--font-sans)', cursor: 'pointer',
                  textDecoration: 'underline',
                }}
              >Terms of Use</button>
            </div>
          </>
        ) : (
          <>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '16px' }}>
              <PricingCard
                name={isFoundingOpen ? 'Founding Member' : 'Annual'}
                price={isFoundingOpen ? '$99' : '$149.99'}
                period="/yr"
                description={isFoundingOpen
                  ? `Lock the founding rate. ${spotsRemaining} of 50 spots left.`
                  : 'Best value, save vs monthly.'}
                savings={isFoundingOpen ? 'Founding rate locked while subscribed' : null}
                cta="Start 14-day free trial"
                onSelect={() => handleStripeSubscribe(isFoundingOpen ? 'trial' : 'annual_standard')}
                loading={checkoutLoading}
                highlight
                badge={isFoundingOpen ? 'Best Value' : null}
              />
              <PricingCard
                name="Monthly"
                price="$19.99"
                period="/mo"
                description="Full Pro access, billed monthly."
                cta="Subscribe monthly"
                onSelect={() => handleStripeSubscribe('monthly')}
                loading={checkoutLoading}
                secondary
              />
            </div>

            {isNative && (
              <div style={{ textAlign: 'center', marginBottom: '16px', fontSize: '11px', color: 'var(--text-tertiary)' }}>
                Continues in your browser
              </div>
            )}
          </>
        )}

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '16px',
        }}>
          <SectionLabel>What You Get</SectionLabel>
          <FeatureRow icon="unlock" text="Full signal data: side, line, edge %, sizing" />
          <FeatureRow icon="chart" text="Quantified performance dashboard" />
          <FeatureRow icon="bell" text="Real-time push notifications" />
          <FeatureRow icon="track" text="Signal-linked tracking with closing line value" />
          <FeatureRow icon="history" text="Complete historical record" />
          <FeatureRow icon="unlock" text="Discipline scoring with benchmarks" />
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '16px',
        }}>
          <SectionLabel>What Doesn't Change</SectionLabel>
          <FeatureRow icon="same" text="Same model. Same thresholds." />
          <FeatureRow icon="same" text="One signal per day, maximum." />
          <FeatureRow icon="same" text="Pass days are intentional." />
          <FeatureRow icon="same" text="Verified by data, not talk." />
        </div>

        <p style={{
          fontSize: '11px', color: 'var(--text-tertiary)', lineHeight: '1.5',
          textAlign: 'center', padding: '8px 0 16px',
        }}>
          {isIOS ? 'Payment is charged to your Apple ID account.' : '14-day free trial on annual plan. Cancel anytime.'}
        </p>
      </div>
    </div>
  );
}

function PlanToggle({ label, price, duration, selected, onSelect, badge }) {
  return (
    <button
      onClick={onSelect}
      style={{
        flex: 1, padding: '14px 12px', borderRadius: '12px',
        background: selected ? 'rgba(79,134,247,0.06)' : 'var(--surface-1)',
        border: selected ? '2px solid var(--blue-primary)' : '1px solid var(--stroke-subtle)',
        cursor: 'pointer', textAlign: 'center', position: 'relative',
      }}
    >
      {badge && (
        <div style={{
          position: 'absolute', top: '-8px', left: '50%', transform: 'translateX(-50%)',
          background: 'var(--blue-primary)', color: '#fff',
          fontSize: '9px', fontWeight: 700, padding: '2px 8px',
          borderRadius: '4px', fontFamily: 'var(--font-sans)',
          letterSpacing: '0.04em', textTransform: 'uppercase',
          whiteSpace: 'nowrap',
        }}>{badge}</div>
      )}
      <div style={{
        fontSize: '13px', fontWeight: 600,
        color: selected ? 'var(--text-primary)' : 'var(--text-secondary)',
        marginBottom: '4px',
      }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700,
        color: selected ? 'var(--text-primary)' : 'var(--text-tertiary)',
      }}>{price}{duration ? ` / ${duration}` : ''}</div>
    </button>
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

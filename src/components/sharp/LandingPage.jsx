import { useState, useEffect } from 'react';
import { useApi } from '../../hooks/useApi';
import { Capacitor } from '@capacitor/core';
import AuthModal from './AuthModal';
import Wordmark from './Wordmark';
import { getOfferings } from '../../lib/revenuecat';

const isNative = Capacitor.isNativePlatform();
const isIOS = Capacitor.getPlatform() === 'ios';

const SECTION_MAX = 1080;
const GRID_PAD = 'clamp(20px, 5vw, 64px)';

const sectionStyle = {
  maxWidth: SECTION_MAX,
  margin: '0 auto',
  padding: `0 ${GRID_PAD}`,
};

const GREEN = 'var(--green-profit)';
const GREEN_DARK = 'var(--green-dark)';
const GREEN_BG_08 = 'rgba(90, 158, 114, 0.08)';
const GREEN_BG_12 = 'rgba(90, 158, 114, 0.12)';
const GREEN_BORDER = 'rgba(90, 158, 114, 0.20)';
const GREEN_BORDER_30 = 'rgba(90, 158, 114, 0.30)';

function Step({ num, title, body }) {
  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
      <div style={{
        width: 32, height: 32, borderRadius: 8,
        background: GREEN_BG_12, border: `1px solid ${GREEN_BORDER}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600,
        color: GREEN, flexShrink: 0, marginTop: 2,
      }}>{num}</div>
      <div>
        <h3 style={{
          fontFamily: 'var(--font-serif)', fontSize: 16, fontWeight: 500,
          color: 'var(--text-primary)', marginBottom: 6, lineHeight: 1.35,
        }}>{title}</h3>
        <p style={{
          fontFamily: 'var(--font-sans)', fontSize: 13, lineHeight: 1.65,
          color: 'var(--text-secondary)',
        }}>{body}</p>
      </div>
    </div>
  );
}

function FeatureCard({ title, body, accent }) {
  return (
    <div style={{
      background: 'var(--surface-1)',
      border: '1px solid var(--stroke-subtle)',
      borderLeft: `2px solid ${accent}`,
      borderRadius: 10, padding: '28px 24px',
    }}>
      <h3 style={{
        fontFamily: 'var(--font-serif)', fontSize: 16, fontWeight: 500,
        color: 'var(--text-primary)', marginBottom: 10, lineHeight: 1.35,
      }}>{title}</h3>
      <p style={{
        fontFamily: 'var(--font-sans)', fontSize: 13, lineHeight: 1.65,
        color: 'var(--text-secondary)',
      }}>{body}</p>
    </div>
  );
}

function SignalCardMock() {
  return (
    <div style={{
      maxWidth: 520, margin: '0 auto',
      background: 'var(--surface-1)',
      border: '1px solid var(--stroke-subtle)',
      borderRadius: 12, overflow: 'hidden',
    }}>
      <div style={{ padding: '20px 24px 16px', borderBottom: '1px solid var(--stroke-subtle)' }}>
        <div style={{
          fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 500,
          color: 'var(--text-primary)', marginBottom: 4,
        }}>Minnesota Timberwolves +10.0</div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-tertiary)', letterSpacing: '0.04em',
        }}>MIN @ BOS · 7:10 PM ET</div>
      </div>
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
        borderBottom: '1px solid var(--stroke-subtle)',
      }}>
        {[
          { l: 'SIGNAL', v: '+8.0%' },
          { l: 'COVER PROB', v: '61.6%' },
          { l: 'PROJ MARGIN', v: '+7.1' },
        ].map((c, i) => (
          <div key={c.l} style={{
            padding: 16, textAlign: 'center',
            borderRight: i < 2 ? '1px solid var(--stroke-subtle)' : 'none',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 9,
              letterSpacing: '0.12em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', marginBottom: 4,
            }}>{c.l}</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 500,
              color: GREEN,
            }}>{c.v}</div>
          </div>
        ))}
      </div>
      <div style={{ padding: '18px 24px' }}>
        <div style={{
          fontFamily: 'var(--font-serif)', fontStyle: 'italic',
          fontSize: 13, color: 'var(--text-secondary)', marginBottom: 14,
        }}>Playable down to +8. Edge invalidates beyond.</div>
        <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {[
            'MIN 118.7 PPG vs BOS DEF 107.1 allowed',
            'Rest advantage: MIN 2 days vs BOS back-to-back',
            'Spread-adjusted scoring margin: +3.6',
            'Model consensus: 4/4 models agree (GBM, RF, XGB, ADA)',
          ].map(line => (
            <li key={line} style={{
              fontFamily: 'var(--font-sans)', fontSize: 12,
              color: 'var(--text-secondary)', padding: '3px 0',
              display: 'flex', alignItems: 'flex-start', gap: 8, lineHeight: 1.5,
            }}>
              <span style={{
                fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)', flexShrink: 0,
              }}>·</span>
              <span>{line}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function BehavioralMock() {
  const stats = [
    { v: '+$612', l: 'Portfolio P/L', g: true },
    { v: '+36%', l: 'ROI', g: true },
    { v: '12-5', l: 'Record' },
    { v: '58.1%', l: 'Selectivity' },
    { v: 'B', l: 'Discipline' },
  ];
  return (
    <div style={{
      maxWidth: 520,
      background: 'var(--surface-1)',
      border: '1px solid var(--stroke-subtle)',
      borderRadius: 12, padding: '32px 28px',
    }}>
      <div style={{
        display: 'flex', gap: 24, marginBottom: 20, flexWrap: 'wrap',
      }}>
        {stats.map(s => (
          <div key={s.l}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 24, fontWeight: 500,
              color: s.g ? GREEN : 'var(--text-primary)',
            }}>{s.v}</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', marginTop: 2,
            }}>{s.l}</div>
          </div>
        ))}
      </div>
      <p style={{
        fontFamily: 'var(--font-sans)', fontSize: 13, lineHeight: 1.65,
        color: 'var(--text-secondary)',
      }}>
        Your tracked bets at actual stakes. +5.9 units across 17 bets at 1u flat.
        Selectivity rate of 58.1% vs industry average of 78%. Fewer decisions, better decisions.
      </p>
    </div>
  );
}

function PriceCard({ tier, price, sub, features, ctaLabel, onCta, highlight, badge }) {
  return (
    <div style={{
      background: 'var(--surface-1)',
      border: `1px solid ${highlight ? GREEN : 'var(--stroke-subtle)'}`,
      boxShadow: highlight ? `0 0 40px ${GREEN_BG_08}` : 'none',
      borderRadius: 12, padding: '28px 24px',
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 12,
        letterSpacing: '0.10em', textTransform: 'uppercase',
        color: 'var(--text-tertiary)', marginBottom: 12,
      }}>
        {tier}
        {badge && (
          <span style={{
            fontSize: 9, color: GREEN, background: GREEN_BG_12,
            padding: '2px 8px', borderRadius: 4,
            marginLeft: 8, verticalAlign: 'middle',
          }}>{badge}</span>
        )}
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 36, fontWeight: 700,
        color: 'var(--text-primary)', marginBottom: 2,
      }}>{price}</div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 11,
        color: 'var(--text-tertiary)', marginBottom: 20,
      }}>{sub}</div>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, marginBottom: 24, flex: 1 }}>
        {features.map(f => (
          <li key={f} style={{
            fontFamily: 'var(--font-sans)', fontSize: 12,
            color: 'var(--text-secondary)', padding: '4px 0',
            display: 'flex', alignItems: 'flex-start', gap: 8, lineHeight: 1.5,
          }}>
            <span style={{
              fontFamily: 'var(--font-mono)', color: GREEN,
              flexShrink: 0, fontSize: 10,
            }}>{'>'}</span>
            <span>{f}</span>
          </li>
        ))}
      </ul>
      <button onClick={onCta} style={{
        display: 'block', width: '100%', textAlign: 'center',
        fontFamily: 'var(--font-mono)', fontSize: 12,
        letterSpacing: '0.04em', padding: '12px 20px', borderRadius: 8,
        cursor: 'pointer', border: 'none',
        background: highlight ? GREEN : 'transparent',
        color: highlight ? '#fff' : 'var(--text-secondary)',
        outline: highlight ? 'none' : '1px solid var(--stroke-subtle)',
      }}>{ctaLabel}</button>
    </div>
  );
}

export default function LandingPage({ autoView }) {
  const { data: stats } = useApi('/public/stats');
  const { data: founding } = useApi('/public/founding-count');
  const [showAuth, setShowAuth] = useState(autoView === 'signup' || autoView === 'signin');
  const [authMode, setAuthMode] = useState(autoView === 'signin' ? 'login' : 'register');
  const [accountType, setAccountType] = useState(autoView === 'signup' ? (isNative ? 'free' : 'trial') : null);
  const [iapOffering, setIapOffering] = useState(null);

  useEffect(() => {
    if (!isIOS) return;
    let cancelled = false;
    (async () => {
      try {
        const o = await getOfferings();
        if (!cancelled) setIapOffering(o);
      } catch {
        // Offerings unavailable, fall back to placeholder prices
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const openRegister = () => {
    setAuthMode('register');
    setAccountType(isNative ? 'free' : 'trial');
    setShowAuth(true);
  };
  const openLogin = () => {
    setAuthMode('login');
    setShowAuth(true);
  };
  const openFreeRegister = () => {
    setAuthMode('register');
    setAccountType('free');
    setShowAuth(true);
  };

  const spotsLeft = founding ? (founding.remaining != null ? founding.remaining : Math.max(0, 50 - (founding.current || 0))) : null;

  const monthlyPrice = (isIOS && iapOffering?.monthly?.product?.priceString) || (isIOS ? null : '$29.99');
  const annualPrice = (isIOS && iapOffering?.annual?.product?.priceString) || (isIOS ? null : '$99');
  const showFoundingTier = !isIOS && spotsLeft !== null && spotsLeft > 0;

  const proofItems = [
    { v: stats?.record || '...', l: 'Record', g: false },
    { v: stats?.roi != null ? `${stats.roi >= 0 ? '+' : ''}${stats.roi}%` : '...', l: 'ROI', g: true },
    { v: stats?.units != null ? `${stats.units >= 0 ? '+' : ''}${stats.units}u` : '...', l: 'Units', g: true },
    { v: stats?.selectivity != null ? `${stats.selectivity}%` : '...', l: 'Selectivity', g: false },
  ];

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)', overflowX: 'hidden' }}>

      {/* ─── NAV ─── */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 50,
        background: 'rgba(10, 13, 20, 0.92)',
        backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        height: 56, display: 'flex', alignItems: 'center',
      }}>
        <div style={{
          ...sectionStyle, width: '100%',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <Wordmark size={15} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button onClick={openLogin} style={{
              fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '0.04em',
              padding: '8px 18px', borderRadius: 6,
              color: 'var(--text-secondary)', background: 'transparent',
              border: '1px solid var(--stroke-subtle)',
              cursor: 'pointer',
            }}>Sign In</button>
            <button onClick={openRegister} style={{
              fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '0.04em',
              padding: '8px 18px', borderRadius: 6,
              color: '#fff', background: GREEN, border: 'none',
              cursor: 'pointer',
            }}>{isNative ? 'Get Started' : 'Start Free Trial'}</button>
          </div>
        </div>
      </nav>

      {/* ─── HERO ─── */}
      <section style={{
        minHeight: '100vh',
        display: 'flex', flexDirection: 'column',
        justifyContent: 'center', alignItems: 'center',
        textAlign: 'center', padding: '100px 24px 60px',
        position: 'relative',
      }}>
        <div style={{
          position: 'absolute', inset: 0,
          background: 'radial-gradient(ellipse 700px 500px at 50% 35%, rgba(90,158,114,0.04), transparent), radial-gradient(ellipse 400px 300px at 70% 65%, rgba(90,158,114,0.02), transparent)',
          pointerEvents: 'none',
        }} />
        <div style={{ position: 'relative', maxWidth: 760 }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            letterSpacing: '0.16em', textTransform: 'uppercase',
            color: GREEN, marginBottom: 28,
          }}>Sports Market Intelligence</div>
          <h1 style={{
            fontFamily: 'var(--font-serif)', fontSize: 'clamp(36px, 7vw, 64px)',
            fontWeight: 500, lineHeight: 1.1,
            color: 'var(--text-primary)', marginBottom: 24,
          }}>
            One pick beats five.
          </h1>
          <p style={{
            fontFamily: 'var(--font-sans)', fontSize: 15, lineHeight: 1.75,
            color: 'var(--text-secondary)', maxWidth: 560,
            margin: '0 auto 12px',
          }}>
            Market intelligence across NBA, MLB, and WNBA. A four-model ensemble scans every game, detects
            pricing inefficiencies, and surfaces signals only when real edge appears. Most days, the answer
            is pass. That's the product.
          </p>
          <p style={{
            fontFamily: 'var(--font-serif)', fontStyle: 'italic',
            fontSize: 14, color: 'var(--text-tertiary)', marginBottom: 28,
          }}>
            Selective by design.
          </p>
          <div style={{
            display: 'flex', gap: 8, justifyContent: 'center',
            flexWrap: 'wrap', marginBottom: 36,
          }}>
            {[
              { label: 'NBA', on: true },
              { label: 'MLB', on: true },
              { label: 'WNBA  Coming Soon', on: false },
            ].map(p => (
              <span key={p.label} style={{
                fontFamily: 'var(--font-mono)', fontSize: 10,
                letterSpacing: '0.06em', padding: '5px 14px',
                borderRadius: 20, textTransform: 'uppercase',
                background: p.on ? GREEN_BG_12 : 'var(--surface-1)',
                color: p.on ? GREEN : 'var(--text-tertiary)',
                border: `1px solid ${p.on ? GREEN_BORDER : 'var(--stroke-subtle)'}`,
              }}>{p.label}</span>
            ))}
          </div>
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
          }}>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
              <button onClick={openRegister} style={{
                fontFamily: 'var(--font-mono)', fontSize: 13, letterSpacing: '0.04em',
                color: '#fff', background: GREEN, border: 'none',
                padding: '14px 36px', borderRadius: 8, cursor: 'pointer',
              }}>{isNative ? 'Get Started' : 'Start Free Trial'}</button>
              <button onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })} style={{
                fontFamily: 'var(--font-mono)', fontSize: 13, letterSpacing: '0.04em',
                color: 'var(--text-secondary)', background: 'transparent',
                border: '1px solid var(--stroke-subtle)',
                padding: '14px 28px', borderRadius: 8, cursor: 'pointer',
              }}>See How It Works</button>
            </div>
            {!isNative && (
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 10,
                color: 'var(--text-tertiary)', marginTop: 4,
              }}>$99/yr after trial. Cancel anytime.</div>
            )}
          </div>

          <div style={{
            display: 'flex', justifyContent: 'center', gap: 28,
            marginTop: 36, flexWrap: 'wrap',
          }}>
            {proofItems.map(p => (
              <div key={p.l} style={{ textAlign: 'center' }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 500,
                  color: p.g ? GREEN : 'var(--text-primary)',
                }}>{p.v}</div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 9,
                  letterSpacing: '0.10em', textTransform: 'uppercase',
                  color: 'var(--text-tertiary)', marginTop: 2,
                }}>{p.l}</div>
              </div>
            ))}
            {spotsLeft !== null && spotsLeft > 0 && !isIOS && (
              <div style={{ textAlign: 'center' }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 500,
                  color: 'var(--text-primary)',
                }}>{spotsLeft}</div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 9,
                  letterSpacing: '0.10em', textTransform: 'uppercase',
                  color: 'var(--text-tertiary)', marginTop: 2,
                }}>Founding Spots Left</div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ─── DISCIPLINE STRIP ─── */}
      <div style={{
        padding: '48px 24px',
        borderTop: '1px solid var(--stroke-subtle)',
        borderBottom: '1px solid var(--stroke-subtle)',
      }}>
        <div style={{
          maxWidth: 700, margin: '0 auto',
          display: 'flex', justifyContent: 'center', gap: 48,
          flexWrap: 'wrap',
        }}>
          {[
            { v: stats?.total_picks || '...', l: 'Games Analyzed', g: false },
            { v: stats?.total_picks || '...', l: 'Signals Generated', g: true },
            { v: stats?.total_passes || '...', l: 'Games Passed', g: false },
          ].map(s => (
            <div key={s.l} style={{ textAlign: 'center' }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 32, fontWeight: 500,
                color: s.g ? GREEN : 'var(--text-primary)',
              }}>{s.v}</div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 10,
                letterSpacing: '0.10em', textTransform: 'uppercase',
                color: 'var(--text-tertiary)', marginTop: 4,
              }}>{s.l}</div>
            </div>
          ))}
          <div style={{
            width: '100%', textAlign: 'center',
            fontFamily: 'var(--font-serif)', fontStyle: 'italic',
            fontSize: 13, color: 'var(--text-tertiary)', marginTop: 8,
          }}>If it's not sharp, it's not sent.</div>
        </div>
      </div>

      {/* ─── FEATURES ─── */}
      <section style={{ padding: '56px 0' }}>
        <div style={sectionStyle}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            letterSpacing: '0.16em', textTransform: 'uppercase',
            color: GREEN, marginBottom: 14,
          }}>What Sets Us Apart</div>
          <h2 style={{
            fontFamily: 'var(--font-serif)', fontSize: 'clamp(24px, 4vw, 38px)',
            fontWeight: 500, lineHeight: 1.2, marginBottom: 8,
            color: 'var(--text-primary)',
          }}>Six layers of intelligence.</h2>
          <p style={{
            fontFamily: 'var(--font-sans)', fontSize: 14,
            color: 'var(--text-tertiary)', marginBottom: 32,
          }}>Not a picks service. An intelligence platform.</p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 20,
          }}>
            <FeatureCard accent={GREEN}
              title="Daily market brief before you bet"
              body="MEI score, regime classification, top edge, signal density, and a market narrative. Line movement tracking shows which lines are moving toward or away from the model." />
            <FeatureCard accent={GREEN}
              title="Every game analyzed, signals and passes"
              body="The full market board with edge sorting. See which games qualified, which were passed, spread vs model line, moneyline, and the quant analysis behind each. Filter by upcoming, final, or passed." />
            <FeatureCard accent="rgba(90,158,114,0.6)"
              title="Track your bets. See your whole portfolio."
              body="Log wagers at actual stakes, track results, and see your total P/L with an equity curve over time. ROI, record, units, all calculated from your real bets." />
            <FeatureCard accent="rgba(90,158,114,0.6)"
              title="The bets you don't take are tracked too"
              body="Selectivity rate, picks followed vs passed, and a discipline grade. The only platform that measures restraint and compares you to the industry average." />
            <FeatureCard accent="rgba(90,158,114,0.35)"
              title="Sharp Journal, market notes and philosophy"
              body="Signal intelligence notes, market analysis, and discipline essays. Content designed to make you a sharper bettor by understanding when not to bet." />
            <FeatureCard accent="rgba(90,158,114,0.35)"
              title="Live tracking and a permanent public record"
              body="Watch your picks play out in real time. Every result graded against the closing line, published publicly, and permanently on record. Zero picks deleted." />
          </div>
        </div>
      </section>

      {/* ─── MID CTA ─── */}
      <div style={{
        textAlign: 'center', padding: '40px 24px',
        borderTop: '1px solid var(--stroke-subtle)',
        borderBottom: '1px solid var(--stroke-subtle)',
      }}>
        <p style={{
          fontFamily: 'var(--font-serif)', fontStyle: 'italic',
          fontSize: 16, color: 'var(--text-secondary)', marginBottom: 16,
        }}>See the model at work.</p>
        <button onClick={openRegister} style={{
          fontFamily: 'var(--font-mono)', fontSize: 12, letterSpacing: '0.04em',
          color: '#fff', background: GREEN, border: 'none',
          padding: '12px 32px', borderRadius: 8, cursor: 'pointer',
        }}>{isNative ? 'Get Started' : 'Start Free Trial'}</button>
      </div>

      {/* ─── HOW IT WORKS ─── */}
      <section id="how-it-works" style={{ padding: '56px 0' }}>
        <div style={sectionStyle}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            letterSpacing: '0.16em', textTransform: 'uppercase',
            color: GREEN, marginBottom: 14,
          }}>How SharpPicks Works</div>
          <h2 style={{
            fontFamily: 'var(--font-serif)', fontSize: 'clamp(24px, 4vw, 38px)',
            fontWeight: 500, lineHeight: 1.2, marginBottom: 8,
            color: 'var(--text-primary)',
          }}>From market scan to signal.</h2>
          <p style={{
            fontFamily: 'var(--font-sans)', fontSize: 14,
            color: 'var(--text-tertiary)', marginBottom: 32,
          }}>Three steps. One decision. Or none at all.</p>
          <div style={{
            display: 'flex', flexDirection: 'column',
            maxWidth: 600, gap: 28,
          }}>
            <Step num="1" title="Market Intelligence"
              body="SharpPicks scans every game across multiple sportsbooks to detect pricing discrepancies and measure market efficiency in real time." />
            <Step num="2" title="Quantitative Analysis"
              body="Each game is evaluated using four ML models, probability gaps, and market signals. 56 features per game, no narratives." />
            <Step num="3" title="Discipline Filter"
              body="Only positions with 3.5%+ edge survive. Most games are passed. No edge, no pick." />
          </div>
        </div>
      </section>

      {/* ─── SIGNAL CARD ─── */}
      <section style={{ padding: '56px 0' }}>
        <div style={sectionStyle}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            letterSpacing: '0.16em', textTransform: 'uppercase',
            color: GREEN, marginBottom: 14, textAlign: 'center',
          }}>The Model Shows Its Work</div>
          <h2 style={{
            fontFamily: 'var(--font-serif)', fontSize: 'clamp(24px, 4vw, 38px)',
            fontWeight: 500, lineHeight: 1.2, marginBottom: 8,
            color: 'var(--text-primary)', textAlign: 'center',
          }}>Full transparency on every signal.</h2>
          <p style={{
            fontFamily: 'var(--font-sans)', fontSize: 14,
            color: 'var(--text-tertiary)', marginBottom: 32, textAlign: 'center',
          }}>56 features. Four models. Full reasoning.</p>
          <SignalCardMock />
        </div>
      </section>

      {/* ─── BEHAVIORAL EDGE ─── */}
      <section style={{ padding: '56px 0' }}>
        <div style={sectionStyle}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            letterSpacing: '0.16em', textTransform: 'uppercase',
            color: GREEN, marginBottom: 14,
          }}>Your Results + Behavioral Edge</div>
          <h2 style={{
            fontFamily: 'var(--font-serif)', fontSize: 'clamp(24px, 4vw, 38px)',
            fontWeight: 500, lineHeight: 1.2, marginBottom: 8,
            color: 'var(--text-primary)',
          }}>Track your bets. Measure your discipline.</h2>
          <p style={{
            fontFamily: 'var(--font-sans)', fontSize: 15, lineHeight: 1.7,
            color: 'var(--text-secondary)', maxWidth: 600, marginBottom: 32,
          }}>Your portfolio, your equity curve, your discipline score, all in one view.</p>
          <BehavioralMock />
        </div>
      </section>

      {/* ─── PERFORMANCE STATS ─── */}
      <section style={{ padding: '56px 0' }}>
        <div style={sectionStyle}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            letterSpacing: '0.16em', textTransform: 'uppercase',
            color: GREEN, marginBottom: 14,
          }}>Live Tracking + Public Record</div>
          <h2 style={{
            fontFamily: 'var(--font-serif)', fontSize: 'clamp(24px, 4vw, 38px)',
            fontWeight: 500, lineHeight: 1.2, marginBottom: 8,
            color: 'var(--text-primary)',
          }}>Verified. Public. No exceptions.</h2>
          <p style={{
            fontFamily: 'var(--font-sans)', fontSize: 14,
            color: 'var(--text-tertiary)', marginBottom: 32,
          }}>Watch picks play out live. Every result graded against the closing line.</p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
            gap: 20, maxWidth: 600,
          }}>
            {[
              { v: stats?.total_picks ?? '...', l: 'Total Picks', sub: 'All time', hl: false, g: false },
              { v: stats?.selectivity != null ? `${stats.selectivity}%` : '...', l: 'Selectivity', sub: 'Signal rate', hl: false, g: true },
              { v: stats?.total_passes ?? '...', l: 'Total Passes', sub: 'Games skipped', hl: false, g: false },
              { v: '0', l: 'Picks Deleted', sub: 'Full transparency', hl: true, g: false },
            ].map(s => (
              <div key={s.l} style={{
                background: s.hl ? GREEN_BG_08 : 'var(--surface-1)',
                border: `1px solid ${s.hl ? GREEN_BORDER_30 : 'var(--stroke-subtle)'}`,
                borderRadius: 10, padding: '24px 20px', textAlign: 'center',
              }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700,
                  color: (s.g || s.hl) ? GREEN : 'var(--text-primary)', marginBottom: 4,
                }}>{s.v}</div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 9,
                  letterSpacing: '0.10em', textTransform: 'uppercase',
                  color: 'var(--text-tertiary)',
                }}>{s.l}</div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 9,
                  color: 'var(--text-tertiary)', marginTop: 2,
                }}>{s.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── PRICING ─── */}
      <section id="pricing" style={{ padding: '56px 0' }}>
        <div style={sectionStyle}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            letterSpacing: '0.16em', textTransform: 'uppercase',
            color: GREEN, marginBottom: 14, textAlign: 'center',
          }}>Pricing</div>
          <h2 style={{
            fontFamily: 'var(--font-serif)', fontSize: 'clamp(24px, 4vw, 38px)',
            fontWeight: 500, lineHeight: 1.2, marginBottom: 8,
            color: 'var(--text-primary)', textAlign: 'center',
          }}>Simple, transparent plans.</h2>
          <p style={{
            fontFamily: 'var(--font-sans)', fontSize: 14,
            color: 'var(--text-tertiary)', marginBottom: 32, textAlign: 'center',
          }}>14-day free trial on all paid plans. Cancel anytime.</p>

          <div style={{
            display: 'grid',
            gridTemplateColumns: showFoundingTier ? 'repeat(auto-fit, minmax(240px, 1fr))' : 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: 16, maxWidth: showFoundingTier ? 800 : 560, margin: '0 auto',
          }}>
            <PriceCard
              tier="Free"
              price="$0"
              sub="Forever"
              features={['See if a pick exists today', 'Public record access', 'Market overview']}
              ctaLabel="Sign Up Free"
              onCta={openFreeRegister}
              highlight={false}
            />
            <PriceCard
              tier="Monthly"
              price={monthlyPrice || '...'}
              sub={isIOS ? 'Cancel anytime' : 'Cancel anytime'}
              features={[
                'Daily market brief with MEI score',
                'Full pick details, edge %, side, line',
                'Full market board, signals + passes',
                'Bet tracking and portfolio P/L',
                'Discipline score and behavioral insights',
                'Sharp Journal, market notes',
                'Live tracking and real-time alerts',
              ]}
              ctaLabel="Start 14-Day Free Trial"
              onCta={openRegister}
              highlight={!showFoundingTier}
            />
            {showFoundingTier && (
              <PriceCard
                tier="Annual"
                badge="Founding Rate"
                price="$99"
                sub="$99/yr rate locked in. $149/yr once spots are claimed."
                features={[
                  'Everything in Monthly',
                  'Founding member badge (limited)',
                  'Locked-in rate for duration of subscription',
                  'Priority support',
                ]}
                ctaLabel="Claim Founding Spot"
                onCta={openRegister}
                highlight={true}
              />
            )}
            {!showFoundingTier && isIOS && (
              <PriceCard
                tier="Annual"
                price={annualPrice || '...'}
                sub="Best value. Cancel anytime."
                features={[
                  'Everything in Monthly',
                  'Locked-in rate for duration of subscription',
                  'Priority support',
                ]}
                ctaLabel="Start 14-Day Free Trial"
                onCta={openRegister}
                highlight={true}
              />
            )}
          </div>

          {showFoundingTier && (
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 11,
              color: 'var(--text-tertiary)', textAlign: 'center', marginTop: 20,
            }}>
              <span style={{ color: GREEN, fontWeight: 500 }}>{spotsLeft}</span> of 50 founding spots remaining
            </div>
          )}
          <p style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            color: 'var(--text-tertiary)', textAlign: 'center',
            maxWidth: 600, margin: '12px auto 0', lineHeight: 1.6,
          }}>
            All subscriptions include a 14-day free trial. Cancel anytime before trial ends and you won't be charged.
            {showFoundingTier ? ' Founding member rate locks in for the duration of an active, uninterrupted subscription.' : ''}
          </p>
        </div>
      </section>

      {/* ─── BOTTOM CTA ─── */}
      <section style={{
        textAlign: 'center', padding: '56px 24px',
        borderTop: '1px solid var(--stroke-subtle)',
      }}>
        <h2 style={{
          fontFamily: 'var(--font-serif)', fontSize: 'clamp(24px, 5vw, 36px)',
          fontWeight: 500, marginBottom: 8,
          color: 'var(--text-primary)',
        }}>Start scanning the market.</h2>
        <p style={{
          fontFamily: 'var(--font-sans)', fontSize: 14,
          color: 'var(--text-tertiary)', marginBottom: 28,
        }}>Create a free account and see the model at work. Upgrade anytime.</p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button onClick={openRegister} style={{
            fontFamily: 'var(--font-mono)', fontSize: 13, letterSpacing: '0.04em',
            color: '#fff', background: GREEN, border: 'none',
            padding: '14px 36px', borderRadius: 8, cursor: 'pointer',
          }}>{isNative ? 'Get Started' : 'Start Free Trial'}</button>
          <button onClick={openFreeRegister} style={{
            fontFamily: 'var(--font-mono)', fontSize: 13, letterSpacing: '0.04em',
            color: 'var(--text-secondary)', background: 'transparent',
            border: '1px solid var(--stroke-subtle)',
            padding: '14px 28px', borderRadius: 8, cursor: 'pointer',
          }}>Sign Up Free</button>
        </div>
      </section>

      {/* ─── FOOTER ─── */}
      <footer style={{
        borderTop: '1px solid var(--stroke-subtle)',
        padding: '48px 0 40px',
      }}>
        <div style={{ ...sectionStyle, textAlign: 'center' }}>
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
            marginBottom: 28,
          }}>
            {[
              'Beat the market, not the scoreboard.',
              'One pick beats five.',
              'No edge, no pick.',
            ].map(line => (
              <span key={line} style={{
                fontFamily: 'var(--font-serif)', fontSize: 14, fontWeight: 500,
                fontStyle: 'italic', color: 'var(--text-tertiary)',
              }}>{line}</span>
            ))}
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: 10, marginBottom: 20,
          }}>
            <Wordmark size={12} opacity={0.5} />
          </div>
          <p style={{
            fontFamily: 'var(--font-sans)', fontSize: 11,
            color: 'var(--text-tertiary)', marginBottom: 12, lineHeight: 1.6,
            maxWidth: 420, margin: '0 auto 12px',
          }}>
            SharpPicks provides sports analytics and model-based insights only. Not financial advice. Not a sportsbook.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginBottom: 12 }}>
            <a href="/privacy" style={{ fontSize: 11, color: 'var(--text-tertiary)', textDecoration: 'none' }}>Privacy</a>
            <a href="/terms" style={{ fontSize: 11, color: 'var(--text-tertiary)', textDecoration: 'none' }}>Terms</a>
            <a href="/disclaimer" style={{ fontSize: 11, color: 'var(--text-tertiary)', textDecoration: 'none' }}>Disclaimer</a>
          </div>
          <a href="mailto:support@sharppicks.ai" style={{
            fontFamily: 'var(--font-sans)', fontSize: 12,
            color: 'var(--text-secondary)', textDecoration: 'none',
          }}>support@sharppicks.ai</a>
        </div>
      </footer>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} initialMode={authMode} initialAccountType={accountType} />}
    </div>
  );
}

import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { Capacitor } from '@capacitor/core';
import AuthModal from './AuthModal';

const isNative = Capacitor.isNativePlatform();

/* ─── Shared Style Tokens ─── */
const SECTION_MAX = 1080;
const GRID_PAD = 'clamp(20px, 5vw, 64px)';

const sectionStyle = {
  maxWidth: SECTION_MAX,
  margin: '0 auto',
  padding: `0 ${GRID_PAD}`,
};

/* ─── Regime Pill (mock) ─── */
function RegimeBadge({ label = 'ACTIVE', color = '#FBBF24' }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700,
      letterSpacing: '0.1em', color,
    }}>
      <span style={{
        width: 7, height: 7, borderRadius: '50%',
        background: color, boxShadow: `0 0 8px ${color}55`,
      }} />
      {label}
    </span>
  );
}

/* ─── Mock Game Card ─── */
function MockGameCard() {
  return (
    <div style={{
      background: 'var(--surface-1)',
      border: '1px solid var(--stroke-subtle)',
      borderRadius: 10, overflow: 'hidden',
    }}>
      {/* Header row */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 72px 56px 64px',
        padding: '6px 14px 2px', gap: 6,
      }}>
        <div />
        {['Spread', 'Total', 'ML'].map(h => (
          <span key={h} style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', textAlign: 'center',
          }}>{h}</span>
        ))}
      </div>
      {/* Away */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 72px 56px 64px',
        padding: '5px 14px', alignItems: 'center', gap: 6,
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Dallas Mavericks
          </span>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>30-28</span>
        </div>
        <div style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>+13.5</div>
        <div style={{
          textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.82rem',
          color: 'var(--text-primary)', background: 'rgba(100,116,139,0.08)', borderRadius: 4, padding: '2px 0',
        }}>236.5</div>
        <div style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: '#FBBF24', fontWeight: 600 }}>+480</div>
      </div>
      <div style={{ height: 1, background: 'var(--stroke-subtle)', margin: '0 14px' }} />
      {/* Home */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 72px 56px 64px',
        padding: '5px 14px 8px', alignItems: 'center', gap: 6,
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Cleveland Cavaliers
          </span>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>48-9</span>
        </div>
        <div style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-primary)', fontWeight: 600 }}>-13.5</div>
        <div />
        <div style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'rgba(96,165,250,0.85)', fontWeight: 600 }}>-650</div>
      </div>
      {/* Edge strip */}
      <div style={{
        borderTop: '1px solid var(--stroke-subtle)',
        padding: '8px 14px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.72rem', fontWeight: 700,
            color: '#34D399', letterSpacing: '0.02em',
          }}>EDGE +8%</span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.58rem', fontWeight: 700,
            letterSpacing: '0.06em', color: 'var(--color-signal)',
            padding: '2px 6px', borderRadius: 3,
            background: 'var(--color-signal-bg)', border: '1px solid var(--color-signal-border)',
          }}>SIGNAL</span>
        </div>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 600,
          color: 'var(--text-tertiary)',
        }}>STRONG</span>
      </div>
    </div>
  );
}

/* ─── Quant Analysis Mock ─── */
function MockQuantCard() {
  const bullets = [
    'Rest advantage: Dallas off 2d rest vs Cleveland 1d (+1d advantage)',
    'Defensive mismatch: Cleveland allows 116.8 PPG (Bottom 8 NBA)',
    'Market movement: line opened -14, steamed to -13.5 — buying below market',
  ];
  return (
    <div style={{
      background: 'var(--surface-1)',
      border: '1px solid var(--stroke-subtle)',
      borderRadius: 10, padding: '16px 18px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
        letterSpacing: '0.1em', color: 'var(--text-tertiary)',
        marginBottom: 14, textTransform: 'uppercase',
      }}>Quant Analysis</div>

      {/* Edge bar */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 700, color: '#34D399' }}>+8%</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: '#34D399' }}>STRONG</span>
        </div>
        <div style={{ height: 5, borderRadius: 3, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
          <div style={{ width: '80%', height: '100%', borderRadius: 3, background: 'linear-gradient(90deg, #34D399, #5A9E72)' }} />
        </div>
      </div>

      {/* Probabilities */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--text-tertiary)', marginBottom: 3, textTransform: 'uppercase' }}>Cover Prob</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>71.6%</div>
        </div>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--text-tertiary)', marginBottom: 3, textTransform: 'uppercase' }}>Implied Prob</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700, color: 'var(--text-secondary)' }}>47.6%</div>
        </div>
      </div>

      {/* Reasoning */}
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
        letterSpacing: '0.08em', color: 'var(--text-tertiary)',
        marginBottom: 8, textTransform: 'uppercase',
      }}>Quant Reasoning</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {bullets.map((b, i) => (
          <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--color-signal)', flexShrink: 0, marginTop: 2 }}>▸</span>
            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{b}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Pillar Card ─── */
function PillarCard({ icon, title, description }) {
  return (
    <div style={{
      background: 'var(--surface-1)',
      border: '1px solid var(--stroke-subtle)',
      borderRadius: 12, padding: '28px 24px',
      flex: '1 1 280px', minWidth: 240,
    }}>
      <div style={{
        fontSize: 28, marginBottom: 16, lineHeight: 1,
        filter: 'grayscale(0.3)',
      }}>{icon}</div>
      <h3 style={{
        fontFamily: 'var(--font-serif)', fontSize: 18, fontWeight: 600,
        color: 'var(--text-primary)', marginBottom: 10,
      }}>{title}</h3>
      <p style={{
        fontFamily: 'var(--font-sans)', fontSize: 14, color: 'var(--text-secondary)',
        lineHeight: 1.65,
      }}>{description}</p>
    </div>
  );
}

/* ═══════════════════════════════════════
   LANDING PAGE
   ═══════════════════════════════════════ */
export default function LandingPage() {
  const { data: stats } = useApi('/public/stats');
  const { data: founding } = useApi('/public/founding-count');
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState('register');
  const [accountType, setAccountType] = useState(null);

  const openRegister = () => { setAuthMode('register'); setAccountType(isNative ? 'free' : 'trial'); setShowAuth(true); };
  const openLogin = () => { setAuthMode('login'); setShowAuth(true); };

  const spotsLeft = founding ? (founding.remaining != null ? founding.remaining : Math.max(0, 50 - (founding.current || 0))) : null;

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-primary)', overflowX: 'hidden' }}>

      {/* ─── NAV ─── */}
      <nav style={{
        position: 'sticky', top: 0, zIndex: 50,
        background: 'rgba(10, 13, 20, 0.85)',
        backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <div style={{
          ...sectionStyle, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          height: 56,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <img src="/images/crest.png" alt="" width={26} height={26} style={{ display: 'block', objectFit: 'contain' }} />
            <span style={{
              fontFamily: 'var(--font-sans)', fontSize: 13, fontWeight: 600,
              color: '#F2F4F8', letterSpacing: '3.9px', textTransform: 'uppercase', lineHeight: 1,
            }}>SHARP<span style={{ opacity: 0.5, margin: '0 0.4em', fontWeight: 500, letterSpacing: '0.18em' }}>||</span>PICKS</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button onClick={openLogin} style={{
              padding: '7px 16px', backgroundColor: 'transparent',
              color: 'var(--text-secondary)', border: '1px solid var(--stroke-muted)',
              borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer', fontFamily: 'var(--font-sans)',
            }}>Sign in</button>
            <button onClick={openRegister} style={{
              padding: '7px 18px', backgroundColor: 'var(--blue-primary)',
              color: '#fff', border: 'none', borderRadius: 8,
              fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'var(--font-sans)',
            }}>{isNative ? 'Get Started' : 'Start Free Trial'}</button>
          </div>
        </div>
      </nav>

      {/* ─── HERO ─── */}
      <section style={{
        position: 'relative', overflow: 'hidden',
        background: 'linear-gradient(180deg, #0E1A2B 0%, #0A0D14 100%)',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}>
        {/* Ghosted crest */}
        <div style={{
          position: 'absolute', top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 480, height: 480, opacity: 0.025, pointerEvents: 'none',
          backgroundImage: 'url(/images/crest.png)',
          backgroundSize: 'contain', backgroundRepeat: 'no-repeat', backgroundPosition: 'center',
        }} />

        <div className="landing-hero-grid" style={{
          ...sectionStyle,
          padding: `80px ${GRID_PAD} 80px`,
        }}>
          {/* Left — Copy */}
          <div>
            <h1 style={{
              fontFamily: 'var(--font-serif)', fontSize: 'clamp(32px, 4.5vw, 52px)',
              fontWeight: 700, lineHeight: 1.1,
              color: '#FFFFFF', marginBottom: 20,
            }}>
              Beat the market,<br />not the scoreboard.
            </h1>
            <p style={{
              fontFamily: 'var(--font-sans)', fontSize: 'clamp(15px, 1.4vw, 18px)',
              color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 10,
              maxWidth: 480,
            }}>
              SharpPicks analyzes sports betting markets like a trading desk — identifying pricing
              inefficiencies, measuring probability gaps, and generating signals only when real edges appear.
            </p>
            <p style={{
              fontFamily: 'var(--font-serif)', fontSize: 'clamp(14px, 1.2vw, 16px)',
              fontStyle: 'italic', color: 'var(--text-tertiary)', marginBottom: 36,
            }}>
              Selective by design.
            </p>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <button onClick={openRegister} style={{
                padding: '14px 32px', backgroundColor: 'var(--blue-primary)',
                color: '#fff', border: 'none', borderRadius: 10,
                fontSize: 15, fontWeight: 700, cursor: 'pointer',
                fontFamily: 'var(--font-sans)',
                boxShadow: '0 4px 24px rgba(79,125,243,0.30)',
                transition: 'transform 0.15s ease, box-shadow 0.15s ease',
              }}>
                View Today's Market
              </button>
              <button onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })} style={{
                padding: '14px 28px', backgroundColor: 'transparent',
                color: 'var(--text-secondary)', border: '1px solid var(--stroke-muted)',
                borderRadius: 10, fontSize: 15, fontWeight: 500, cursor: 'pointer',
                fontFamily: 'var(--font-sans)', transition: 'border-color 0.15s ease',
              }}>
                See How It Works
              </button>
            </div>
          </div>

          {/* Right — Mock UI */}
          <div style={{
            display: 'flex', flexDirection: 'column', gap: 14,
            position: 'relative',
          }}>
            {/* Regime header */}
            <div style={{
              background: 'var(--surface-1)', border: '1px solid rgba(251,191,36,0.25)',
              borderRadius: 10, padding: '16px 20px',
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
                letterSpacing: '0.12em', color: 'var(--text-tertiary)', marginBottom: 10,
                textTransform: 'uppercase',
              }}>Market Regime</div>
              <RegimeBadge />
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginTop: 14,
              }}>
                {[
                  { label: 'Analyzed', value: '8' },
                  { label: 'Edges', value: '4', color: '#FBBF24' },
                  { label: 'Signals', value: '3', color: '#34D399' },
                ].map(m => (
                  <div key={m.label} style={{ textAlign: 'center' }}>
                    <div style={{
                      fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 700,
                      color: m.color || 'var(--text-primary)',
                    }}>{m.value}</div>
                    <div style={{
                      fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600,
                      letterSpacing: '0.06em', color: 'var(--text-tertiary)', textTransform: 'uppercase',
                    }}>{m.label}</div>
                  </div>
                ))}
              </div>
            </div>
            <MockGameCard />
          </div>
        </div>
      </section>

      {/* ─── DISCIPLINE FILTER (Trust strip) ─── */}
      <section style={{
        borderBottom: '1px solid rgba(255,255,255,0.04)',
        background: 'var(--surface-0)',
        padding: '48px 0',
      }}>
        <div style={{ ...sectionStyle, textAlign: 'center' }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
            letterSpacing: '0.14em', color: 'var(--text-tertiary)',
            textTransform: 'uppercase', marginBottom: 24,
          }}>Discipline Filter</div>
          <div style={{
            display: 'flex', justifyContent: 'center', gap: 'clamp(24px, 5vw, 64px)',
            flexWrap: 'wrap', marginBottom: 20,
          }}>
            {[
              { value: '15', label: 'Games Analyzed' },
              { value: '3', label: 'Signals Generated', color: '#34D399' },
              { value: '12', label: 'Games Passed' },
            ].map(s => (
              <div key={s.label}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 'clamp(28px, 3vw, 40px)', fontWeight: 700,
                  color: s.color || 'var(--text-primary)',
                }}>{s.value}</div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600,
                  letterSpacing: '0.06em', color: 'var(--text-tertiary)', textTransform: 'uppercase',
                }}>{s.label}</div>
              </div>
            ))}
          </div>
          <p style={{
            fontFamily: 'var(--font-serif)', fontSize: 'clamp(16px, 1.5vw, 20px)',
            fontWeight: 500, fontStyle: 'italic',
            color: 'var(--text-secondary)',
          }}>
            One pick beats five.
          </p>
        </div>
      </section>

      {/* ─── HOW IT WORKS ─── */}
      <section id="how-it-works" style={{
        padding: '80px 0',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}>
        <div style={sectionStyle}>
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
              letterSpacing: '0.14em', color: 'var(--text-tertiary)',
              textTransform: 'uppercase', marginBottom: 12,
            }}>How SharpPicks Works</div>
            <h2 style={{
              fontFamily: 'var(--font-serif)', fontSize: 'clamp(24px, 3vw, 36px)',
              fontWeight: 700, color: 'var(--text-primary)',
            }}>
              From market scan to signal.
            </h2>
          </div>

          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
            <PillarCard
              icon="◎"
              title="Market Intelligence"
              description="SharpPicks scans every game across multiple sportsbooks to detect pricing discrepancies and measure market efficiency in real time."
            />
            <PillarCard
              icon="△"
              title="Quantitative Analysis"
              description="Each game is evaluated using statistical models, probability gaps, and market signals — 50+ features per game, no narratives."
            />
            <PillarCard
              icon="◇"
              title="Discipline Filter"
              description="Only the strongest edges become signals. Most games are passed. No edge, no pick."
            />
          </div>
        </div>
      </section>

      {/* ─── PRODUCT SCREENSHOT — Quant Analysis ─── */}
      <section style={{
        padding: '80px 0',
        background: 'linear-gradient(180deg, var(--bg-primary) 0%, #0E1220 50%, var(--bg-primary) 100%)',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}>
        <div className="landing-product-grid" style={sectionStyle}>
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
              letterSpacing: '0.14em', color: 'var(--text-tertiary)',
              textTransform: 'uppercase', marginBottom: 12,
            }}>Inside The Signal</div>
            <h2 style={{
              fontFamily: 'var(--font-serif)', fontSize: 'clamp(24px, 2.8vw, 34px)',
              fontWeight: 700, color: 'var(--text-primary)', marginBottom: 16,
            }}>
              Every signal shows its work.
            </h2>
            <p style={{
              fontFamily: 'var(--font-sans)', fontSize: 15, color: 'var(--text-secondary)',
              lineHeight: 1.7, marginBottom: 24, maxWidth: 440,
            }}>
              No black boxes. Each qualified signal surfaces the edge percentage,
              cover probability, implied probability gap, and the specific quantitative
              reasoning behind the pick.
            </p>
            <p style={{
              fontFamily: 'var(--font-serif)', fontSize: 15, fontStyle: 'italic',
              color: 'var(--text-tertiary)',
            }}>
              Transparency isn't a feature. It's the product.
            </p>
          </div>
          <MockQuantCard />
        </div>
      </section>

      {/* ─── SOCIAL PROOF / METRICS ─── */}
      <section style={{
        padding: '64px 0',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}>
        <div style={sectionStyle}>
          <div style={{ textAlign: 'center', marginBottom: 36 }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
              letterSpacing: '0.14em', color: 'var(--text-tertiary)',
              textTransform: 'uppercase', marginBottom: 12,
            }}>Model Performance</div>
            <h2 style={{
              fontFamily: 'var(--font-serif)', fontSize: 'clamp(22px, 2.5vw, 32px)',
              fontWeight: 700, color: 'var(--text-primary)',
            }}>
              The numbers are public.
            </h2>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 16,
          }}>
            {[
              { label: 'Total Picks', value: stats?.total_picks || '—', sub: 'All time' },
              { label: 'Selectivity', value: stats?.selectivity ? `${stats.selectivity}%` : '—', sub: 'Signal rate' },
              { label: 'Total Passes', value: stats?.total_passes || '—', sub: 'Games skipped' },
              { label: 'Picks Deleted', value: '0', sub: 'Full transparency' },
            ].map(m => (
              <div key={m.label} style={{
                background: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
                borderRadius: 10, padding: '24px 20px', textAlign: 'center',
              }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700,
                  color: 'var(--text-primary)', marginBottom: 4,
                }}>{m.value}</div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
                  letterSpacing: '0.08em', color: 'var(--text-tertiary)', textTransform: 'uppercase',
                  marginBottom: 2,
                }}>{m.label}</div>
                <div style={{
                  fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-tertiary)',
                }}>{m.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FOUNDING MEMBER (conditional) ─── */}
      {!isNative && spotsLeft !== null && spotsLeft > 0 && (
        <section style={{
          padding: '48px 0',
          borderBottom: '1px solid rgba(255,255,255,0.04)',
        }}>
          <div style={{ ...sectionStyle, textAlign: 'center' }}>
            <div style={{
              display: 'inline-block',
              background: 'rgba(79, 134, 247, 0.06)',
              border: '1px solid rgba(79, 134, 247, 0.15)',
              borderRadius: 14, padding: '28px 40px',
            }}>
              <div style={{
                fontFamily: 'var(--font-sans)', fontSize: 18, fontWeight: 700,
                color: 'var(--text-primary)', marginBottom: 8,
              }}>Founding Members</div>
              <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 6 }}>
                The first 50 members lock in the lowest rate permanently. Once it's gone, it's gone.
              </p>
              <p style={{
                fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600,
                color: 'var(--blue-primary)',
              }}>{spotsLeft} of 50 spots remaining</p>
            </div>
          </div>
        </section>
      )}

      {/* ─── CTA STRIP ─── */}
      <section style={{
        padding: '80px 0',
        background: 'linear-gradient(180deg, var(--bg-primary) 0%, #0E1A2B 100%)',
      }}>
        <div style={{ ...sectionStyle, textAlign: 'center' }}>
          <h2 style={{
            fontFamily: 'var(--font-serif)', fontSize: 'clamp(24px, 3vw, 36px)',
            fontWeight: 700, color: '#FFFFFF', marginBottom: 20,
          }}>
            Start scanning the market.
          </h2>
          <p style={{
            fontFamily: 'var(--font-sans)', fontSize: 16, color: 'var(--text-secondary)',
            marginBottom: 32, maxWidth: 440, margin: '0 auto 32px',
          }}>
            Create a free account and see the model at work. Upgrade anytime.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button onClick={openRegister} style={{
              padding: '14px 36px', backgroundColor: 'var(--blue-primary)',
              color: '#fff', border: 'none', borderRadius: 10,
              fontSize: 15, fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font-sans)',
              boxShadow: '0 4px 24px rgba(79,125,243,0.30)',
            }}>
              {isNative ? 'Get Started' : 'Start Free Trial'}
            </button>
            <button onClick={() => { setAuthMode('register'); setAccountType('free'); setShowAuth(true); }} style={{
              padding: '14px 28px', backgroundColor: 'transparent',
              color: 'var(--text-secondary)', border: '1px solid var(--stroke-muted)',
              borderRadius: 10, fontSize: 15, fontWeight: 500, cursor: 'pointer', fontFamily: 'var(--font-sans)',
            }}>
              {isNative ? 'Sign In' : 'Create Free Account'}
            </button>
          </div>
        </div>
      </section>

      {/* ─── FOOTER PHILOSOPHY ─── */}
      <footer style={{
        borderTop: '1px solid rgba(255,255,255,0.06)',
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

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginBottom: 20 }}>
            <img src="/images/crest.png" alt="" width={18} height={18} style={{ opacity: 0.4, objectFit: 'contain' }} />
            <span style={{
              fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 600,
              color: 'var(--text-tertiary)', letterSpacing: '2.5px', textTransform: 'uppercase',
            }}>SHARP<span style={{ opacity: 0.45, margin: '0 0.35em' }}>||</span>PICKS</span>
          </div>

          <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 12, lineHeight: 1.6, maxWidth: 420, margin: '0 auto 12px' }}>
            SharpPicks provides sports analytics and model-based insights only. Not financial advice. Not a sportsbook.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginBottom: 12 }}>
            <a href="/privacy" style={{ fontSize: 11, color: 'var(--text-tertiary)', textDecoration: 'none' }}>Privacy</a>
            <a href="/terms" style={{ fontSize: 11, color: 'var(--text-tertiary)', textDecoration: 'none' }}>Terms</a>
            <a href="/disclaimer" style={{ fontSize: 11, color: 'var(--text-tertiary)', textDecoration: 'none' }}>Disclaimer</a>
          </div>
          <a href="mailto:support@sharppicks.ai" style={{ fontSize: 12, color: 'var(--text-secondary)', textDecoration: 'none' }}>
            support@sharppicks.ai
          </a>
        </div>
      </footer>

      {/* ─── AUTH MODAL ─── */}
      {showAuth && <AuthModal onClose={() => setShowAuth(false)} initialMode={authMode} initialAccountType={accountType} />}
    </div>
  );
}

import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { Capacitor } from '@capacitor/core';
import AuthModal from './AuthModal';
import Wordmark from './Wordmark';

const isNative = Capacitor.isNativePlatform();

/* ─── Shared Style Tokens ─── */
const SECTION_MAX = 1080;
const GRID_PAD = 'clamp(20px, 5vw, 64px)';

const sectionStyle = {
  maxWidth: SECTION_MAX,
  margin: '0 auto',
  padding: `0 ${GRID_PAD}`,
};

/* ─── Phone Frame for screenshots ─── */
function PhoneFrame({ src, alt, maxWidth = 280 }) {
  return (
    <div style={{
      position: 'relative',
      width: '100%',
      maxWidth,
      margin: '0 auto',
      borderRadius: 28,
      overflow: 'hidden',
      border: '2px solid rgba(255,255,255,0.08)',
      boxShadow: '0 24px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.04)',
      background: '#0a1628',
    }}>
      <img
        src={src}
        alt={alt}
        loading="lazy"
        style={{ display: 'block', width: '100%', height: 'auto' }}
      />
    </div>
  );
}

 

/* ─── Quant Analysis Mock ─── */
 

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
export default function LandingPage({ autoView }) {
  const { data: stats } = useApi('/public/stats');
  const { data: founding } = useApi('/public/founding-count');
  const [showAuth, setShowAuth] = useState(autoView === 'signup' || autoView === 'signin');
  const [authMode, setAuthMode] = useState(autoView === 'signin' ? 'login' : 'register');
  const [accountType, setAccountType] = useState(autoView === 'signup' ? (isNative ? 'free' : 'trial') : null);

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
          <Wordmark size={15} />
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
            }}>{isNative ? 'Get Started' : 'Start 14-Day Trial'}</button>
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
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700,
              letterSpacing: '0.16em', textTransform: 'uppercase',
              color: 'var(--text-tertiary)', marginBottom: 16,
            }}>Sports Market Intelligence</div>
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
              SharpPicks analyzes sports betting markets like a trading desk, identifying pricing
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

          {/* Right — App Screenshot */}
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <PhoneFrame src="/images/screenshot-signal-detail.png" alt="SharpPicks Signal Detail" maxWidth={300} />
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
              description="Each game is evaluated using statistical models, probability gaps, and market signals. 50+ features per game, no narratives."
            />
            <PillarCard
              icon="◇"
              title="Discipline Filter"
              description="Only the strongest edges become signals. Most games are passed. No edge, no pick."
            />
          </div>
        </div>
      </section>

      {/* ─── PRODUCT SCREENSHOTS ─── */}
      <section style={{
        padding: '80px 0',
        background: 'linear-gradient(180deg, var(--bg-primary) 0%, #0E1220 50%, var(--bg-primary) 100%)',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}>
        <div style={sectionStyle}>
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
              letterSpacing: '0.14em', color: 'var(--text-tertiary)',
              textTransform: 'uppercase', marginBottom: 12,
            }}>Inside The App</div>
            <h2 style={{
              fontFamily: 'var(--font-serif)', fontSize: 'clamp(24px, 2.8vw, 34px)',
              fontWeight: 700, color: 'var(--text-primary)', marginBottom: 16,
            }}>
              Every signal shows its work.
            </h2>
            <p style={{
              fontFamily: 'var(--font-sans)', fontSize: 16, color: 'var(--text-secondary)',
              lineHeight: 1.7, maxWidth: 520, margin: '0 auto',
            }}>
              No black boxes. Each qualified signal surfaces the edge percentage,
              cover probability, implied probability gap, and the specific quantitative
              reasoning behind the pick.
            </p>
          </div>

          <div className="landing-screenshots-row" style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 24,
            alignItems: 'center',
          }}>
            <div style={{ textAlign: 'center' }}>
              <PhoneFrame src="/images/screenshot-signal-detail.png" alt="Signal detail with full analysis" maxWidth={240} />
              <p style={{
                fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
                letterSpacing: '0.1em', color: 'var(--text-tertiary)',
                textTransform: 'uppercase', marginTop: 16,
              }}>Signal Detail</p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <PhoneFrame src="/images/screenshot-market.png" alt="Market Intelligence dashboard" maxWidth={240} />
              <p style={{
                fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
                letterSpacing: '0.1em', color: 'var(--text-tertiary)',
                textTransform: 'uppercase', marginTop: 16,
              }}>Market Intelligence</p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <PhoneFrame src="/images/screenshot-market-games.png" alt="Market board with game odds" maxWidth={240} />
              <p style={{
                fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
                letterSpacing: '0.1em', color: 'var(--text-tertiary)',
                textTransform: 'uppercase', marginTop: 16,
              }}>Market Board</p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <PhoneFrame src="/images/screenshot-results.png" alt="Results and performance tracking" maxWidth={240} />
              <p style={{
                fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
                letterSpacing: '0.1em', color: 'var(--text-tertiary)',
                textTransform: 'uppercase', marginTop: 16,
              }}>Results Tracker</p>
            </div>
          </div>
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
              {isNative ? 'Get Started' : 'Start 14-Day Trial'}
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
            <img src="/images/crest.png" alt="" width={16} height={16} style={{ opacity: 0.4, objectFit: 'contain', borderRadius: 3 }} />
            <Wordmark size={12} opacity={0.5} />
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

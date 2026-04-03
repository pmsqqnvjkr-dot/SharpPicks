import { useState, useRef } from 'react';

const brandGreen = '#5A9E72';
const bg = '#0A0D14';
const s1 = '#111e33';
const bd = '#1e3050';
const t1 = '#e8ecf0';
const t2 = '#8a9bb0';
const t3 = '#4a5a6e';
const mono = "'JetBrains Mono','SF Mono','Menlo','Consolas','Courier New',monospace";
const serif = "'Georgia','Times New Roman',serif";
const sans = "'Inter','SF Pro Display','Helvetica Neue','Arial',sans-serif";

function BrandMark({ size = 44 }) {
  const bar = size * 0.6;
  const w = size * 0.12;
  const gap = size * 0.28;
  const accent = size * 0.4;
  return (
    <svg width={size} height={size} viewBox="0 0 500 500">
      <rect x="150" y="100" width="60" height="300" rx="30" fill={t1} />
      <rect x="290" y="100" width="60" height="300" rx="30" fill={t1} />
      <rect x="150" y="420" width="200" height="20" rx="10" fill={brandGreen} />
    </svg>
  );
}

function PassDayMini() {
  return (
    <div style={{
      background: s1, border: `0.5px solid ${bd}`, borderRadius: '8px',
      padding: '10px 12px', margin: '12px 0',
    }}>
      <div style={{
        fontFamily: mono, fontSize: '9px', color: t2,
        letterSpacing: '1px', fontWeight: 600, textAlign: 'center', marginBottom: '6px',
      }}>NO QUALIFYING EDGE</div>
      <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center', padding: '4px 0' }}>
        {[['9', 'GAMES'], ['3', 'EDGES'], ['0', 'SIGNALS'], ['2.8%', 'TOP EDGE']].map(([v, l]) => (
          <div key={l}>
            <div style={{ fontFamily: mono, fontSize: '12px', fontWeight: 700, color: t1 }}>{v}</div>
            <div style={{ fontFamily: mono, fontSize: '7px', letterSpacing: '1px', color: t3, marginTop: '2px' }}>{l}</div>
          </div>
        ))}
      </div>
      <div style={{
        fontFamily: serif, fontStyle: 'italic', fontSize: '10px',
        color: t3, textAlign: 'center', marginTop: '6px',
      }}>Selective by design.</div>
    </div>
  );
}

const SCREENS = [
  {
    label: 'HOW SHARPPICKS WORKS',
    headline: 'Sports markets analyzed like financial markets.',
    body: (
      <>
        <p>SharpPicks scans every game, every day. It calculates edges, classifies market regimes, and publishes a signal only when the model finds a real pricing inefficiency.</p>
        <p>Most days, there is no signal. That is the product working.</p>
      </>
    ),
    footer: 'One pick beats five.',
    cta: 'CONTINUE',
    filled: false,
  },
  {
    label: 'DAILY INTELLIGENCE',
    headline: 'Every day you get the full picture.',
    body: (
      <>
        <p>Full game slate with every edge calculated. Daily Market Brief with regime analysis and efficiency scoring. The reasoning why each game did or did not clear the threshold.</p>
        <PassDayMini />
        <p style={{ fontSize: '11px', color: t3 }}>A pass day is not an empty screen. It is a complete market intelligence report.</p>
      </>
    ),
    cta: 'CONTINUE',
    filled: false,
  },
  {
    label: 'FULL TRANSPARENCY',
    headline: 'Your full record. No edits. No deletions.',
    body: (
      <>
        <p>Log any bet. See your equity curve, discipline score, and selectivity rate vs. the industry average. Every signal is tracked with CLV against the closing line.</p>
        <p>SharpPicks measures what you bet, what you skip, and what that restraint is worth.</p>
      </>
    ),
    footer: 'Append-only. No cherry-picking. No hiding losses.',
    cta: 'CONTINUE',
    filled: false,
  },
  {
    label: 'WHY SHARPPICKS EXISTS',
    headline: null,
    body: (
      <>
        <div style={{
          borderLeft: `2px solid ${brandGreen}`, padding: '10px 14px',
          margin: '8px 0 14px', background: 'rgba(90,158,114,0.12)',
          borderRadius: '0 6px 6px 0',
        }}>
          <p style={{
            fontFamily: serif, fontStyle: 'italic', fontSize: '13px',
            color: t1, lineHeight: 1.55, margin: 0,
          }}>"We built SharpPicks because every betting product we found rewarded action. More picks, more bets, more engagement. The result was always the same: a slow bleed disguised as entertainment."</p>
        </div>
        <p>SharpPicks is built on a different assumption: that the best bet is often no bet at all. That restraint is a competitive advantage. That a market analyzed with discipline will outperform one traded on instinct.</p>
        <div style={{ marginTop: '12px' }}>
          <div style={{ fontSize: '11px', color: t2 }}>Evan Cole</div>
          <div style={{
            fontFamily: mono, fontSize: '8px', letterSpacing: '1.5px',
            color: t3, marginTop: '2px',
          }}>HEAD OF SIGNAL INTELLIGENCE</div>
        </div>
      </>
    ),
    cta: 'ENTER SHARPPICKS',
    filled: true,
  },
];

export default function OnboardingFlow({ onComplete }) {
  const [step, setStep] = useState(0);
  const touchStartX = useRef(null);

  const handleNext = () => {
    if (step < SCREENS.length - 1) setStep(step + 1);
    else onComplete();
  };

  const handleTouchStart = (e) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e) => {
    if (touchStartX.current === null) return;
    const diff = touchStartX.current - e.changedTouches[0].clientX;
    if (diff > 60 && step < SCREENS.length - 1) setStep(step + 1);
    if (diff < -60 && step > 0) setStep(step - 1);
    touchStartX.current = null;
  };

  const screen = SCREENS[step];

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      backgroundColor: bg, color: t1,
      display: 'flex', flexDirection: 'column',
      fontFamily: sans,
      overflowY: 'auto', WebkitOverflowScrolling: 'touch',
    }}>
      <div
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          padding: '60px 28px 32px',
          maxWidth: '420px', width: '100%', margin: '0 auto',
        }}
      >
        {/* Progress bar */}
        <div style={{ display: 'flex', gap: '5px', marginBottom: '24px' }}>
          {SCREENS.map((_, i) => (
            <div key={i} style={{
              height: '2px', flex: 1, borderRadius: '1px',
              backgroundColor: i <= step ? brandGreen : bd,
              transition: 'background-color 0.3s',
            }} />
          ))}
        </div>

        {/* Skip */}
        <div style={{
          fontSize: '11px', color: t3, textAlign: 'right',
          marginBottom: '20px', letterSpacing: '0.5px', cursor: 'pointer',
        }} onClick={onComplete}>Skip</div>

        {/* Brand mark */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px' }}>
          <BrandMark size={step === 0 ? 52 : 40} />
        </div>

        {/* Label */}
        <div style={{
          fontFamily: mono, fontSize: '9px', letterSpacing: '2.5px',
          color: brandGreen, fontWeight: 600, marginBottom: '12px', textAlign: 'center',
        }}>{screen.label}</div>

        {/* Headline */}
        {screen.headline && (
          <h1 style={{
            fontFamily: serif, fontSize: '20px', fontWeight: 700,
            lineHeight: 1.3, marginBottom: '14px', textAlign: 'center',
            margin: '0 0 14px',
          }}>{screen.headline}</h1>
        )}

        {/* Body */}
        <div style={{
          fontSize: '12.5px', color: t2, lineHeight: 1.65,
        }}>
          {typeof screen.body === 'string' ? <p style={{ margin: '0 0 10px' }}>{screen.body}</p> : screen.body}
        </div>

        {/* Footer quote */}
        {screen.footer && (
          <div style={{
            fontFamily: serif, fontStyle: 'italic', fontSize: '12px',
            color: t3, lineHeight: 1.5, textAlign: 'center',
            marginTop: 'auto', paddingTop: '12px',
            borderTop: `1px solid ${bd}`,
          }}>{screen.footer}</div>
        )}

        {/* Spacer */}
        <div style={{ flex: 1, minHeight: '14px' }} />

        {/* CTA Button */}
        <button
          onClick={handleNext}
          style={{
            display: 'block', width: '100%', padding: '12px',
            border: screen.filled ? 'none' : `1.5px solid ${brandGreen}`,
            background: screen.filled ? brandGreen : 'transparent',
            color: screen.filled ? bg : brandGreen,
            fontFamily: mono, fontSize: '11px', fontWeight: 600,
            letterSpacing: '1px', borderRadius: '8px',
            cursor: 'pointer', textAlign: 'center',
          }}
        >{screen.cta}</button>
      </div>
    </div>
  );
}

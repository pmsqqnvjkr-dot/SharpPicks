import Wordmark from './Wordmark';

const TRUST_STACK = [
  {
    label: 'Market Regime',
    detail: 'Daily market conditions classified',
    color: 'rgba(79,134,247,0.7)',
    bg: 'rgba(79,134,247,0.06)',
    border: 'rgba(79,134,247,0.15)',
  },
  {
    label: 'Edges Detected',
    detail: 'Every game scanned for inefficiency',
    color: 'rgba(251,191,36,0.8)',
    bg: 'rgba(251,191,36,0.06)',
    border: 'rgba(251,191,36,0.15)',
  },
  {
    label: 'Qualified Signals',
    detail: 'Only statistically significant edges pass',
    color: 'rgba(90,158,114,0.8)',
    bg: 'rgba(90,158,114,0.06)',
    border: 'rgba(90,158,114,0.15)',
  },
  {
    label: 'Quant Reasoning',
    detail: 'Full model logic transparent to you',
    color: 'rgba(255,255,255,0.5)',
    bg: 'rgba(255,255,255,0.02)',
    border: 'rgba(255,255,255,0.08)',
  },
  {
    label: 'CLV Performance',
    detail: 'Did the model beat the closing line?',
    color: '#5A9E72',
    bg: 'rgba(90,158,114,0.08)',
    border: 'rgba(90,158,114,0.22)',
    isFinal: true,
  },
];

export default function OnboardingFlow({ onComplete }) {
  return (
    <div style={{
      position: 'fixed', inset: 0,
      backgroundColor: '#0A0D14',
      zIndex: 1000,
      display: 'flex', flexDirection: 'column',
      maxWidth: '480px', margin: '0 auto',
      overflow: 'auto', WebkitOverflowScrolling: 'touch',
    }}>
      <div style={{
        paddingTop: 'max(env(safe-area-inset-top, 16px), 16px)',
      }} />

      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column',
        alignItems: 'center',
        padding: '0 28px',
      }}>

        <img
          src="/images/crest.png"
          alt="SharpPicks"
          style={{
            width: '64px', height: '64px',
            objectFit: 'contain',
            opacity: 0.07,
            marginBottom: '12px', marginTop: '8px',
            borderRadius: 12,
          }}
        />

        <div style={{
          fontFamily: 'var(--font-sans)', fontSize: '13px', fontWeight: 700,
          letterSpacing: '0.2em', textTransform: 'uppercase',
          color: 'rgba(255,255,255,0.45)',
          marginBottom: '20px',
        }}>
          <Wordmark size={13} opacity={0.45} />
        </div>

        <h1 style={{
          fontFamily: 'var(--font-serif)', fontSize: '26px', fontWeight: 700,
          color: '#FFFFFF', lineHeight: 1.15,
          textAlign: 'center',
          maxWidth: '280px',
          margin: '0 auto 8px',
        }}>
          Sports markets analyzed like financial markets
        </h1>

        <p style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '14px', color: 'rgba(255,255,255,0.45)', lineHeight: 1.5,
          textAlign: 'center', maxWidth: '260px', margin: '0 auto 24px',
        }}>
          One signal per day. Only when the edge is real.
        </p>

        {/* ── Model Trust Stack ── */}
        <div style={{
          width: '100%', maxWidth: '320px',
          marginBottom: '20px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
            letterSpacing: '0.12em', textTransform: 'uppercase',
            color: 'rgba(255,255,255,0.3)',
            textAlign: 'center', marginBottom: '12px',
          }}>Model Trust Stack</div>

          {TRUST_STACK.map((step, i) => (
            <div key={step.label}>
              <div style={{
                padding: '10px 14px',
                borderRadius: '8px',
                border: `1px solid ${step.border}`,
                background: step.bg,
                display: 'flex', alignItems: 'center', gap: '10px',
              }}>
                <div style={{
                  width: '22px', height: '22px', borderRadius: '6px',
                  background: step.isFinal
                    ? 'linear-gradient(135deg, rgba(90,158,114,0.3), rgba(90,158,114,0.1))'
                    : 'rgba(255,255,255,0.03)',
                  border: `1px solid ${step.border}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
                    color: step.color,
                  }}>{i + 1}</span>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700,
                    letterSpacing: '0.06em', textTransform: 'uppercase',
                    color: step.color,
                    lineHeight: 1.2,
                  }}>{step.label}</div>
                  <div style={{
                    fontFamily: 'var(--font-sans)', fontSize: '11px',
                    color: 'rgba(255,255,255,0.3)', lineHeight: 1.3,
                    marginTop: '1px',
                  }}>{step.detail}</div>
                </div>
                {step.isFinal && (
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
                    letterSpacing: '0.04em', textTransform: 'uppercase',
                    color: '#5A9E72',
                    padding: '2px 6px', borderRadius: 3,
                    background: 'rgba(90,158,114,0.12)',
                    border: '1px solid rgba(90,158,114,0.25)',
                    flexShrink: 0,
                  }}>Proof</span>
                )}
              </div>
              {i < TRUST_STACK.length - 1 && (
                <div style={{
                  display: 'flex', justifyContent: 'center', padding: '3px 0',
                }}>
                  <div style={{ width: '1px', height: '10px', background: 'rgba(255,255,255,0.08)' }} />
                </div>
              )}
            </div>
          ))}
        </div>

        <p style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '13px', fontWeight: 500,
          fontStyle: 'italic', color: 'rgba(255,255,255,0.5)', lineHeight: 1.6,
          textAlign: 'center', margin: '0 0 16px',
        }}>
          Discipline is the product.<br />
          Selective by design.
        </p>
      </div>

      {/* ── CTA ── */}
      <div style={{
        padding: '16px 32px',
        paddingBottom: 'max(40px, calc(env(safe-area-inset-bottom, 0px) + 40px))',
      }}>
        <button
          onClick={onComplete}
          onPointerDown={e => { e.currentTarget.style.opacity = '0.85'; }}
          onPointerUp={e => { e.currentTarget.style.opacity = '1'; }}
          onPointerLeave={e => { e.currentTarget.style.opacity = '1'; }}
          style={{
            width: '100%', maxWidth: '280px', height: '52px',
            display: 'block', margin: '0 auto',
            background: 'var(--blue-primary)',
            border: 'none', borderRadius: '14px',
            color: '#FFFFFF', fontSize: '16px', fontWeight: 700,
            fontFamily: 'var(--font-sans)',
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
        >
          Enter SharpPicks
        </button>
      </div>
    </div>
  );
}

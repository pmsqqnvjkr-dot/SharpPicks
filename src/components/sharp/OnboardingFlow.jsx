import { useState } from 'react';

export default function OnboardingFlow({ onComplete }) {
  const [step, setStep] = useState(0);

  const steps = [
    {
      title: 'One pick. Maximum.',
      description: 'Sharp Picks publishes at most one pick per day. Only when the model detects a statistical edge above threshold. Most days, there is no pick.',
      detail: 'This is not a limitation — it is the product.',
      icon: (
        <svg viewBox="0 0 40 40" width="48" height="48" fill="none">
          <path d="M20 2L4 9v12c0 10 6.5 18.5 16 21 9.5-2.5 16-11 16-21V9L20 2z" stroke="white" strokeWidth="3" fill="none"/>
          <rect x="14" y="16" width="3" height="12" rx="1" fill="white"/>
          <rect x="19" y="12" width="3" height="16" rx="1" fill="white"/>
          <rect x="24" y="18" width="3" height="10" rx="1" fill="white"/>
          <path d="M12 20L20 10L30 6" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
          <path d="M27 5l4 1-1 4" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
        </svg>
      ),
    },
    {
      title: 'Most days look like this.',
      description: 'At ~28% selectivity, the majority of days are pass days. This is the screen you\'ll see most often. It means the model found no qualifying edge — and that\'s the system working exactly as designed.',
      detail: 'If your first few days are all passes, the app isn\'t broken. It\'s protecting your bankroll.',
      icon: (
        <svg viewBox="0 0 24 24" width="48" height="48" stroke="white" fill="none" strokeWidth="2" strokeLinecap="round">
          <rect x="6" y="5" width="4" height="14" rx="1" />
          <rect x="14" y="5" width="4" height="14" rx="1" />
        </svg>
      ),
      hasPreview: true,
    },
    {
      title: 'Track everything. Question nothing.',
      description: 'Every pick and every pass is logged with full transparency. Our public record cannot be edited or deleted. You see exactly what we see.',
      detail: 'Append-only. No cherry-picking. No hiding losses.',
      icon: (
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 3v18h18"/>
          <path d="M7 17l4-4 4 4 6-6"/>
        </svg>
      ),
    },
    {
      title: 'A note from the founder',
      isFounderNote: true,
    },
  ];

  const current = steps[step];
  const isLast = step === steps.length - 1;

  return (
    <div style={{
      position: 'fixed', inset: '0',
      backgroundColor: 'var(--bg-primary)',
      zIndex: 1000, display: 'flex', flexDirection: 'column',
      maxWidth: '480px', margin: '0 auto',
    }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        padding: '16px 20px', alignItems: 'center',
      }}>
        <div style={{ display: 'flex', gap: '6px' }}>
          {steps.map((_, i) => (
            <div key={i} style={{
              width: i === step ? '24px' : '8px', height: '4px',
              borderRadius: '2px',
              backgroundColor: i === step ? 'var(--blue-primary)' : 'var(--surface-2)',
              transition: 'all 0.3s ease',
            }} />
          ))}
        </div>
        <button onClick={onComplete} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          fontFamily: 'var(--font-sans)', fontSize: '13px',
          color: 'var(--text-tertiary)', fontWeight: 500,
        }}>Skip</button>
      </div>

      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column',
        justifyContent: 'center', padding: '0 32px',
      }}>
        {current.isFounderNote ? (
          <FounderNote />
        ) : (
          <>
            <div style={{ marginBottom: '32px', opacity: 0.8 }}>
              {current.icon}
            </div>
            <h1 style={{
              fontFamily: 'var(--font-serif)', fontSize: '28px', fontWeight: 600,
              color: 'var(--text-primary)', lineHeight: '1.2', marginBottom: '16px',
            }}>{current.title}</h1>
            <p style={{
              fontSize: '16px', color: 'var(--text-secondary)', lineHeight: '1.7',
              marginBottom: '20px',
            }}>{current.description}</p>
            {current.hasPreview && <PassDayPreview />}
            <p style={{
              fontFamily: 'var(--font-mono)', fontSize: '12px',
              color: 'var(--text-tertiary)', letterSpacing: '0.02em',
              lineHeight: '1.6',
            }}>{current.detail}</p>
          </>
        )}
      </div>

      <div style={{ padding: '20px 32px 40px' }}>
        <button onClick={() => {
          if (isLast) {
            onComplete();
          } else {
            setStep(s => s + 1);
          }
        }} style={{
          width: '100%', padding: '16px',
          background: 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))',
          border: 'none', borderRadius: '14px',
          color: '#fff', fontSize: '15px', fontWeight: 700,
          cursor: 'pointer', fontFamily: 'var(--font-sans)',
        }}>
          {isLast ? 'Enter Sharp Picks' : 'Continue'}
        </button>
      </div>
    </div>
  );
}

function PassDayPreview() {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      border: '1px solid var(--stroke-subtle)',
      padding: '20px',
      marginBottom: '20px',
      opacity: 0.85,
      transform: 'scale(0.92)',
    }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{
          width: '48px', height: '48px', borderRadius: '14px',
          backgroundColor: 'var(--surface-2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 12px',
        }}>
          <svg viewBox="0 0 24 24" width="24" height="24" stroke="var(--text-tertiary)" fill="none" strokeWidth="2" strokeLinecap="round">
            <rect x="6" y="5" width="4" height="14" rx="1" />
            <rect x="14" y="5" width="4" height="14" rx="1" />
          </svg>
        </div>
        <div style={{
          fontFamily: 'var(--font-serif)', fontSize: '16px', fontWeight: 600,
          color: 'var(--text-primary)', marginBottom: '6px',
        }}>No qualifying pick</div>
        <div style={{
          fontSize: '12px', color: 'var(--text-tertiary)', lineHeight: '1.5',
        }}>Model analyzed 8 games. No edge above threshold.</div>
      </div>
    </div>
  );
}

function FounderNote() {
  return (
    <div>
      <div style={{
        width: '56px', height: '56px', borderRadius: '50%',
        backgroundColor: 'var(--surface-2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: '24px',
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5">
          <circle cx="12" cy="8" r="4"/>
          <path d="M4 20c0-4 4-7 8-7s8 3 8 7"/>
        </svg>
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
        letterSpacing: '2px', textTransform: 'uppercase',
        color: 'var(--text-tertiary)', marginBottom: '16px',
      }}>A note from the founder</div>
      <div style={{
        fontFamily: 'var(--font-serif)', fontSize: '18px', fontStyle: 'italic',
        color: 'var(--text-primary)', lineHeight: '1.6', marginBottom: '20px',
      }}>
        "I built Sharp Picks because I lost money the same way everyone does — too many bets, not enough discipline."
      </div>
      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.7',
        marginBottom: '12px',
      }}>
        Every betting product I used rewarded action. More picks, more bets, more engagement. The result was always the same: a slow bleed disguised as entertainment.
      </p>
      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.7',
        marginBottom: '12px',
      }}>
        Sharp Picks is built on a different assumption — that the best bet is often no bet at all. That restraint is a competitive advantage.
      </p>
      <p style={{
        fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.7',
        marginBottom: '20px',
      }}>
        This app will be quiet most days. That's not a bug. That's the entire point.
      </p>
      <div style={{
        fontFamily: 'var(--font-serif)', fontSize: '14px', fontStyle: 'italic',
        color: 'var(--text-tertiary)',
      }}>— Evan Cole, Founder</div>
    </div>
  );
}

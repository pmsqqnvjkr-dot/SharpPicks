import { useState, useRef } from 'react';

const SCREENS = [
  {
    headline: 'Welcome to SharpPicks',
    body: 'Model-driven signals across NBA and MLB. Only when a real edge appears.',
    icon: (
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
        <rect x="4" y="4" width="40" height="40" rx="12" stroke="#5A9E72" strokeWidth="2" />
        <path d="M16 24l6 6 10-12" stroke="#5A9E72" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    cta: 'Get Started',
  },
  {
    headline: 'How Signals Work',
    body: 'The model analyzes every game. When it finds a pricing mistake above our 3.5% edge threshold, it generates a signal. Most days, it passes.',
    icon: (
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
        <path d="M8 8h32v8H28v24h-8V16H8V8z" fill="none" stroke="#4F86F7" strokeWidth="2" />
        <path d="M24 20v16" stroke="#4F86F7" strokeWidth="2" strokeLinecap="round" />
        <path d="M16 28l8-8 8 8" stroke="#4F86F7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <rect x="10" y="36" width="28" height="4" rx="2" fill="rgba(79,134,247,0.15)" />
      </svg>
    ),
    cta: 'Next',
  },
  {
    headline: 'Your Dashboard',
    body: 'Signals shows today\'s picks. Results tracks your performance. Insights has articles on process and discipline.',
    icon: (
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
        <rect x="6" y="12" width="10" height="24" rx="3" stroke="#5A9E72" strokeWidth="2" />
        <rect x="19" y="8" width="10" height="28" rx="3" stroke="#4F86F7" strokeWidth="2" />
        <rect x="32" y="16" width="10" height="20" rx="3" stroke="rgba(255,255,255,0.3)" strokeWidth="2" />
      </svg>
    ),
    cta: 'Start Exploring',
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
    <div
      onClick={(e) => { if (e.target === e.currentTarget) onComplete(); }}
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        backgroundColor: 'rgba(0,0,0,0.75)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '24px',
      }}
    >
      <div
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        style={{
          width: '100%', maxWidth: '380px',
          backgroundColor: '#0F1424',
          borderRadius: '20px',
          border: '1px solid rgba(255,255,255,0.08)',
          padding: '32px 28px 28px',
          position: 'relative',
          boxShadow: '0 24px 48px rgba(0,0,0,0.5)',
        }}
      >
        <button
          onClick={onComplete}
          style={{
            position: 'absolute', top: '16px', right: '16px',
            background: 'none', border: 'none',
            fontFamily: 'var(--font-mono)', fontSize: '12px',
            color: 'rgba(255,255,255,0.4)', cursor: 'pointer',
            letterSpacing: '0.05em',
          }}
        >Skip</button>

        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ marginBottom: '20px', opacity: 0.9 }}>
            {screen.icon}
          </div>
          <h2 style={{
            fontFamily: 'var(--font-sans)', fontSize: '22px', fontWeight: 700,
            color: '#FFFFFF', margin: '0 0 12px', lineHeight: 1.2,
          }}>{screen.headline}</h2>
          <p style={{
            fontFamily: 'var(--font-sans)', fontSize: '14px',
            color: 'rgba(255,255,255,0.55)', lineHeight: 1.6,
            margin: 0, maxWidth: '280px', marginLeft: 'auto', marginRight: 'auto',
          }}>{screen.body}</p>
        </div>

        <div style={{
          display: 'flex', justifyContent: 'center', gap: '8px',
          marginBottom: '20px',
        }}>
          {SCREENS.map((_, i) => (
            <div
              key={i}
              onClick={() => setStep(i)}
              style={{
                width: i === step ? '20px' : '6px', height: '6px',
                borderRadius: '3px', cursor: 'pointer',
                backgroundColor: i === step ? '#5A9E72' : 'rgba(255,255,255,0.15)',
                transition: 'all 0.2s ease',
              }}
            />
          ))}
        </div>

        <button
          onClick={handleNext}
          style={{
            width: '100%', height: '48px',
            background: step === SCREENS.length - 1
              ? 'linear-gradient(135deg, #5A9E72, #4A8E62)'
              : 'var(--blue-primary)',
            border: 'none', borderRadius: '12px',
            color: '#FFFFFF', fontSize: '15px', fontWeight: 700,
            fontFamily: 'var(--font-sans)', cursor: 'pointer',
          }}
        >{screen.cta}</button>
      </div>
    </div>
  );
}

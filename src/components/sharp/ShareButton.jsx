import { useState } from 'react';

export function ShareIcon({ size = 18, color = 'var(--text-tertiary)' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 17l9.2-9.2M17 17V7H7" />
    </svg>
  );
}

export default function ShareButton({ onShare, style = {} }) {
  const [pressed, setPressed] = useState(false);
  const [sharing, setSharing] = useState(false);

  const handleTap = async () => {
    if (sharing) return;
    setSharing(true);
    try {
      await onShare();
    } finally {
      setSharing(false);
    }
  };

  return (
    <button
      onClick={handleTap}
      onPointerDown={() => setPressed(true)}
      onPointerUp={() => setPressed(false)}
      onPointerLeave={() => setPressed(false)}
      disabled={sharing}
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        minWidth: '44px', minHeight: '44px',
        background: 'none', border: 'none', cursor: 'pointer',
        opacity: pressed ? 0.5 : (sharing ? 0.4 : 1),
        transition: 'opacity 0.1s',
        padding: 0,
        ...style,
      }}
      aria-label="Share"
    >
      <ShareIcon />
    </button>
  );
}

export function ShareResultsButton({ onShare }) {
  const [pressed, setPressed] = useState(false);
  const [sharing, setSharing] = useState(false);

  const handleTap = async () => {
    if (sharing) return;
    setSharing(true);
    try {
      await onShare();
    } finally {
      setSharing(false);
    }
  };

  return (
    <button
      onClick={handleTap}
      onPointerDown={() => setPressed(true)}
      onPointerUp={() => setPressed(false)}
      onPointerLeave={() => setPressed(false)}
      disabled={sharing}
      style={{
        width: '100%', padding: '14px',
        background: 'transparent',
        border: '1px solid var(--color-border)',
        borderRadius: '12px',
        color: 'var(--text-secondary)',
        fontSize: '14px', fontWeight: 700,
        fontFamily: 'var(--font-mono)',
        letterSpacing: '0.05em', textTransform: 'uppercase',
        cursor: 'pointer',
        opacity: pressed ? 0.5 : (sharing ? 0.4 : 1),
        transition: 'opacity 0.1s',
        minHeight: '44px',
      }}
    >
      {sharing ? 'Generating...' : 'Share Results'}
    </button>
  );
}

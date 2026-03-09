export default function OnboardingFlow({ onComplete }) {
  return (
    <div style={{
      position: 'fixed', inset: 0,
      backgroundColor: '#0A0D14',
      zIndex: 1000,
      display: 'flex', flexDirection: 'column',
      maxWidth: '480px', margin: '0 auto',
      overflow: 'hidden',
    }}>
      {/* ── Top safe area ── */}
      <div style={{
        paddingTop: 'max(env(safe-area-inset-top, 16px), 16px)',
      }} />

      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '0 32px',
      }}>

        {/* ── Logo ── */}
        <img
          src="/images/crest.png"
          alt="SharpPicks"
          style={{
            width: '80px', height: '80px',
            objectFit: 'contain',
            opacity: 0.08,
            marginBottom: '16px',
          }}
        />

        {/* ── Wordmark ── */}
        <div style={{
          fontFamily: 'var(--font-sans)', fontSize: '14px', fontWeight: 700,
          letterSpacing: '0.2em', textTransform: 'uppercase',
          color: 'rgba(255,255,255,0.5)',
          marginBottom: '28px',
        }}>
          SHARP<span style={{ opacity: 0.4, margin: '0 0.25em' }}>||</span>PICKS
        </div>

        {/* ── Headline ── */}
        <h1 style={{
          fontFamily: 'var(--font-serif)', fontSize: '28px', fontWeight: 700,
          color: '#FFFFFF', lineHeight: 1.15,
          textAlign: 'center',
          maxWidth: '280px',
          margin: '0 auto 12px',
        }}>
          Sports markets analyzed like financial markets
        </h1>

        {/* ── Subtext ── */}
        <p style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '15px', color: 'rgba(255,255,255,0.5)', lineHeight: 1.6,
          textAlign: 'center', maxWidth: '260px', margin: '0 auto 24px',
        }}>
          One signal per day. Only when the edge is real.
        </p>

        {/* ── Process Flow ── */}
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          marginBottom: '20px', width: '100%', maxWidth: '220px',
        }}>
          {['Market Data', 'Model Analysis', 'Edge Detection', 'Qualification Filters'].map((label) => (
            <div key={label} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div style={{
                fontFamily: 'var(--font-mono, monospace)', fontSize: '11px',
                fontWeight: 500, letterSpacing: '0.08em',
                color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase',
                padding: '4px 0',
              }}>{label}</div>
              <div style={{ width: '1px', height: '8px', backgroundColor: '#1E2A3A' }} />
            </div>
          ))}
          <div style={{
            fontFamily: 'var(--font-mono, monospace)', fontSize: '12px',
            fontWeight: 700, letterSpacing: '0.06em',
            color: '#5A9E72', textTransform: 'uppercase',
            padding: '4px 0',
            borderBottom: '2px solid #5A9E72',
          }}>Qualified Signal</div>
        </div>

        {/* ── Philosophy ── */}
        <p style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '14px', fontWeight: 500,
          fontStyle: 'italic', color: 'rgba(255,255,255,0.55)', lineHeight: 1.6,
          textAlign: 'center', margin: '0 0 20px',
        }}>
          Passing is a position.<br />
          Selective by design.
        </p>

        {/* ── Supporting Points ── */}
        <div style={{ maxWidth: '300px', width: '100%' }}>
          <SupportPoint text="Every game is analyzed — the model evaluates the full daily slate" />
          <SupportPoint text="Most edges are filtered out — only statistically significant edges pass" />
          <SupportPoint text="Signals appear only when an inefficiency is detected — not on a schedule" />
        </div>
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

function SupportPoint({ text }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: '10px',
      marginBottom: '8px',
    }}>
      <div style={{
        width: '5px', height: '5px', borderRadius: '50%',
        backgroundColor: '#5A9E72',
        flexShrink: 0, marginTop: '7px',
      }} />
      <span style={{
        fontSize: '13px', color: 'rgba(255,255,255,0.4)', lineHeight: 1.5,
      }}>{text}</span>
    </div>
  );
}

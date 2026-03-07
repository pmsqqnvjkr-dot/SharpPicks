export default function OnboardingFlow({ onComplete }) {
  return (
    <div style={{
      position: 'fixed', inset: 0,
      backgroundColor: '#0A0D14',
      zIndex: 1000,
      display: 'flex', flexDirection: 'column',
      maxWidth: '480px', margin: '0 auto',
      overflowY: 'auto',
      WebkitOverflowScrolling: 'touch',
    }}>
      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '0 32px',
        minHeight: '100vh',
      }}>

        {/* ── Logo ── */}
        <img
          src="/images/crest.png"
          alt="SharpPicks"
          style={{
            width: '72px', height: '72px',
            objectFit: 'contain',
            marginBottom: '24px',
          }}
        />

        {/* ── Wordmark ── */}
        <div style={{
          fontFamily: 'var(--font-sans)', fontSize: '18px', fontWeight: 700,
          letterSpacing: '0.18em', textTransform: 'uppercase',
          color: '#FFFFFF',
          marginBottom: '48px',
        }}>
          SHARP<span style={{ opacity: 0.4, margin: '0 0.25em' }}>||</span>PICKS
        </div>

        {/* ── Headline ── */}
        <h1 style={{
          fontFamily: 'var(--font-sans)', fontSize: '26px', fontWeight: 600,
          color: '#FFFFFF', lineHeight: 1.25,
          textAlign: 'center', marginBottom: '16px',
          maxWidth: '320px',
          margin: '0 auto 16px',
        }}>
          Sports markets analyzed like financial markets
        </h1>

        {/* ── Subtext ── */}
        <p style={{
          fontSize: '15px', color: '#8A94A6', lineHeight: 1.7,
          textAlign: 'center', maxWidth: '310px', margin: '0 auto 40px',
        }}>
          One signal per day. Only when the edge is real.
        </p>

        {/* ── Divider ── */}
        <div style={{
          width: '40px', height: '1px',
          backgroundColor: '#5A9E72',
          margin: '0 auto 40px',
        }} />

        {/* ── Process Flow ── */}
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          marginBottom: '40px', width: '100%', maxWidth: '240px',
        }}>
          {['Market Data', 'Model Analysis', 'Edge Detection', 'Qualification Filters'].map((label, i) => (
            <div key={label} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div style={{
                fontFamily: 'var(--font-mono, monospace)', fontSize: '12px',
                fontWeight: 500, letterSpacing: '0.06em',
                color: '#5A6678', textTransform: 'uppercase',
                padding: '8px 0',
              }}>{label}</div>
              <div style={{ width: '1px', height: '14px', backgroundColor: '#1E2A3A' }} />
            </div>
          ))}
          <div style={{
            fontFamily: 'var(--font-mono, monospace)', fontSize: '13px',
            fontWeight: 700, letterSpacing: '0.06em',
            color: '#5A9E72', textTransform: 'uppercase',
            padding: '8px 0',
            borderBottom: '2px solid #5A9E72',
          }}>Qualified Signal</div>
        </div>

        {/* ── Philosophy ── */}
        <div style={{
          textAlign: 'center', marginBottom: '40px',
          maxWidth: '280px',
        }}>
          <p style={{
            fontSize: '15px', fontWeight: 500,
            fontStyle: 'italic', color: '#C8CDD5', lineHeight: 1.6,
            margin: 0,
          }}>
            Passing is a position.<br />
            Selective by design.
          </p>
        </div>

        {/* ── Supporting Points ── */}
        <div style={{
          maxWidth: '320px', width: '100%', marginBottom: '48px',
        }}>
          <SupportPoint text="Every game is analyzed — the model evaluates the full daily slate" />
          <SupportPoint text="Most edges are filtered out — only statistically significant edges pass" />
          <SupportPoint text="Signals appear only when an inefficiency is detected — not on a schedule" />
        </div>
      </div>

      {/* ── CTA ── */}
      <div style={{
        padding: '0 32px 32px',
        paddingBottom: 'max(32px, calc(env(safe-area-inset-bottom, 0px) + 32px))',
        position: 'sticky', bottom: 0,
        backgroundColor: '#0A0D14',
      }}>
        <button
          onClick={onComplete}
          onPointerDown={e => { e.currentTarget.style.opacity = '0.85'; }}
          onPointerUp={e => { e.currentTarget.style.opacity = '1'; }}
          onPointerLeave={e => { e.currentTarget.style.opacity = '1'; }}
          style={{
            width: '100%', height: '52px',
            background: '#5A9E72',
            border: 'none', borderRadius: '10px',
            color: '#FFFFFF', fontSize: '15px', fontWeight: 600,
            fontFamily: 'var(--font-sans)',
            letterSpacing: '0.06em', textTransform: 'uppercase',
            cursor: 'pointer',
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
      display: 'flex', alignItems: 'flex-start', gap: '12px',
      marginBottom: '14px',
    }}>
      <div style={{
        width: '6px', height: '6px', borderRadius: '50%',
        backgroundColor: '#5A9E72',
        flexShrink: 0, marginTop: '7px',
      }} />
      <span style={{
        fontSize: '14px', color: '#8A94A6', lineHeight: 1.6,
      }}>{text}</span>
    </div>
  );
}

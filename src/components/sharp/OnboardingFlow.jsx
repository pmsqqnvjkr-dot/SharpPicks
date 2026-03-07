export default function OnboardingFlow({ onComplete }) {
  return (
    <div style={{
      position: 'fixed', inset: 0,
      backgroundColor: 'var(--bg-primary)',
      zIndex: 1000,
      display: 'flex', flexDirection: 'column',
      maxWidth: '480px', margin: '0 auto',
      overflowY: 'auto',
      WebkitOverflowScrolling: 'touch',
    }}>
      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column',
        padding: '0 24px',
      }}>

        {/* ── Wordmark ── */}
        <div style={{
          textAlign: 'center',
          paddingTop: 'max(env(safe-area-inset-top, 20px), 48px)',
          marginBottom: 'var(--space-xl)',
        }}>
          <span style={{
            fontFamily: 'var(--font-sans)', fontSize: '14px', fontWeight: 700,
            letterSpacing: '0.2em', textTransform: 'uppercase',
            color: 'var(--color-signal)',
          }}>SHARP<span style={{ opacity: 0.5, margin: '0 0.3em' }}>||</span>PICKS</span>
        </div>

        {/* ── Headline ── */}
        <h1 style={{
          fontFamily: 'var(--font-sans)', fontSize: '28px', fontWeight: 600,
          color: 'var(--text-primary)', lineHeight: 1.2,
          textAlign: 'center', marginBottom: 'var(--space-lg)',
          maxWidth: '340px', margin: '0 auto var(--space-lg)',
        }}>
          Sports markets analyzed<br />like financial markets
        </h1>

        {/* ── Subtext ── */}
        <p style={{
          fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.7,
          textAlign: 'center', maxWidth: '320px', margin: '0 auto',
          marginBottom: 'var(--space-lg)',
        }}>
          SharpPicks scans the entire betting market and identifies
          statistical edges using ensemble machine learning.
        </p>
        <p style={{
          fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.7,
          textAlign: 'center', maxWidth: '320px', margin: '0 auto',
          marginBottom: 'var(--space-xl)',
        }}>
          Only edges that pass strict qualification filters become
          signals. Most days produce few opportunities.
        </p>

        {/* ── Philosophy ── */}
        <div style={{
          textAlign: 'center',
          padding: 'var(--space-xl) 0',
          borderTop: '1px solid var(--color-border)',
          borderBottom: '1px solid var(--color-border)',
          margin: '0 auto var(--space-xl)',
          maxWidth: '280px', width: '100%',
        }}>
          <p style={{
            fontFamily: 'var(--font-sans)', fontSize: '16px', fontWeight: 500,
            fontStyle: 'italic', color: 'var(--text-primary)', lineHeight: 1.6,
            margin: 0,
          }}>
            Passing is a position.<br />
            Selective by design.
          </p>
        </div>

        {/* ── Process Diagram ── */}
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          maxWidth: '200px', margin: '0 auto var(--space-xl)', width: '100%',
        }}>
          <ProcessStep label="Market Data" />
          <Connector />
          <ProcessStep label="Model Analysis" />
          <Connector />
          <ProcessStep label="Edge Detection" />
          <Connector />
          <ProcessStep label="Qualification Filters" />
          <Connector />
          <ProcessStep label="Qualified Signal" isSignal />
        </div>

        {/* ── Supporting Points ── */}
        <div style={{
          padding: '0 0 var(--space-xl)',
          maxWidth: '340px', margin: '0 auto', width: '100%',
        }}>
          <SupportPoint text="Every game is analyzed — the model evaluates the full daily slate" />
          <SupportPoint text="Most edges are filtered out — only statistically significant edges pass" />
          <SupportPoint text="Signals appear only when an inefficiency is detected — not on a schedule" />
        </div>
      </div>

      {/* ── CTA ── */}
      <div style={{
        padding: '0 24px 24px',
        paddingBottom: 'max(24px, calc(env(safe-area-inset-bottom, 0px) + 24px))',
      }}>
        <button
          onClick={onComplete}
          onPointerDown={e => { e.currentTarget.style.opacity = '0.8'; }}
          onPointerUp={e => { e.currentTarget.style.opacity = '1'; }}
          onPointerLeave={e => { e.currentTarget.style.opacity = '1'; }}
          style={{
            width: '100%', height: '52px',
            background: 'var(--color-signal)',
            border: 'none', borderRadius: '8px',
            color: '#fff', fontSize: '16px', fontWeight: 600,
            fontFamily: 'var(--font-sans)',
            letterSpacing: '0.05em', textTransform: 'uppercase',
            cursor: 'pointer',
          }}
        >
          Enter Market View
        </button>
      </div>
    </div>
  );
}

function ProcessStep({ label, isSignal }) {
  return (
    <div style={{
      fontFamily: 'var(--font-sans)', fontSize: '14px',
      fontWeight: isSignal ? 700 : 400,
      color: isSignal ? 'var(--color-signal)' : 'var(--text-secondary)',
      textAlign: 'center',
      padding: 'var(--space-sm) 0',
    }}>
      {label}
    </div>
  );
}

function Connector() {
  return (
    <div style={{
      width: '1px', height: '16px',
      backgroundColor: 'var(--color-border)',
    }} />
  );
}

function SupportPoint({ text }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 'var(--space-sm)',
      marginBottom: 'var(--space-sm)',
      paddingLeft: 'var(--space-lg)',
    }}>
      <span style={{
        color: 'var(--color-signal)', fontSize: '14px', lineHeight: 1.6,
        flexShrink: 0,
      }}>✔</span>
      <span style={{
        fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6,
      }}>{text}</span>
    </div>
  );
}

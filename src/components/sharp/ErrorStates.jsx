export default function ErrorStates({ errors, onBack }) {
  const activeErrors = errors?.filter(e => !e.resolved) || [];
  const resolvedErrors = errors?.filter(e => e.resolved) || [];

  return (
    <div style={{ padding: 0, paddingBottom: '100px' }}>
      <div style={{
        padding: 'var(--space-md) 20px',
        display: 'flex', alignItems: 'center', gap: '12px',
      }}>
        {onBack && (
          <button onClick={onBack} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-secondary)', padding: '4px',
            minWidth: '44px', minHeight: '44px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
          </button>
        )}
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: '16px', fontWeight: 600,
          color: 'var(--text-primary)',
        }}>System Status</span>
      </div>

      <div style={{ padding: '0 20px' }}>
        {activeErrors.length > 0 && (
          <>
            <SectionLabel>Active Notices</SectionLabel>
            {activeErrors.map((err, i) => (
              <ErrorCard key={i} error={err} />
            ))}
          </>
        )}

        {activeErrors.length === 0 && (
          <div style={{
            backgroundColor: 'var(--surface-1)', borderRadius: '16px',
            border: '1px solid var(--color-border)', padding: 'var(--space-lg)',
            marginBottom: 'var(--space-md)', textAlign: 'center',
          }}>
            <div style={{
              width: '48px', height: '48px', borderRadius: '12px',
              backgroundColor: 'var(--color-signal-bg)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto var(--space-md)',
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-signal)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
            <div style={{
              fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)',
              marginBottom: '6px',
            }}>All Systems Operational</div>
            <div style={{
              fontSize: '13px', color: 'var(--text-secondary)',
            }}>Model and data feeds running normally.</div>
          </div>
        )}

        {resolvedErrors.length > 0 && (
          <>
            <div style={{ marginTop: activeErrors.length > 0 ? '20px' : 0 }}>
              <SectionLabel>Resolved</SectionLabel>
            </div>
            {resolvedErrors.map((err, i) => (
              <ErrorCard key={i} error={err} resolved />
            ))}
          </>
        )}
      </div>
    </div>
  );
}

export function InlineError({ title, message }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '14px',
      border: '1px solid var(--color-border)',
      padding: 'var(--space-md) 20px', marginBottom: '12px',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-sm)',
      }}>
        <div style={{
          width: '6px', height: '6px', borderRadius: '50%',
          backgroundColor: 'var(--gold-pro)',
        }} />
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)',
          fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
          color: 'var(--text-primary)',
        }}>{title}</span>
      </div>
      <p style={{
        fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6',
      }}>{message}</p>
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <div style={{
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-label-size)', fontWeight: 700,
      letterSpacing: '0.08em', textTransform: 'uppercase',
      color: 'var(--text-tertiary)',
      marginBottom: '10px',
    }}>{children}</div>
  );
}

function ErrorCard({ error, resolved }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)', borderRadius: '14px',
      border: '1px solid var(--color-border)',
      padding: 'var(--space-md) 20px', marginBottom: '10px',
      opacity: resolved ? 0.5 : 1,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-sm)',
      }}>
        <div style={{
          width: '6px', height: '6px', borderRadius: '50%',
          backgroundColor: resolved ? 'var(--color-signal)' : 'var(--gold-pro)',
        }} />
        <span style={{
          fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)',
        }}>{error.title}</span>
      </div>
      <p style={{
        fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6',
      }}>{error.message}</p>
    </div>
  );
}

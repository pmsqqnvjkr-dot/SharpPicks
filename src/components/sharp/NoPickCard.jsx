export default function NoPickCard({ data }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '16px',
      overflow: 'hidden',
      border: '1px solid var(--stroke-subtle)',
      marginTop: '8px',
    }}>
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--stroke-subtle)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}>
        <div style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: 'var(--text-tertiary)',
        }} />
        <span style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '12px',
          fontWeight: 600,
          color: 'var(--text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}>
          No Pick Today
        </span>
      </div>

      <div style={{ padding: '32px 24px', textAlign: 'center' }}>
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '14px',
          backgroundColor: 'var(--surface-2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 20px',
        }}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--blue-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </div>

        <h2 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: '22px',
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: '12px',
        }}>
          Discipline preserved
        </h2>

        <p style={{
          fontSize: '14px',
          color: 'var(--text-secondary)',
          lineHeight: '1.7',
          maxWidth: '320px',
          margin: '0 auto 24px',
        }}>
          {data.message}
        </p>

        <div style={{
          backgroundColor: 'var(--surface-2)',
          borderRadius: '12px',
          padding: '16px',
          display: 'flex',
          justifyContent: 'center',
          gap: '32px',
        }}>
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '18px',
              fontWeight: 600,
              color: 'var(--text-primary)',
            }}>
              {data.games_analyzed}
            </div>
            <div style={{
              fontSize: '11px',
              color: 'var(--text-tertiary)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginTop: '2px',
            }}>
              Analyzed
            </div>
          </div>
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '18px',
              fontWeight: 600,
              color: 'var(--text-primary)',
            }}>
              {data.closest_edge_pct ? `${data.closest_edge_pct}%` : '--'}
            </div>
            <div style={{
              fontSize: '11px',
              color: 'var(--text-tertiary)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginTop: '2px',
            }}>
              Best Edge
            </div>
          </div>
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '18px',
              fontWeight: 600,
              color: 'var(--blue-primary)',
            }}>
              3.5%
            </div>
            <div style={{
              fontSize: '11px',
              color: 'var(--text-tertiary)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginTop: '2px',
            }}>
              Threshold
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

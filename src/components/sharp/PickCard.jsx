export default function PickCard({ pick, isPro, onUpgrade }) {
  const isLocked = pick.locked && !isPro;

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
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: 'var(--green-profit)',
          }} />
          <span style={{
            fontFamily: 'var(--font-sans)',
            fontSize: '12px',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}>
            Today's Pick
          </span>
        </div>
        {pick.edge_pct && (
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '12px',
            color: 'var(--green-profit)',
            backgroundColor: 'rgba(52, 211, 153, 0.1)',
            padding: '4px 10px',
            borderRadius: '6px',
          }}>
            {pick.edge_pct}% edge
          </span>
        )}
      </div>

      <div style={{ padding: '24px 20px' }}>
        <div style={{
          fontSize: '13px',
          color: 'var(--text-tertiary)',
          marginBottom: '6px',
        }}>
          {pick.away_team} @ {pick.home_team}
        </div>

        {isLocked ? (
          <div>
            <div style={{
              fontFamily: 'var(--font-serif)',
              fontSize: '28px',
              fontWeight: 600,
              color: 'var(--text-primary)',
              marginBottom: '4px',
              filter: 'blur(8px)',
              userSelect: 'none',
            }}>
              Team -3.5
            </div>
            <p style={{
              fontSize: '14px',
              color: 'var(--text-secondary)',
              marginTop: '16px',
              marginBottom: '16px',
            }}>
              A qualifying edge was found today. Upgrade to see the full pick.
            </p>
            <button
              onClick={onUpgrade}
              style={{
                width: '100%',
                padding: '14px',
                backgroundColor: 'var(--blue-primary)',
                color: '#fff',
                border: 'none',
                borderRadius: '10px',
                fontSize: '15px',
                fontWeight: 600,
                cursor: 'pointer',
                fontFamily: 'var(--font-sans)',
              }}
            >
              Start Free Trial
            </button>
          </div>
        ) : (
          <div>
            <div style={{
              fontFamily: 'var(--font-serif)',
              fontSize: '28px',
              fontWeight: 600,
              color: 'var(--text-primary)',
              marginBottom: '4px',
            }}>
              {pick.side}
            </div>
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '13px',
              color: 'var(--text-tertiary)',
            }}>
              {pick.line > 0 ? `+${pick.line}` : pick.line}
            </div>

            <div style={{
              marginTop: '20px',
              display: 'flex',
              gap: '12px',
            }}>
              <StatPill label="Confidence" value={`${(pick.model_confidence * 100).toFixed(0)}%`} />
              <StatPill label="Edge" value={`${pick.edge_pct}%`} />
            </div>

            {pick.result && pick.result !== 'pending' && (
              <div style={{
                marginTop: '16px',
                padding: '12px 16px',
                borderRadius: '10px',
                backgroundColor: pick.result === 'win'
                  ? 'rgba(52, 211, 153, 0.1)'
                  : 'rgba(239, 68, 68, 0.1)',
                border: `1px solid ${pick.result === 'win' ? 'rgba(52, 211, 153, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`,
              }}>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '14px',
                  fontWeight: 600,
                  color: pick.result === 'win' ? 'var(--green-profit)' : 'var(--red-loss)',
                }}>
                  {pick.result === 'win' ? 'Win +91u' : 'Loss -110u'}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function StatPill({ label, value }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-2)',
      borderRadius: '8px',
      padding: '8px 14px',
      flex: 1,
      textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '16px',
        fontWeight: 600,
        color: 'var(--text-primary)',
      }}>
        {value}
      </div>
      <div style={{
        fontSize: '10px',
        color: 'var(--text-tertiary)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginTop: '2px',
      }}>
        {label}
      </div>
    </div>
  );
}

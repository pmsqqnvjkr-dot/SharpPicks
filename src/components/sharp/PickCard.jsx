export default function PickCard({ pick, isPro, onUpgrade, onTrack }) {
  const isLocked = pick.locked && !isPro;

  if (isLocked) {
    return (
      <div style={{
        backgroundColor: 'var(--surface-1)',
        border: '1px solid var(--stroke-subtle)',
        borderRadius: '16px',
        padding: '24px 20px',
        marginTop: '8px',
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '10px', fontWeight: 600,
          letterSpacing: '1.5px', textTransform: 'uppercase',
          color: 'var(--green-profit)',
          marginBottom: '16px',
        }}>Pick Published Today</div>

        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '11px', fontWeight: 500,
          letterSpacing: '1.2px', textTransform: 'uppercase',
          color: 'var(--text-secondary)',
          marginBottom: '20px',
        }}>
          {pick.away_team} @ {pick.home_team}
        </div>

        <div style={{
          background: 'rgba(255,255,255,0.02)',
          border: '1px dashed var(--stroke-muted)',
          borderRadius: '12px',
          padding: '28px 20px',
          textAlign: 'center',
          marginBottom: '16px',
        }}>
          <div style={{ fontSize: '20px', marginBottom: '10px', opacity: 0.6 }}>🔒</div>
          <p style={{ fontSize: '13px', color: 'var(--text-tertiary)', lineHeight: '1.5', marginBottom: '16px' }}>
            Side and line locked for Pro members. Upgrade to see the full pick and track your bets.
          </p>
          <button
            onClick={onUpgrade}
            style={{
              width: '100%', height: '48px', borderRadius: '14px',
              border: 'none',
              background: 'linear-gradient(135deg, var(--blue-primary), var(--blue-deep))',
              color: 'white', fontFamily: 'var(--font-sans)',
              fontSize: '14px', fontWeight: 700, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
            }}
          >
            Start Free Trial
          </button>
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', textAlign: 'center', lineHeight: '1.5' }}>
          14-day free trial · Cancel anytime
        </p>
      </div>
    );
  }

  return (
    <div style={{ padding: '0 4px' }}>
      <article style={{
        borderRadius: '22px',
        padding: '22px 18px 18px',
        background: 'radial-gradient(900px 520px at 40% 0%, rgba(79,134,247,0.26), transparent 55%), linear-gradient(165deg, rgba(23,36,74,0.92), rgba(17,26,56,0.92))',
        border: '1px solid rgba(79,134,247,0.18)',
        boxShadow: '0 10px 30px rgba(0,0,0,0.35)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: '10px',
          marginBottom: '14px',
        }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            padding: '8px 12px', borderRadius: '999px',
            fontFamily: 'var(--font-sans)',
            fontSize: '11px', fontWeight: 800,
            letterSpacing: '1.2px', textTransform: 'uppercase',
            border: '1px solid rgba(52,211,153,0.22)',
            background: 'rgba(52,211,153,0.10)',
            color: 'rgba(52,211,153,0.95)',
          }}>
            Qualified (A)
          </span>
        </div>

        <div style={{
          fontSize: '11px', letterSpacing: '1.6px', textTransform: 'uppercase',
          color: 'rgba(169,180,207,0.85)', fontWeight: 700,
          marginBottom: '6px',
        }}>
          {pick.away_team} @ {pick.home_team}
        </div>

        <div style={{
          fontSize: '34px', fontWeight: 800, lineHeight: '1.0',
          letterSpacing: '-0.6px',
          color: 'rgba(255,255,255,0.95)',
          textShadow: '0 12px 30px rgba(0,0,0,0.35)',
          marginBottom: '14px',
        }}>
          {pick.side}
        </div>

        <section style={{
          margin: '14px 0 12px',
          padding: '14px',
          borderRadius: '16px',
          border: '1px solid rgba(255,255,255,0.10)',
          background: 'rgba(0,0,0,0.18)',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            gap: '10px', marginBottom: '10px',
          }}>
            <span style={{
              fontSize: '11px', letterSpacing: '1.2px', textTransform: 'uppercase',
              fontWeight: 800, color: 'rgba(169,180,207,0.9)',
            }}>Expected Edge</span>
            <span style={{
              color: 'rgba(255,255,255,0.55)',
              fontSize: '10px', fontWeight: 800,
              letterSpacing: '1.1px', textTransform: 'uppercase',
            }}>Model vs Market</span>
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '30px', fontWeight: 800,
            color: 'var(--green-profit)',
            letterSpacing: '-0.6px',
          }}>+{pick.edge_pct}%</div>
        </section>

        <div style={{ height: '1px', background: 'rgba(255,255,255,0.10)', margin: '14px 0' }} />

        {pick.model_signals && pick.model_signals.length > 0 && (
          <>
            <div style={{
              fontSize: '11px', letterSpacing: '1.3px', textTransform: 'uppercase',
              fontWeight: 800, color: 'rgba(169,180,207,0.9)',
              margin: '10px 0',
            }}>Model Signal</div>
            <ul style={{
              margin: 0, paddingLeft: '18px',
              color: 'rgba(234,240,255,0.88)',
              lineHeight: '1.65', fontSize: '14px',
              listStyle: 'disc',
            }}>
              {pick.model_signals.map((s, i) => (
                <li key={i} style={{ margin: '6px 0' }}>{s}</li>
              ))}
            </ul>
            <div style={{ height: '1px', background: 'rgba(255,255,255,0.10)', margin: '14px 0' }} />
          </>
        )}

        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: '12px', marginTop: '12px',
        }}>
          <PickStat label="Model line" value={pick.model_line || pick.line || '--'} />
          <PickStat label="Market" value={pick.market_line || '--'} />
          <PickStat label="Confidence" value={`${pick.model_confidence ? (pick.model_confidence * 100).toFixed(0) : '--'}%`} />
          <PickStat label="Edge" value={`${pick.edge_pct}%`} profit />
        </div>

        {pick.result && pick.result !== 'pending' ? (
          <div style={{
            marginTop: '16px', padding: '14px',
            borderRadius: '16px',
            border: `1px solid ${pick.result === 'win' ? 'rgba(52,211,153,0.22)' : 'rgba(239,68,68,0.22)'}`,
            background: pick.result === 'win' ? 'rgba(52,211,153,0.08)' : 'rgba(239,68,68,0.08)',
            textAlign: 'center',
          }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 800,
              color: pick.result === 'win' ? 'var(--green-profit)' : 'var(--red-loss)',
            }}>
              {pick.result === 'win' ? `Win +${pick.pnl ?? 91}u` : `Loss ${pick.pnl ?? -110}u`}
            </div>
          </div>
        ) : (
          <button
            onClick={() => onTrack && onTrack(pick)}
            style={{
              width: '100%', marginTop: '16px',
              borderRadius: '16px', padding: '15px 14px',
              fontWeight: 800, fontSize: '15px', letterSpacing: '0.3px',
              color: 'rgba(255,255,255,0.92)',
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.14)',
              boxShadow: '0 12px 30px rgba(0,0,0,0.25)',
              cursor: 'pointer',
            }}
          >
            Track outcome
          </button>
        )}

        <div style={{
          marginTop: '14px', paddingTop: '14px',
          borderTop: '1px solid rgba(255,255,255,0.10)',
          fontSize: '12px', lineHeight: '1.55',
          color: 'rgba(169,180,207,0.78)',
          textAlign: 'center',
        }}>
          Posted {pick.posted_time || '2h before tip'} · Best at {pick.best_book || 'DraftKings'}
        </div>
      </article>
    </div>
  );
}

function PickStat({ label, value, profit }) {
  return (
    <div style={{
      borderRadius: '16px', padding: '12px 12px 10px',
      border: '1px solid rgba(255,255,255,0.10)',
      background: 'rgba(0,0,0,0.16)',
    }}>
      <div style={{
        fontSize: '10px', letterSpacing: '1.25px', textTransform: 'uppercase',
        fontWeight: 800, color: 'rgba(169,180,207,0.9)',
        marginBottom: '8px',
      }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '20px', fontWeight: 800,
        color: profit ? 'var(--green-profit)' : 'rgba(255,255,255,0.95)',
        letterSpacing: '-0.2px',
        fontVariantNumeric: 'tabular-nums',
      }}>{value}</div>
    </div>
  );
}

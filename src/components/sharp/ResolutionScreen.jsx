export default function ResolutionScreen({ pick, onBack }) {
  const isRevoked = pick?.result === 'revoked';
  const isWin = pick?.result === 'win';
  const isPush = pick?.result === 'push';

  if (isRevoked) {
    return <WithdrawnDetailScreen pick={pick} onBack={onBack} />;
  }

  const accentColor = isPush ? 'var(--text-secondary)' : isWin ? 'var(--green-profit)' : 'var(--red-loss)';
  const resultLabel = isPush ? 'Push' : isWin ? 'Win' : 'Loss';
  const profitDisplay = pick?.profit_units != null
    ? `${pick.profit_units >= 0 ? '+' : ''}${pick.profit_units}u`
    : '--';
  const hasScore = pick?.home_score != null && pick?.away_score != null;

  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>
      <div style={{
        padding: '16px 20px',
        display: 'flex', alignItems: 'center', gap: '12px',
      }}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-secondary)', padding: '4px',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </button>
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: '16px', fontWeight: 600,
          color: 'var(--text-primary)',
        }}>Outcome Resolved</span>
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '20px',
          border: '1px solid var(--stroke-subtle)', padding: '24px',
          marginBottom: '16px', textAlign: 'center',
        }}>
          <div style={{
            width: '56px', height: '56px', borderRadius: '50%',
            backgroundColor: isPush ? 'rgba(255,255,255,0.05)' : isWin ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            border: `2px solid ${accentColor}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px',
          }}>
            {isPush ? (
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={accentColor} strokeWidth="2.5" strokeLinecap="round">
                <line x1="6" y1="12" x2="18" y2="12"/>
              </svg>
            ) : isWin ? (
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={accentColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            ) : (
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={accentColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            )}
          </div>

          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600,
            letterSpacing: '2px', textTransform: 'uppercase',
            color: accentColor, marginBottom: '8px',
          }}>{resultLabel}</div>

          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: '22px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '6px',
          }}>
            {pick?.away_team} @ {pick?.home_team}
          </div>

          {hasScore && (
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 600,
              color: 'var(--text-primary)', marginBottom: '8px',
            }}>
              {pick.away_score} – {pick.home_score}
            </div>
          )}

          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '14px',
            color: 'var(--text-secondary)', marginBottom: '16px',
          }}>
            {pick?.side} {pick?.line > 0 ? `+${pick.line}` : pick?.line}
            {pick?.market_odds ? ` (${pick.market_odds > 0 ? '+' : ''}${pick.market_odds})` : ''}
          </div>

          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '36px', fontWeight: 700,
            color: accentColor,
          }}>{profitDisplay}</div>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '16px',
        }}>
          <h3 style={{
            fontFamily: 'var(--font-sans)', fontSize: '15px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '12px',
          }}>Process Review</h3>
          <p style={{
            fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.7',
            marginBottom: '16px',
          }}>
            {isPush
              ? `The spread landed exactly on the number. Your wager is returned — no win, no loss. The edge was ${pick?.edge_pct || '--'}% at entry. A push is variance doing what variance does.`
              : isWin
              ? `This outcome was within the model's expected range. The edge was ${pick?.edge_pct || '--'}% — meaning a win was expected roughly ${Math.round(50 + (pick?.edge_pct || 0))}% of the time. This result confirms the process, but one win does not validate a model.`
              : `This outcome was within the model's expected range. The edge was ${pick?.edge_pct || '--'}% — meaning a loss was expected roughly ${Math.round(50 - (pick?.edge_pct || 0))}% of the time. A single loss does not invalidate the model.`
            }
          </p>

          <div style={{
            display: 'flex', justifyContent: 'space-around',
            padding: '16px 0', borderTop: '1px solid var(--stroke-subtle)',
          }}>
            <ContextStat value={`${pick?.edge_pct || '--'}%`} label="Edge at entry" />
            <ContextStat value={`${Math.round(50 + (pick?.edge_pct || 0))}%`} label="Win probability" />
            <ContextStat value={pick?.season_record || '--'} label="Season record" />
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '16px',
        }}>
          <h3 style={{
            fontFamily: 'var(--font-sans)', fontSize: '15px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '12px',
          }}>What Discipline Looks Like Now</h3>
          <p style={{
            fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.7',
          }}>
            {isPush
              ? 'A push changes nothing. No adjustment needed. The process identified an edge, the game landed on the number. The next pick comes when the edge is there.'
              : isWin
              ? 'The correct response to a win is the same as a loss: nothing. No expanding your criteria. No overconfidence. The next pick comes when the edge is there.'
              : 'The correct response to a loss is the same as a win: nothing. No revenge bets. No doubling down. No changing your unit size. The next pick comes when the edge is there.'
            }
          </p>
        </div>

        <div style={{
          fontFamily: 'var(--font-serif)', fontStyle: 'italic', fontSize: '14px',
          color: 'var(--text-secondary)', textAlign: 'center',
          padding: '16px 0 8px', lineHeight: '1.5',
        }}>
          {isPush
            ? "A push is neither validation nor failure. The number landed exactly where the market set it."
            : isWin
            ? "A win doesn't mean you were right. It means the probability played out."
            : "A loss doesn't mean the model failed. It means variance occurred within expected parameters."
          }
        </div>

        <p style={{
          fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'center',
          padding: '4px 0 16px', lineHeight: '1.5',
        }}>
          Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  );
}

function WithdrawnDetailScreen({ pick, onBack }) {
  const accentColor = 'rgba(99,102,241,0.8)';

  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>
      <div style={{
        padding: '16px 20px',
        display: 'flex', alignItems: 'center', gap: '12px',
      }}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-secondary)', padding: '4px',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </button>
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: '16px', fontWeight: 600,
          color: 'var(--text-primary)',
        }}>Pick Withdrawn</span>
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '20px',
          border: '1px solid var(--stroke-subtle)', padding: '24px',
          marginBottom: '16px', textAlign: 'center',
        }}>
          <div style={{
            width: '56px', height: '56px', borderRadius: '50%',
            backgroundColor: 'rgba(99,102,241,0.1)',
            border: `2px solid ${accentColor}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px',
          }}>
            <svg viewBox="0 0 24 24" width="24" height="24" stroke={accentColor} fill="none" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>

          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600,
            letterSpacing: '2px', textTransform: 'uppercase',
            color: accentColor, marginBottom: '8px',
          }}>Withdrawn</div>

          <div style={{
            fontFamily: 'var(--font-serif)', fontSize: '22px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '6px',
          }}>
            {pick?.away_team} @ {pick?.home_team}
          </div>

          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '14px',
            color: 'var(--text-secondary)', marginBottom: '16px',
          }}>
            {pick?.side} {pick?.line > 0 ? `+${pick.line}` : pick?.line}
          </div>

          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '36px', fontWeight: 700,
            color: accentColor,
          }}>0u</div>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '16px',
        }}>
          <h3 style={{
            fontFamily: 'var(--font-sans)', fontSize: '15px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '12px',
          }}>Process Review</h3>
          <p style={{
            fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.7',
            marginBottom: '16px',
          }}>
            The market moved and the statistical edge fell below our threshold before tip-off. Capital was preserved. No trade is a position.
          </p>

          <div style={{
            display: 'flex', justifyContent: 'space-around',
            padding: '16px 0', borderTop: '1px solid var(--stroke-subtle)',
          }}>
            <ContextStat value={`${pick?.edge_pct || '--'}%`} label="Edge at entry" color={accentColor} />
            <ContextStat value={pick?.edge_at_close ? `${pick.edge_at_close}%` : '< threshold'} label="Edge at withdrawal" color="var(--text-tertiary)" />
            <ContextStat value="Pull" label="Action" color="var(--text-tertiary)" />
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '16px',
        }}>
          <h3 style={{
            fontFamily: 'var(--font-sans)', fontSize: '15px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '12px',
          }}>What Discipline Looks Like</h3>
          <p style={{
            fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.7',
          }}>
            Not every signal survives. The edge decides — not emotion. A withdrawal is the system protecting capital. The next pick comes when the edge is there.
          </p>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--stroke-subtle)', padding: '20px',
          marginBottom: '16px',
        }}>
          <h3 style={{
            fontFamily: 'var(--font-sans)', fontSize: '15px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '12px',
          }}>Already placed the bet?</h3>
          <p style={{
            fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.7',
          }}>
            If you already wagered before the withdrawal, treat it as a standalone decision. Your tracked bet will still be graded based on the actual game result. The withdrawal only reflects that the statistical edge no longer met our threshold.
          </p>
        </div>

        <div style={{
          fontFamily: 'var(--font-serif)', fontStyle: 'italic', fontSize: '14px',
          color: 'var(--text-secondary)', textAlign: 'center',
          padding: '16px 0 8px', lineHeight: '1.5',
        }}>
          Capital preservation is the discipline.
        </div>

        <p style={{
          fontSize: '11px', color: 'var(--text-tertiary)', textAlign: 'center',
          padding: '4px 0 16px', lineHeight: '1.5',
        }}>
          Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  );
}

function ContextStat({ value, label, color }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 600,
        color: color || 'var(--text-primary)', marginBottom: '4px',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.05em',
      }}>{label}</div>
    </div>
  );
}

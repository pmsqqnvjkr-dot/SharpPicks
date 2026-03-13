import { useEffect } from 'react';

export default function ResolutionScreen({ pick, onBack, onNavigate }) {
  useEffect(() => { window.scrollTo(0, 0); }, []);

  const isRevoked = pick?.result === 'revoked';
  const isWin = pick?.result === 'win';
  const isPush = pick?.result === 'push';

  if (isRevoked) {
    return <WithdrawnDetailScreen pick={pick} onBack={onBack} />;
  }

  const profitDisplay = pick?.profit_units != null
    ? `${pick.profit_units >= 0 ? '+' : ''}${Number(pick.profit_units).toFixed(1)}u`
    : '--';
  const hasScore = pick?.home_score != null && pick?.away_score != null;
  const pnlColor = isPush ? 'var(--text-secondary)' : isWin ? 'var(--color-signal)' : 'var(--color-loss)';

  const sideDisplay = pick?.side && pick?.line != null && pick.side.includes(String(Math.abs(pick.line)))
    ? pick.side
    : pick?.side && pick?.line != null
    ? `${pick.side} ${pick.line > 0 ? '+' : ''}${pick.line}`
    : pick?.side || '—';

  return (
    <div style={{ padding: 0, paddingBottom: '100px' }}>
      <div style={{
        padding: 'var(--space-md) 20px',
        display: 'flex', alignItems: 'center', gap: '12px',
      }}>
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
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: '16px', fontWeight: 600,
          color: 'var(--text-primary)',
        }}>Outcome Log</span>
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--color-border)', padding: 'var(--space-lg)',
          marginBottom: 'var(--space-md)', textAlign: 'center',
          opacity: 0.85,
        }}>
          <div style={{
            fontFamily: 'var(--font-sans)', fontSize: '20px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '6px',
          }}>
            {pick?.away_team} @ {pick?.home_team}
          </div>

          {hasScore && (
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 'var(--text-card-title)', fontWeight: 700,
              fontVariantNumeric: 'tabular-nums',
              color: 'var(--text-primary)', marginBottom: 'var(--space-sm)',
            }}>
              {pick.away_score} &ndash; {pick.home_score}
            </div>
          )}

          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '13px',
            fontVariantNumeric: 'tabular-nums',
            color: 'var(--text-tertiary)',
          }}>
            {sideDisplay}
            {pick?.market_odds ? ` (${pick.market_odds > 0 ? '+' : ''}${pick.market_odds})` : ''}
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--color-border)', padding: '20px',
          marginBottom: 'var(--space-md)',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '12px',
          }}>Process Review</div>
          <p style={{
            fontSize: 'var(--text-metric)', color: 'var(--text-secondary)', lineHeight: '1.7',
            marginBottom: 'var(--space-md)',
          }}>
            {isPush
              ? `Spread landed on the number. Wager returned. Edge was ${pick?.edge_pct || '--'}% at entry. Variance within expected parameters.`
              : isWin
              ? `Outcome within expected range. Edge: ${pick?.edge_pct || '--'}%. Win expected ~${Math.round(50 + (pick?.edge_pct || 0))}% of the time. One result does not validate a model.`
              : `Outcome within expected range. Edge: ${pick?.edge_pct || '--'}%. Loss expected ~${Math.round(50 - (pick?.edge_pct || 0))}% of the time. One result does not invalidate a model.`
            }
          </p>

          <div style={{
            display: 'flex', justifyContent: 'space-around',
            padding: 'var(--space-md) 0', borderTop: '1px solid var(--color-border)',
          }}>
            <ContextStat value={`${pick?.edge_pct || '--'}%`} label="Edge at entry" />
            <ContextStat value={`${Math.round(50 + (pick?.edge_pct || 0))}%`} label="Model probability" />
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '12px',
          border: '1px solid var(--color-border)', padding: '12px var(--space-md)',
          marginBottom: 'var(--space-md)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)',
          }}>P&L</span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '15px', fontWeight: 700,
            fontVariantNumeric: 'tabular-nums',
            color: pnlColor,
          }}>{profitDisplay}</span>
        </div>

        <CLVCard pick={pick} />

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--color-border)', padding: '20px',
          marginBottom: 'var(--space-md)',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '12px',
          }}>Discipline Framework</div>
          <p style={{
            fontSize: 'var(--text-metric)', color: 'var(--text-secondary)', lineHeight: '1.7',
          }}>
            {isPush
              ? 'Push changes nothing. Process identified an edge, game landed on the number. Next signal when the edge is there.'
              : isWin
              ? 'Correct response to a win: nothing. No expanding criteria. No overconfidence. Next signal when the edge is there.'
              : 'Correct response to a loss: nothing. No revenge bets. No doubling down. No changing unit size. Next signal when the edge is there.'
            }
          </p>
        </div>

        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 'var(--text-caption)',
          color: 'var(--text-tertiary)', textAlign: 'center',
          padding: 'var(--space-md) 0 var(--space-sm)', lineHeight: '1.5',
        }}>
          {isPush
            ? "Neither validation nor failure. The number landed where the market set it."
            : isWin
            ? "A win does not mean you were right. It means the probability played out."
            : "A loss does not mean the model failed. Variance within expected parameters."
          }
        </div>

        {onNavigate && (
          <button
            onClick={() => onNavigate('insights')}
            style={{
              width: '100%', textAlign: 'center', padding: '14px var(--space-md)',
              background: 'var(--surface-1)', border: '1px solid var(--color-border)',
              borderRadius: '12px', cursor: 'pointer', marginBottom: '12px',
              minHeight: '44px',
            }}
          >
            <span style={{
              fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5',
            }}>
              {isWin
                ? 'Read: Why one win does not change the process'
                : isPush
                ? 'Read: How pushes fit into long-term edge'
                : 'Read: How to think about losses correctly'}
            </span>
            <span style={{ color: 'var(--color-info)', fontWeight: 500, marginLeft: '6px' }}>&rarr;</span>
          </button>
        )}

        <p style={{
          fontSize: '10px', color: 'var(--text-tertiary)', textAlign: 'center',
          padding: '4px 0 var(--space-md)', lineHeight: '1.5', opacity: 0.6,
        }}>
          Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  );
}

function WithdrawnDetailScreen({ pick, onBack }) {
  useEffect(() => { window.scrollTo(0, 0); }, []);

  return (
    <div style={{ padding: 0, paddingBottom: '100px' }}>
      <div style={{
        padding: 'var(--space-md) 20px',
        display: 'flex', alignItems: 'center', gap: '12px',
      }}>
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
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: '16px', fontWeight: 600,
          color: 'var(--text-primary)',
        }}>Signal Withdrawn</span>
      </div>

      <div style={{ padding: '0 20px' }}>
        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--color-border)', padding: 'var(--space-lg)',
          marginBottom: 'var(--space-md)', textAlign: 'center',
        }}>
          <div style={{
            fontFamily: 'var(--font-sans)', fontSize: '20px', fontWeight: 600,
            color: 'var(--text-primary)', marginBottom: '6px',
          }}>
            {pick?.away_team} @ {pick?.home_team}
          </div>

          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '13px',
            fontVariantNumeric: 'tabular-nums',
            color: 'var(--text-tertiary)',
          }}>
            {pick?.side && pick?.line != null && pick.side.includes(String(Math.abs(pick.line)))
              ? pick.side
              : pick?.side && pick?.line != null
              ? `${pick.side} ${pick.line > 0 ? '+' : ''}${pick.line}`
              : pick?.side || '—'}
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--color-border)', padding: '20px',
          marginBottom: 'var(--space-md)',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '12px',
          }}>Process Review</div>
          <p style={{
            fontSize: 'var(--text-metric)', color: 'var(--text-secondary)', lineHeight: '1.7',
            marginBottom: 'var(--space-md)',
          }}>
            Market moved. Edge fell below threshold before tip-off. Capital preserved. No trade is a position.
          </p>

          <div style={{
            display: 'flex', justifyContent: 'space-around',
            padding: 'var(--space-md) 0', borderTop: '1px solid var(--color-border)',
          }}>
            <ContextStat value={`${pick?.edge_pct || '--'}%`} label="Edge at entry" />
            <ContextStat value={pick?.edge_at_close != null ? `${pick.edge_at_close}%` : '--'} label="Edge at withdrawal" muted />
            <ContextStat value="Protected" label="Action" muted />
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '12px',
          border: '1px solid var(--color-border)', padding: '12px var(--space-md)',
          marginBottom: 'var(--space-md)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)',
          }}>P&L</span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '15px', fontWeight: 700,
            fontVariantNumeric: 'tabular-nums',
            color: 'var(--text-secondary)',
          }}>0.0u</span>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--color-border)', padding: '20px',
          marginBottom: 'var(--space-md)',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '12px',
          }}>Discipline Framework</div>
          <p style={{
            fontSize: 'var(--text-metric)', color: 'var(--text-secondary)', lineHeight: '1.7',
          }}>
            Not every signal survives. The edge decides — not emotion. A withdrawal is the system protecting capital. Next signal when the edge is there.
          </p>
        </div>

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          border: '1px solid var(--color-border)', padding: '20px',
          marginBottom: 'var(--space-md)',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '12px',
          }}>Already Placed?</div>
          <p style={{
            fontSize: 'var(--text-metric)', color: 'var(--text-secondary)', lineHeight: '1.7',
          }}>
            If already wagered before withdrawal, treat as standalone decision. Tracked bet still graded on actual result. Withdrawal reflects edge no longer met threshold.
          </p>
        </div>

        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 'var(--text-caption)',
          color: 'var(--text-tertiary)', textAlign: 'center',
          padding: 'var(--space-md) 0 var(--space-sm)', lineHeight: '1.5',
        }}>
          Capital preservation is the discipline.
        </div>

        <p style={{
          fontSize: '10px', color: 'var(--text-tertiary)', textAlign: 'center',
          padding: '4px 0 var(--space-md)', lineHeight: '1.5', opacity: 0.6,
        }}>
          Past performance does not guarantee future results.
        </p>
      </div>
    </div>
  );
}

function fmtSpread(val) {
  if (val == null) return '—';
  const n = parseFloat(val);
  if (Number.isInteger(n)) return n > 0 ? `+${n}` : `${n}`;
  return n > 0 ? `+${n.toFixed(1)}` : `${n.toFixed(1)}`;
}

function CLVCard({ pick }) {
  const pickLine = pick?.line;
  const closingLine = pick?.closing_spread;
  const rawCLV = pick?.clv != null ? parseFloat(pick.clv) : null;
  const clvVal = rawCLV ?? (pickLine != null && closingLine != null ? parseFloat(pickLine) - parseFloat(closingLine) : null);

  if (pickLine == null && closingLine == null && clvVal == null) return null;

  const clvColor = clvVal == null ? 'var(--text-tertiary)'
    : clvVal > 0 ? 'var(--green-profit, var(--color-signal))'
    : clvVal < 0 ? 'var(--color-loss)'
    : 'var(--text-tertiary)';

  const borderAccent = clvVal == null ? 'var(--color-border)'
    : clvVal > 0 ? 'rgba(52,211,153,0.25)'
    : clvVal < 0 ? 'rgba(158,122,124,0.25)'
    : 'var(--color-border)';

  const bgAccent = clvVal == null ? 'var(--surface-1)'
    : clvVal > 0 ? 'linear-gradient(135deg, var(--surface-1) 0%, rgba(52,211,153,0.04) 100%)'
    : clvVal < 0 ? 'linear-gradient(135deg, var(--surface-1) 0%, rgba(158,122,124,0.04) 100%)'
    : 'var(--surface-1)';

  return (
    <div style={{
      background: bgAccent, borderRadius: '16px',
      border: `1px solid ${borderAccent}`, padding: '20px',
      marginBottom: 'var(--space-md)',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 'var(--text-label-size)', fontWeight: 700,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        color: 'var(--text-tertiary)', marginBottom: '14px',
      }}>Closing Line Value</div>

      {clvVal != null && (
        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '36px', fontWeight: 700,
            fontVariantNumeric: 'tabular-nums', lineHeight: 1,
            color: clvColor, marginBottom: '6px',
          }}>
            {clvVal > 0 ? '+' : ''}{clvVal.toFixed(1)}
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
            letterSpacing: '0.06em', color: 'var(--text-tertiary)',
          }}>
            {clvVal > 0 ? 'Points of closing line value' : clvVal < 0 ? 'Points behind the close' : 'Matched closing line'}
          </div>
        </div>
      )}

      <div style={{
        borderTop: '1px solid var(--color-border)',
        paddingTop: '14px',
        display: 'flex', flexDirection: 'column', gap: '8px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
            letterSpacing: '0.06em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)',
          }}>Pick Line</span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700,
            fontVariantNumeric: 'tabular-nums', color: 'var(--text-secondary)',
          }}>{fmtSpread(pickLine)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
            letterSpacing: '0.06em', textTransform: 'uppercase',
            color: 'var(--text-tertiary)',
          }}>Closing Line</span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '16px', fontWeight: 700,
            fontVariantNumeric: 'tabular-nums', color: 'var(--text-primary)',
          }}>{fmtSpread(closingLine)}</span>
        </div>
      </div>

      {clvVal != null && clvVal > 0 && (
        <div style={{
          marginTop: '14px', paddingTop: '12px',
          borderTop: '1px solid var(--color-border)',
          fontFamily: 'var(--font-mono)', fontSize: '11px',
          color: 'var(--text-tertiary)', lineHeight: 1.5, textAlign: 'center',
        }}>
          Model identified this line before the market moved. Positive CLV means the model was early and correct.
        </div>
      )}
    </div>
  );
}

function ContextStat({ value, label, muted }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 'var(--text-card-title)', fontWeight: 700,
        fontVariantNumeric: 'tabular-nums',
        color: muted ? 'var(--text-tertiary)' : 'var(--text-primary)', marginBottom: '4px',
      }}>{value}</div>
      <div style={{
        fontSize: '10px', color: 'var(--text-tertiary)',
        textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700,
      }}>{label}</div>
    </div>
  );
}

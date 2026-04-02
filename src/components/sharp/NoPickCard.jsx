import { InsightPassDayCTA } from './InsightsTab';

export default function NoPickCard({ data, sport, modelPhase, onInsightTap }) {
  const isCal = modelPhase === 'calibration';
  const sportName = (sport || 'nba').toUpperCase();

  return (
    <div style={{ padding: '0 4px' }}>
      <div style={{ textAlign: 'center', padding: '24px 0 32px' }}>
        <div style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: isCal ? '#3B82F6' : 'var(--text-tertiary)', opacity: isCal ? 0.8 : 0.5,
          margin: '0 auto 24px',
        }} />

        <h1 style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--text-label-size)',
          fontWeight: 700,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: 'var(--text-secondary)',
          marginBottom: '12px',
        }}>
          Market Intelligence Complete
        </h1>

        <h2 style={{
          fontFamily: 'var(--font-sans)',
          fontSize: '20px', fontWeight: 700,
          color: 'var(--text-primary)',
          marginBottom: '12px',
        }}>
          {isCal ? `No Qualifying ${sportName} Edge` : 'No Qualifying Signal'}
        </h2>

        <p style={{
          fontSize: 'var(--text-metric)',
          color: 'var(--text-secondary)',
          lineHeight: '1.55', marginBottom: '4px',
        }}>
          {data.games_analyzed > 0
              ? `${data.games_analyzed} games scanned, none above threshold.`
              : 'Model analysis complete.'}
        </p>
        <p style={{
          fontSize: 'var(--text-caption)',
          color: 'var(--text-tertiary)',
          lineHeight: '1.55',
        }}>
          Next scan: Tomorrow 10:00 AM EST
        </p>
      </div>

      {data.whatif?.side && data.whatif?.edge_pct != null && (
        <ClosestMiss whatif={data.whatif} />
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: 'var(--space-xl)' }}>
        {isCal ? (
          <>
            <InsightCard
              title="Restraint builds the edge"
              desc="Early-phase discipline. No forced edges. The model earns trust through selectivity."
            />
            <InsightCard
              title="Building the edge in public"
              desc="Every signal tracked from Day 1. No resets, no hiding. Full transparency."
            />
            <InsightCard
              title="Process over outcomes"
              desc="Calibration means proving the model before scaling it. This is how real edges are built."
            />
          </>
        ) : (
          <>
            <InsightCard
              title="Restraint is a feature"
              desc="Quiet days are intentional. Market efficient. No action required."
            />
            <InsightCard
              title="Selectivity beats volume"
              desc="Industry average: 78% of slates get action. SharpPicks: ~30%. That difference is the edge."
            />
            <InsightCard
              title="Process over outcomes"
              desc="All signals tracked publicly. No deletes. Confidence calibrated, not exaggerated."
            />
          </>
        )}
      </div>

      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px',
        marginBottom: 'var(--space-xl)',
      }}>
        <NopickStat value={data.picks_this_week ?? 2} label="Signals this week" />
        <NopickStat value={data.passes_this_week ?? 4} label="Passes this week" />
        <NopickStat value={`${data.selectivity ?? 33}%`} label="Selectivity" />
        <NopickStat value={data.days_per_bet ?? '3.2'} label="Days per signal" />
      </div>

      {onInsightTap && <InsightPassDayCTA onTap={onInsightTap} />}

      <p style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--text-caption)',
        color: 'var(--text-tertiary)',
        textAlign: 'center',
        marginTop: 'var(--space-lg)',
        letterSpacing: '0.04em',
      }}>Selective by design.</p>
    </div>
  );
}

function InsightCard({ title, desc }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      borderRadius: '14px',
      border: '1px solid var(--color-border)',
      padding: 'var(--space-md)',
    }}>
      <h3 style={{
        fontFamily: 'var(--font-sans)',
        fontSize: '15px', fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: 'var(--space-sm)',
      }}>{title}</h3>
      <p style={{
        fontSize: '13px',
        color: 'var(--text-secondary)',
        lineHeight: '1.55',
      }}>{desc}</p>
    </div>
  );
}

function NopickStat({ value, label }) {
  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      border: '1px solid var(--color-border)',
      borderRadius: '12px',
      padding: 'var(--space-md)',
      textAlign: 'center',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '22px', fontWeight: 700,
        fontVariantNumeric: 'tabular-nums',
        color: 'var(--text-primary)',
        marginBottom: '4px',
      }}>{value}</div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px', fontWeight: 700,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        color: 'var(--text-tertiary)',
      }}>{label}</div>
    </div>
  );
}

function ClosestMiss({ whatif }) {
  const mono = 'var(--font-mono)';
  const matchup = whatif.away_team && whatif.home_team
    ? `${whatif.away_team} @ ${whatif.home_team}` : null;
  const lineFmt = whatif.line != null
    ? (whatif.line > 0 ? `+${whatif.line}` : String(whatif.line)) : null;

  return (
    <div style={{
      backgroundColor: 'var(--surface-1)',
      border: '1px solid var(--color-border)',
      borderRadius: '14px',
      padding: 'var(--space-md)',
      marginBottom: 'var(--space-lg)',
    }}>
      <div style={{
        fontFamily: mono, fontSize: '10px', fontWeight: 700,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        color: 'var(--text-tertiary)', marginBottom: '10px',
      }}>Closest Miss</div>

      {matchup && (
        <div style={{
          fontFamily: 'var(--font-sans)', fontSize: '15px', fontWeight: 600,
          color: 'var(--text-primary)', marginBottom: '6px',
        }}>{matchup}</div>
      )}

      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '10px' }}>
        <MissStat label="Side" value={whatif.pick_side || whatif.side} />
        {lineFmt && <MissStat label="Line" value={lineFmt} />}
        <MissStat label="Edge" value={`${whatif.edge_pct}%`} accent />
        {whatif.cover_prob != null && (
          <MissStat label="Cover Prob" value={`${(whatif.cover_prob * 100).toFixed(0)}%`} />
        )}
      </div>

      <div style={{
        fontFamily: mono, fontSize: '12px', color: 'var(--text-tertiary)',
        lineHeight: '1.5',
      }}>
        Below the 3% qualification threshold. The filter did its job.
      </div>
    </div>
  );
}

function MissStat({ label, value, accent }) {
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
        letterSpacing: '0.06em', textTransform: 'uppercase',
        color: 'var(--text-tertiary)', marginBottom: '2px',
      }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700,
        color: accent ? '#D4A843' : 'var(--text-primary)',
        fontVariantNumeric: 'tabular-nums',
      }}>{value}</div>
    </div>
  );
}

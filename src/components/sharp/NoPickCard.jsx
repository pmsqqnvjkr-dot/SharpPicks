import { InsightPassDayCTA } from './InsightsTab';

const blue = '#4A8EC2';
const cardBg = '#0C1018';
const descBg = '#070C12';
const border = '#2A3A50';
const titleColor = '#E8EAF0';
const secondaryColor = '#9EAABB';
const statLabelColor = '#A0AABB';
const statValColor = '#E2E4E8';
const badgeText = '#A8C8E8';
const badgeBg = '#0E1E30';
const badgeBorder = '#2A5070';
const mono = "'JetBrains Mono', var(--font-mono), monospace";
const serif = "'IBM Plex Serif', var(--font-serif), serif";
const sans = "'Inter', var(--font-sans), sans-serif";

export default function NoPickCard({ data, sport, modelPhase, onInsightTap }) {
  const isCal = modelPhase === 'calibration';
  const sportName = (sport || 'nba').toUpperCase();
  const today = new Date();
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const dateStr = `${months[today.getMonth()]} ${today.getDate()}`;

  const gamesAnalyzed = data.games_analyzed || 0;
  const edgesDetected = data.edges_detected || 0;
  const signalsCount = data.picks_this_week || 0;
  const topEdge = data.closest_edge != null ? `${data.closest_edge}%` : '0%';

  return (
    <div style={{ padding: '0 4px' }}>
      {/* Main card */}
      <div style={{
        background: cardBg,
        border: `1.5px solid ${border}`,
        borderRadius: '16px',
        padding: '28px',
        position: 'relative',
        overflow: 'hidden',
        marginBottom: '16px',
      }}>
        {/* Top accent bar */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
          background: `linear-gradient(90deg, ${blue}, transparent)`,
          borderRadius: '16px 16px 0 0',
        }} />

        {/* Header: icon + title + badge */}
        <div style={{
          display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
          marginBottom: '22px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <SignalBars />
            <div>
              <div style={{
                fontFamily: sans, fontSize: '17px', fontWeight: 600,
                color: titleColor, marginBottom: '2px',
              }}>
                {isCal ? `No Qualifying ${sportName} Edge` : 'No Qualifying Edge'}
              </div>
              <div style={{
                fontFamily: sans, fontSize: '12px', color: secondaryColor,
              }}>
                {dateStr} · {sportName}
              </div>
            </div>
          </div>
          <span style={{
            background: badgeBg,
            border: `1.5px solid ${badgeBorder}`,
            borderRadius: '6px',
            padding: '5px 12px',
            fontFamily: mono, fontSize: '10px', fontWeight: 700,
            letterSpacing: '0.1em', textTransform: 'uppercase',
            color: badgeText,
            flexShrink: 0,
          }}>PASS</span>
        </div>

        {/* Description block */}
        <div style={{
          background: descBg,
          borderRadius: '8px',
          padding: '14px 16px',
          marginBottom: '22px',
        }}>
          <div style={{
            fontFamily: "'Courier New', monospace",
            fontSize: '13px', color: secondaryColor,
            lineHeight: '1.5',
          }}>
            {gamesAnalyzed > 0
              ? `${gamesAnalyzed} game${gamesAnalyzed !== 1 ? 's' : ''} scanned. ${edgesDetected} edge${edgesDetected !== 1 ? 's' : ''} detected,\nzero cleared the signal threshold.`
              : (data.pass_reason && data.pass_reason.toLowerCase().includes('off day'))
                ? `No ${sportName} games scheduled today.`
                : 'Model analysis complete. No games met the signal threshold.'}
          </div>
        </div>

        {/* Stats grid */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr',
          gap: '1px', background: border,
          borderRadius: '0', overflow: 'hidden',
          marginBottom: '20px',
        }}>
          <StatCell value={gamesAnalyzed} label="Games" />
          <StatCell value={edgesDetected} label="Edges" />
          <StatCell value={signalsCount} label="Signals" />
          <StatCell value={topEdge} label="Top Edge" />
        </div>

        {/* Footer: tagline + dots */}
        <div style={{
          borderTop: `1px solid ${border}`,
          paddingTop: '16px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div style={{
            fontFamily: sans, fontSize: '12px', fontStyle: 'italic',
            color: secondaryColor,
          }}>Selective by design.</div>
          <div style={{ display: 'flex', gap: '5px' }}>
            {[0,1,2,3].map(i => (
              <span key={i} style={{
                width: '6px', height: '6px', borderRadius: '50%',
                background: i === 2 ? blue : border,
              }} />
            ))}
          </div>
        </div>
      </div>

      {/* Closest miss */}
      {data.whatif?.side && data.whatif?.edge_pct != null && (
        <ClosestMiss whatif={data.whatif} />
      )}

      {/* Insight cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: 'var(--space-xl)' }}>
        {isCal ? (
          <>
            <InsightCard title="Restraint builds the edge" desc="Early-phase discipline. No forced edges. The model earns trust through selectivity." />
            <InsightCard title="Building the edge in public" desc="Every signal tracked from Day 1. No resets, no hiding. Full transparency." />
            <InsightCard title="Process over outcomes" desc="Calibration means proving the model before scaling it. This is how real edges are built." />
          </>
        ) : (
          <>
            <InsightCard title="Restraint is a feature" desc="Quiet days are intentional. Market efficient. No action required." />
            <InsightCard title="Selectivity beats volume" desc="Industry average: 78% of slates get action. SharpPicks: ~30%. That difference is the edge." />
            <InsightCard title="Process over outcomes" desc="All signals tracked publicly. No deletes. Confidence calibrated, not exaggerated." />
          </>
        )}
      </div>

      {onInsightTap && <InsightPassDayCTA onTap={onInsightTap} />}
    </div>
  );
}

function SignalBars() {
  const heights = [8, 14, 20];
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-end', gap: '4px',
      height: '20px', flexShrink: 0,
    }}>
      {heights.map((h, i) => (
        <div key={i} style={{
          width: '4px', height: `${h}px`,
          background: `rgba(74,142,194,0.35)`,
          borderRadius: '2px',
        }} />
      ))}
    </div>
  );
}

function StatCell({ value, label }) {
  return (
    <div style={{
      background: cardBg,
      padding: '16px 8px 14px',
      textAlign: 'center',
    }}>
      <div style={{
        fontFamily: mono, fontSize: '22px', fontWeight: 600,
        color: statValColor, fontVariantNumeric: 'tabular-nums',
        marginBottom: '4px',
      }}>{value}</div>
      <div style={{
        fontFamily: mono, fontSize: '10px', fontWeight: 700,
        letterSpacing: '0.12em', textTransform: 'uppercase',
        color: statLabelColor,
      }}>{label}</div>
    </div>
  );
}

function InsightCard({ title, desc }) {
  return (
    <div style={{
      background: cardBg,
      borderRadius: '14px',
      border: `1.5px solid ${border}`,
      padding: '18px',
    }}>
      <h3 style={{
        fontFamily: sans, fontSize: '15px', fontWeight: 600,
        color: titleColor, marginBottom: '8px',
      }}>{title}</h3>
      <p style={{
        fontSize: '13px', color: secondaryColor, lineHeight: '1.55',
      }}>{desc}</p>
    </div>
  );
}

function ClosestMiss({ whatif }) {
  const matchup = whatif.away_team && whatif.home_team
    ? `${whatif.away_team} @ ${whatif.home_team}` : null;
  const lineFmt = whatif.line != null
    ? (whatif.line > 0 ? `+${whatif.line}` : String(whatif.line)) : null;

  return (
    <div style={{
      background: cardBg,
      border: `1.5px solid ${border}`,
      borderRadius: '14px',
      padding: '18px',
      marginBottom: '16px',
    }}>
      <div style={{
        fontFamily: mono, fontSize: '10px', fontWeight: 700,
        letterSpacing: '0.08em', textTransform: 'uppercase',
        color: statLabelColor, marginBottom: '10px',
      }}>Closest Miss</div>

      {matchup && (
        <div style={{
          fontFamily: sans, fontSize: '15px', fontWeight: 600,
          color: titleColor, marginBottom: '6px',
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
        fontFamily: mono, fontSize: '12px', color: secondaryColor,
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
        fontFamily: mono, fontSize: '10px', fontWeight: 600,
        letterSpacing: '0.06em', textTransform: 'uppercase',
        color: statLabelColor, marginBottom: '2px',
      }}>{label}</div>
      <div style={{
        fontFamily: mono, fontSize: '14px', fontWeight: 700,
        color: accent ? '#D4A843' : titleColor,
        fontVariantNumeric: 'tabular-nums',
      }}>{value}</div>
    </div>
  );
}

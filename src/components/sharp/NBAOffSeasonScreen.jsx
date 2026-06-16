// NBA Off-Season screen. Replaces normal PicksTab content for sport='nba'
// whenever launch_config.sports.nba.in_season is false (so this screen
// auto-shows after the 2025-26 Finals end and turns off when the 2026-27
// season window opens). Steel state token throughout.
//
// Sections (per docs/mockups/empty-state-screens-nba-nfl.html left frame):
//   1. Date row + steel NBA OFF-SEASON pill
//   2. Hero ("Season closed.")
//   3. Countdown card to opening night
//   4. Season ledger: CLV BEAT / NET / RECORD + strip + tagline
//   5. The Road Back timeline (config-driven)
//   6. The Market Doesn't Close (live in-season sports)
//   7. Model status narrative card (IN THE LAB pill)
//   8. Off-Season Reading (FurtherReadingCard, first journal article)
//   9. Sharp Principle + disclaimer

import { useMemo } from 'react';
import { useApi } from '../../hooks/useApi';
import { useLaunchConfig } from '../../hooks/useLaunchConfig';
import { useSport } from '../../hooks/useSport';
import StatePill from '../empty-state/StatePill';
import Timeline from '../empty-state/Timeline';
import NarrativeCard from '../empty-state/NarrativeCard';
import { NEUTRAL_TOKENS, getStateTokens } from '../empty-state/stateTokens';
import { pickPrimaryArticle } from '../../utils/articleRotation';
import FurtherReadingCard from '../signals/shared/FurtherReadingCard';

const STATE = 'steel';
const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
const WEEKDAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];

// Parse ISO yyyy-mm-dd as a calendar date in the user's local TZ. Avoids
// the new Date('2026-06-23') midnight-UTC trap that bumps the day to
// June 22 in PT/MT/CT.
function parseIsoLocal(iso) {
  if (!iso || typeof iso !== 'string') return null;
  const [y, m, d] = iso.slice(0, 10).split('-').map((x) => parseInt(x, 10));
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d);
}

function formatTodayMono() {
  const now = new Date();
  return `${WEEKDAYS[now.getDay()]} · ${MONTHS[now.getMonth()]} ${now.getDate()}`;
}

function formatRangeMono(startIso, endIso) {
  const start = parseIsoLocal(startIso);
  if (!start) return '';
  const startStr = `${MONTHS[start.getMonth()]} ${start.getDate()}`;
  if (!endIso) return startStr;
  const end = parseIsoLocal(endIso);
  if (!end) return startStr;
  if (end.getMonth() === start.getMonth()) {
    return `${startStr}-${end.getDate()}`;
  }
  return `${startStr} - ${MONTHS[end.getMonth()]} ${end.getDate()}`;
}

function daysUntilLocal(iso) {
  const target = parseIsoLocal(iso);
  if (!target) return null;
  const today = new Date();
  const todayMidnight = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const diffMs = target.getTime() - todayMidnight.getTime();
  return Math.max(0, Math.round(diffMs / (24 * 60 * 60 * 1000)));
}

function formatOpeningNightSub(iso) {
  const d = parseIsoLocal(iso);
  if (!d) return '';
  return `OPENING NIGHT · ${WEEKDAYS[d.getDay()]} ${MONTHS[d.getMonth()]} ${d.getDate()} · ${d.getFullYear()}`;
}

const SPORT_LABEL = { mlb: 'MLB', wnba: 'WNBA' };

function SectionHead({ label, link }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
      marginBottom: '12px',
    }}>
      <div style={{
        fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '10.5px',
        letterSpacing: '0.2em', color: NEUTRAL_TOKENS.text3, fontWeight: 500,
      }}>{label}</div>
      {link}
    </div>
  );
}

function MarketRow({ sport, label, gameCount, onView }) {
  const green = getStateTokens('green');
  return (
    <div style={{
      background: NEUTRAL_TOKENS.card,
      border: `1px solid ${NEUTRAL_TOKENS.hairline}`,
      borderRadius: '10px',
      padding: '14px 16px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: '10px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: green.color, boxShadow: `0 0 0 4px ${green.soft}`,
        }} />
        <div>
          <div style={{
            fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '12.5px',
            fontWeight: 600, letterSpacing: '0.14em', color: NEUTRAL_TOKENS.text,
          }}>{label}</div>
          <div style={{
            fontSize: '11.5px', color: NEUTRAL_TOKENS.text3, marginTop: '2px',
          }}>
            {gameCount != null
              ? `Slate today · ${gameCount} game${gameCount === 1 ? '' : 's'} on the board`
              : 'In season'}
          </div>
        </div>
      </div>
      <button
        type="button"
        onClick={onView}
        style={{
          fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '10px',
          letterSpacing: '0.14em', fontWeight: 600,
          color: green.color, border: `1px solid ${green.border}`,
          background: green.soft, padding: '7px 14px', borderRadius: '6px',
          cursor: 'pointer',
        }}
      >
        VIEW SLATE
      </button>
    </div>
  );
}

export default function NBAOffSeasonScreen({ onNavigate }) {
  const accent = getStateTokens(STATE);
  const { setSport } = useSport();
  const { config } = useLaunchConfig();
  const { data: stats } = useApi('/public/stats?sport=nba');
  const { data: insightsData } = useApi('/insights?limit=8&rotate=1&sport=nba');

  const nba = config?.sports?.nba;
  const openingIso = nba?.opening_night?.date;
  const days = daysUntilLocal(openingIso);
  const openingSub = formatOpeningNightSub(openingIso);
  const dateLine = formatTodayMono();

  const timelineItems = useMemo(() => {
    const list = nba?.road_back || [];
    return list.map((row) => ({
      id: row.id,
      date: formatRangeMono(row.date_start, row.date_end),
      title: row.title,
      pill: row.pill,
      note: row.note,
      isFinal: !!row.is_final,
    }));
  }, [nba]);

  const inSeasonSports = useMemo(() => {
    const sports = config?.sports || {};
    return ['mlb', 'wnba'].filter((k) => sports[k]?.in_season === true);
  }, [config]);

  const article = useMemo(() => {
    return pickPrimaryArticle(insightsData?.insights || [], 'nba');
  }, [insightsData]);

  // Season ledger numbers. /api/public/stats is all-time today; NBA picks
  // only exist post-Feb-2026 calibration so all-time == 2025-26 for now.
  // When the 2026-27 season starts grading, scope this by published_at
  // range to keep the 2025-26 label honest.
  const clvBeat = typeof stats?.clv_beat_rate === 'number' ? stats.clv_beat_rate : null;
  const netUnits = typeof stats?.units === 'number' ? stats.units : (typeof stats?.pnl === 'number' ? stats.pnl : null);
  const wins = stats?.wins;
  const losses = stats?.losses;
  const recordStr = (typeof wins === 'number' && typeof losses === 'number') ? `${wins}-${losses}` : null;
  const signalsIssued = stats?.total_picks;
  const passDays = stats?.total_passes;
  const selectivity = typeof stats?.selectivity === 'number' ? stats.selectivity : null;

  return (
    <div style={{ padding: '22px 20px 0', color: NEUTRAL_TOKENS.text, fontFamily: NEUTRAL_TOKENS.fontSans }}>
      {/* Date row */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '18px',
      }}>
        <div style={{
          fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '11px',
          letterSpacing: '0.22em', color: getStateTokens('green').color, fontWeight: 500,
        }}>{dateLine}</div>
        <StatePill state={STATE}>NBA OFF-SEASON</StatePill>
      </div>

      {/* Hero */}
      <h1 style={{
        fontFamily: NEUTRAL_TOKENS.fontSerif, fontWeight: 600,
        fontSize: '34px', lineHeight: 1.12, margin: '0 0 14px 0',
        letterSpacing: '-0.01em',
      }}>Season closed.</h1>
      <p style={{
        fontSize: '14.5px', lineHeight: 1.6, color: NEUTRAL_TOKENS.text2,
        margin: '0 0 22px 0',
      }}>
        The 2025–26 NBA season is settled. Every signal graded, nothing removed.{' '}
        <strong style={{ color: NEUTRAL_TOKENS.text, fontWeight: 600 }}>
          This isn't a pass day.
        </strong>{' '}
        It's the calendar. The model is in the lab until opening night.
      </p>

      {/* Countdown */}
      <div style={{
        background: NEUTRAL_TOKENS.card,
        border: `1px solid ${NEUTRAL_TOKENS.hairline}`,
        borderRadius: '10px', padding: '16px 18px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '8px',
      }}>
        <div style={{
          fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '10px',
          letterSpacing: '0.2em', color: NEUTRAL_TOKENS.text3,
        }}>NEXT NBA SLATE OPENS IN</div>
        <div style={{
          fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '21px', fontWeight: 600,
        }}>
          {days != null ? days : '—'}
          <span style={{
            fontSize: '12px', color: NEUTRAL_TOKENS.text3, fontWeight: 400, marginLeft: '1px',
          }}>d</span>
        </div>
      </div>
      <div style={{
        fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '10px',
        letterSpacing: '0.06em', color: NEUTRAL_TOKENS.text4,
        textAlign: 'right', margin: '0 2px 26px',
      }}>{openingSub}</div>

      {/* Season ledger */}
      <SectionHead label="2025–26 SEASON LEDGER" />
      <div style={{
        background: NEUTRAL_TOKENS.card,
        border: `1px solid ${NEUTRAL_TOKENS.hairline}`,
        borderRadius: '12px', overflow: 'hidden', marginBottom: '28px',
      }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr' }}>
          <LedgerCell value={clvBeat != null ? `${clvBeat.toFixed(1)}` : null} unit="%" label="CLV BEAT" tone="green" />
          <LedgerCell
            value={netUnits != null ? `${netUnits >= 0 ? '+' : ''}${netUnits.toFixed(1)}` : null}
            unit="u" label="NET" tone={netUnits != null && netUnits < 0 ? 'rose' : 'green'} bordered
          />
          <LedgerCell value={recordStr} label="RECORD" bordered />
        </div>
        <div style={{
          borderTop: `1px solid ${NEUTRAL_TOKENS.hairline}`,
          padding: '11px 16px', textAlign: 'center',
          fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '10.5px',
          letterSpacing: '0.08em', color: NEUTRAL_TOKENS.text4,
        }}>
          {signalsIssued != null && passDays != null && selectivity != null
            ? `${signalsIssued} signals issued · ${passDays} pass days · ${selectivity.toFixed(1)}% selectivity`
            : 'Loading season aggregates...'}
        </div>
        <div style={{
          borderTop: `1px solid ${NEUTRAL_TOKENS.hairline}`,
          padding: '11px 16px', display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', background: 'rgba(90,158,114,0.05)',
        }}>
          <div style={{
            fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '10px',
            letterSpacing: '0.1em', color: getStateTokens('green').color,
          }}>EVERY SIGNAL TRACKED. NOTHING REMOVED.</div>
        </div>
      </div>

      {/* Road Back timeline */}
      <SectionHead label="THE ROAD BACK" />
      <div style={{ marginBottom: '28px' }}>
        <Timeline state={STATE} items={timelineItems} />
      </div>

      {/* The Market Doesn't Close */}
      {inSeasonSports.length > 0 && (
        <>
          <SectionHead label="THE MARKET DOESN'T CLOSE" />
          <div style={{ marginBottom: '28px' }}>
            {inSeasonSports.map((key) => (
              <MarketRow
                key={key}
                sport={key}
                label={SPORT_LABEL[key]}
                gameCount={null}
                onView={() => setSport(key)}
              />
            ))}
          </div>
        </>
      )}

      {/* Model status narrative */}
      <div style={{ marginBottom: '28px' }}>
        <NarrativeCard
          state={STATE}
          eyebrow="MODEL STATUS"
          pill="IN THE LAB"
          title="The off-season retrain is underway."
        >
          The full 2025–26 ledger goes back through the model. Features are audited,
          weak ones are cut, and nothing ships until calibration clears. The version
          you see on opening night will have earned it.
        </NarrativeCard>
      </div>

      {/* Off-Season Reading */}
      {article && (
        <>
          <SectionHead
            label="OFF-SEASON READING"
            link={
              <a
                href="#"
                onClick={(e) => { e.preventDefault(); if (onNavigate) onNavigate('insights'); }}
                style={{
                  fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '10.5px',
                  letterSpacing: '0.14em', color: '#6E9BD8', fontWeight: 600,
                  textDecoration: 'none',
                }}
              >
                JOURNAL &rsaquo;
              </a>
            }
          />
          <div style={{ marginBottom: '24px' }}>
            <FurtherReadingCard
              title={article.title}
              snippet={(article.content || '').split('\n\n')[0]?.slice(0, 200) || ''}
              readMinutes={article.reading_time_minutes || article.read_time || 4}
              publishedDate={article.published_at || article.created_at || ''}
              category={article.category || 'Season Review'}
              source="Sharp Journal"
              onClick={() => onNavigate && onNavigate('insights', null, { insight: article })}
            />
          </div>
        </>
      )}

      {/* Sharp Principle */}
      <div style={{
        borderLeft: `2px solid ${NEUTRAL_TOKENS.text4}`,
        background: NEUTRAL_TOKENS.card,
        borderRadius: '0 10px 10px 0',
        padding: '16px 18px', marginBottom: '30px',
      }}>
        <div style={{
          fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '9.5px',
          letterSpacing: '0.22em', color: NEUTRAL_TOKENS.text3, marginBottom: '8px',
        }}>SHARP PRINCIPLE</div>
        <div style={{
          fontFamily: NEUTRAL_TOKENS.fontSerif, fontSize: '15px',
          lineHeight: 1.5, color: NEUTRAL_TOKENS.text,
        }}>The work between games is the work.</div>
      </div>

      {/* Disclaimer */}
      <div style={{
        fontSize: '10.5px', color: NEUTRAL_TOKENS.text4,
        textAlign: 'center', lineHeight: 1.55,
        padding: '0 24px', marginBottom: '26px',
      }}>
        For entertainment and informational purposes. Past results do not guarantee future performance.
      </div>
    </div>
  );
}

function LedgerCell({ value, unit, label, tone, bordered }) {
  let color = NEUTRAL_TOKENS.text;
  if (tone === 'green') color = getStateTokens('green').color;
  if (tone === 'rose') color = '#C4868A';
  return (
    <div style={{
      padding: '20px 8px 16px', textAlign: 'center',
      borderLeft: bordered ? `1px solid ${NEUTRAL_TOKENS.hairline}` : 'none',
    }}>
      <div style={{
        fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '22px',
        fontWeight: 600, letterSpacing: '-0.01em', color,
      }}>
        {value != null ? value : '—'}
        {value != null && unit && (
          <span style={{ fontSize: '13px', fontWeight: 400 }}>{unit}</span>
        )}
      </div>
      <div style={{
        fontFamily: NEUTRAL_TOKENS.fontMono, fontSize: '9.5px',
        letterSpacing: '0.2em', color: NEUTRAL_TOKENS.text3, marginTop: '7px',
      }}>{label}</div>
    </div>
  );
}

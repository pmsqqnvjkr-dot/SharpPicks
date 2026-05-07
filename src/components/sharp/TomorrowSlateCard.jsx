// Tomorrow's Slate preview card. Used in PicksTab post-midnight ET window
// to give a quick look-ahead at the next day's games before the model run
// publishes signals. Source: docs mockup approved 2026-05-07.
//
// Pure presentational; PicksTab supplies the games array (already
// fetched in the night-mode useEffect) and the publish-time label.
// The "View all" button toggles in-place expansion to show all games.

import { useState } from 'react';

const SP = {
  surface: '#121725',
  border: 'rgba(255, 255, 255, 0.08)',
  border2: 'rgba(255, 255, 255, 0.05)',
  green: '#5A9E72',
  text: '#E8EAED',
  text2: 'rgba(232, 234, 237, 0.7)',
  text3: 'rgba(232, 234, 237, 0.5)',
  text4: 'rgba(232, 234, 237, 0.35)',
  fontMono: "'JetBrains Mono', 'Menlo', ui-monospace, monospace",
  fontSerif: "'IBM Plex Serif', Georgia, serif",
};

function fmtTimeET(timeStr) {
  if (!timeStr) return '';
  // Try ISO timestamp first
  if (typeof timeStr === 'string' && timeStr.includes('T')) {
    try {
      const d = new Date(timeStr);
      if (!Number.isNaN(d.getTime())) {
        return new Intl.DateTimeFormat('en-US', {
          timeZone: 'America/New_York',
          hour: 'numeric', minute: '2-digit', hour12: true,
        }).format(d).replace(' ', ' ') + ' ET';
      }
    } catch { /* fallthrough */ }
  }
  // Already-formatted string (e.g. "7:30 PM ET")
  return String(timeStr);
}

function fmtSlateDate(iso) {
  if (!iso) return '';
  try {
    // Accept either YYYY-MM-DD or full ISO; normalize to date-only.
    const ymd = String(iso).slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(ymd)) return '';
    const d = new Date(`${ymd}T12:00:00Z`);
    if (Number.isNaN(d.getTime())) return '';
    return new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      weekday: 'short', month: 'short', day: 'numeric',
    }).format(d).toUpperCase();
  } catch { return ''; }
}

export default function TomorrowSlateCard({ games, sport = 'nba', publishTimeLabel, slateDate, onViewAll }) {
  const [expanded, setExpanded] = useState(false);
  const sportLabel = (sport || 'nba').toUpperCase();
  const total = games?.length || 0;
  const previewCount = expanded ? total : 5;
  const previewGames = (games || []).slice(0, previewCount);
  const remaining = Math.max(0, total - previewGames.length);
  const slateDateLabel = fmtSlateDate(slateDate);
  const handleToggle = () => {
    setExpanded((v) => !v);
    if (typeof onViewAll === 'function') onViewAll();
  };

  return (
    <div style={{ marginBottom: '22px' }}>
      <div style={{
        fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
        letterSpacing: '0.24em', textTransform: 'uppercase', color: SP.green,
        marginBottom: '12px', paddingLeft: '4px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
      }}>
        <span>
          Tomorrow’s slate
          {slateDateLabel && (
            <span style={{ color: SP.text4, marginLeft: '8px', letterSpacing: '0.04em', fontWeight: 400 }}>
              {slateDateLabel}
            </span>
          )}
        </span>
        {publishTimeLabel && (
          <span style={{ color: SP.text4, letterSpacing: '0.16em' }}>
            EDGES PUBLISH {publishTimeLabel}
          </span>
        )}
      </div>

      <div style={{
        background: SP.surface,
        border: `1px solid ${SP.border}`,
        borderRadius: '14px',
        padding: '20px 22px',
      }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: '14px',
        }}>
          <span style={{
            fontFamily: SP.fontSerif, fontSize: '16px', fontWeight: 600, color: SP.text,
          }}>
            {total > 0 ? `${total} ${sportLabel} game${total === 1 ? '' : 's'}` : `No ${sportLabel} games scheduled`}
          </span>
          {total > 0 && (
            <span style={{ fontFamily: SP.fontMono, fontSize: '11px', color: SP.text3, letterSpacing: '0.04em' }}>
              PRE-MODEL
            </span>
          )}
        </div>

        {previewGames.length > 0 ? (
          <>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {previewGames.map((g, i) => {
                const away = g.away || g.away_team || '?';
                const home = g.home || g.home_team || '?';
                const time = fmtTimeET(g.time || g.game_time || g.start_time);
                return (
                  <div key={`${away}-${home}-${i}`} style={{
                    display: 'grid', gridTemplateColumns: '1fr auto', gap: '12px',
                    alignItems: 'center', padding: '12px 0',
                    borderTop: `1px solid ${SP.border2}`,
                  }}>
                    <span style={{ fontSize: '14px', color: SP.text, fontWeight: 500 }}>
                      {away} @ {home}
                    </span>
                    <span style={{
                      fontFamily: SP.fontMono, fontSize: '11px', color: SP.text3, letterSpacing: '0.04em',
                    }}>{time || '—'}</span>
                  </div>
                );
              })}
            </div>

            {total > 5 && (
              <div style={{
                marginTop: '14px', paddingTop: '14px',
                borderTop: `1px solid ${SP.border2}`,
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}>
                <span style={{
                  fontFamily: SP.fontMono, fontSize: '10px', color: SP.text4,
                  letterSpacing: '0.16em', textTransform: 'uppercase',
                }}>
                  {expanded ? 'Full slate' : `+ ${remaining} more`}
                </span>
                <button
                  onClick={handleToggle}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    fontFamily: SP.fontMono, fontSize: '10px', fontWeight: 500,
                    letterSpacing: '0.16em', textTransform: 'uppercase',
                    color: SP.green, padding: 0,
                  }}
                >{expanded ? 'Show less ↑' : 'View all →'}</button>
              </div>
            )}
          </>
        ) : (
          <div style={{
            fontSize: '12px', lineHeight: 1.5, color: SP.text3, marginTop: '4px',
          }}>
            Tomorrow’s schedule populates after the overnight games-collect cron.
          </div>
        )}
      </div>
    </div>
  );
}

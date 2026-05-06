import { useState } from 'react';

// v4.3 Pass Day. Consolidated single-card hero replaces the seven-card
// stack of the previous design (HeroCard + CapitalCard + SharpPrinciple +
// FurtherReadingCard + CountdownCard + MIPill + ComplianceFooter), all
// in one calmer surface. Source: mockup approved 2026-05-06.
//
// Prop interface preserved so PicksTab.jsx wiring at line ~1383 still works.
// The shared sub-components in src/components/signals/shared/ are no longer
// used here; they remain in the tree for any other consumer.

const PRINCIPLES = [
  `Pass days are not missed opportunities. They are proof the system is working.`,
  `The hardest edge to find is the patience to wait for one.`,
  `A bad bet at +EV beats a good bet at -EV. The market doesn't care which felt better.`,
  `Process over outcome. Always. Outcomes are noise; process is signal.`,
  `Discipline is not doing more. It is doing less, better.`,
  `Capital preserved is capital compounding. Zero risk on a non-edge is a win.`,
];

const FALLBACK_ARTICLES = [
  {
    category: 'Field Guide',
    readMinutes: 3,
    publishedDate: 'Mar 18, 2026',
    title: 'Shadow mode: how we test a model before you see it.',
    snippet: 'Before any model goes live on SharpPicks, it runs in shadow mode. Shadow mode means the model generates picks in real time against real lines, but those picks are tracked privately for at least 60 days before any user sees them.',
    source: 'How it works',
  },
];

function dateSeedIndex(arrayLength) {
  if (!arrayLength || arrayLength <= 0) return 0;
  try {
    const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
    let hash = 0;
    for (let i = 0; i < today.length; i++) hash = (hash * 31 + today.charCodeAt(i)) | 0;
    return Math.abs(hash) % arrayLength;
  } catch {
    return 0;
  }
}

function SectionEyebrow({ title, meta }) {
  return (
    <div style={{
      fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
      fontSize: '10px',
      fontWeight: 500,
      letterSpacing: '0.24em',
      textTransform: 'uppercase',
      color: 'var(--sp-green, #5A9E72)',
      marginBottom: '12px',
      paddingLeft: '4px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'baseline',
    }}>
      <span>{title}</span>
      {meta && (
        <span style={{ color: 'var(--sp-text-4, rgba(232, 234, 237, 0.35))', letterSpacing: '0.04em' }}>
          {meta}
        </span>
      )}
    </div>
  );
}

export default function PassDay({
  date = '',
  sport = 'NBA',
  gamesScanned = 0,
  signalsIssued = 0,
  // eslint-disable-next-line no-unused-vars
  tracked = 0,
  topEdgePct = 0,
  thresholdPct = 8.0,
  // eslint-disable-next-line no-unused-vars
  capitalPreservedUsd = 100,
  nextWindow = { hours: 0, minutes: 0, openLocal: '' },
  elapsedPct = 38,
  // eslint-disable-next-line no-unused-vars
  verdictText = '',
  marketReport,
  furtherReading,
  furtherReadings,
  onOpenMarketReport,
}) {
  const articles = (furtherReadings && furtherReadings.length > 0)
    ? furtherReadings
    : (furtherReading ? [furtherReading] : FALLBACK_ARTICLES);

  const [principleIdx, setPrincipleIdx] = useState(() => dateSeedIndex(PRINCIPLES.length));
  const [articleIdx] = useState(() => dateSeedIndex(articles.length));
  const article = articles[articleIdx];

  const dateUpper = (date || '').toUpperCase();
  const sportUpper = (sport || 'NBA').toUpperCase();
  const gap = Math.max(0, Number(thresholdPct) - Number(topEdgePct));

  const edgeCount = marketReport?.edge_distribution
    ? (marketReport.edge_distribution.strong || 0)
      + (marketReport.edge_distribution.moderate || 0)
      + (marketReport.edge_distribution.weak || 0)
    : (marketReport?.edge_count || 0);
  const signals = signalsIssued || 0;
  const density = gamesScanned > 0 ? Math.round((signals / gamesScanned) * 100) : 0;
  const mei = marketReport?.mei != null
    ? Math.round(marketReport.mei)
    : (marketReport?.market_efficiency_index != null ? Math.round(marketReport.market_efficiency_index) : null);
  const regimeLabel = marketReport?.regime_label || marketReport?.regime || (edgeCount === 0 ? 'Quiet regime' : 'Active regime');
  const miUpdated = marketReport?.last_updated_label || marketReport?.updated_label || '';

  // Compact countdown like "14h 47m"
  const countdown = `${nextWindow.hours || 0}h ${String(nextWindow.minutes || 0).padStart(2, '0')}m`;
  const progressPct = Math.max(0, Math.min(100, Number(elapsedPct) || 0));

  return (
    <div style={{ padding: 0 }}>
      <SectionEyebrow
        title="Today's read"
        meta={`${dateUpper} · ${gamesScanned} GAME${gamesScanned === 1 ? '' : 'S'} SCANNED`}
      />

      <div style={{
        background: 'var(--sp-surface, #121725)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '16px',
        overflow: 'hidden',
        position: 'relative',
        marginBottom: '22px',
      }}>
        <div style={{
          position: 'absolute',
          top: 0,
          left: '20px',
          right: '20px',
          height: '2px',
          background: 'linear-gradient(90deg, transparent, var(--sp-green, #5A9E72) 20%, var(--sp-green, #5A9E72) 80%, transparent)',
          opacity: 0.5,
        }} />

        <div style={{ padding: '24px 24px 20px' }}>
          <div style={{
            fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
            fontSize: '10px',
            fontWeight: 500,
            letterSpacing: '0.22em',
            textTransform: 'uppercase',
            color: 'var(--sp-blue, #4F86F7)',
            marginBottom: '16px',
          }}>
            Capital preserved
          </div>
          <h1 style={{
            fontFamily: '"IBM Plex Serif", Georgia, serif',
            fontSize: '24px',
            fontWeight: 600,
            color: 'var(--sp-text, #E8EAED)',
            lineHeight: 1.25,
            letterSpacing: '-0.005em',
            marginBottom: '12px',
          }}>
            No signal cleared the threshold today.
          </h1>
          <p style={{
            fontSize: '14px',
            lineHeight: 1.55,
            color: 'var(--sp-text-2, rgba(232, 234, 237, 0.7))',
            marginBottom: 0,
          }}>
            The model scanned{' '}
            <strong style={{ color: 'var(--sp-text, #E8EAED)', fontWeight: 500 }}>
              {gamesScanned} game{gamesScanned === 1 ? '' : 's'}
            </strong>
            {topEdgePct > 0 ? (
              <>
                . Best edge came in at{' '}
                <strong style={{ color: 'var(--sp-text, #E8EAED)', fontWeight: 500 }}>
                  +{Number(topEdgePct).toFixed(1)}%
                </strong>
                , well below the{' '}
                <strong style={{ color: 'var(--sp-text, #E8EAED)', fontWeight: 500 }}>
                  +{Number(thresholdPct).toFixed(1)}%
                </strong>
                {' '}qualifying threshold.
              </>
            ) : (
              <>. No qualifying opportunity in tonight's slate.</>
            )}
            {' '}No position taken. Capital available tomorrow.
          </p>
        </div>

        <div style={{
          display: 'flex',
          padding: '0 24px 20px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
        }}>
          {[
            { label: 'Scanned', value: String(gamesScanned), tone: 'plain' },
            { label: 'Top Edge', value: topEdgePct > 0 ? `+${Number(topEdgePct).toFixed(1)}%` : '—', tone: 'green' },
            { label: 'Threshold', value: `+${Number(thresholdPct).toFixed(1)}%`, tone: 'muted' },
            { label: 'Short By', value: gap > 0 ? `${gap.toFixed(1)}pp` : '—', tone: 'plain' },
          ].map((cell, i, arr) => (
            <div
              key={cell.label}
              style={{
                flex: 1,
                padding: '12px 8px',
                textAlign: 'center',
                borderRight: i < arr.length - 1 ? '1px solid rgba(255, 255, 255, 0.05)' : 'none',
              }}
            >
              <div style={{
                fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
                fontSize: '9px',
                letterSpacing: '0.22em',
                textTransform: 'uppercase',
                color: 'var(--sp-text-4, rgba(232, 234, 237, 0.35))',
                marginBottom: '6px',
              }}>
                {cell.label}
              </div>
              <div style={{
                fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
                fontSize: '18px',
                fontWeight: 500,
                lineHeight: 1,
                color: cell.tone === 'green'
                  ? 'var(--sp-green, #5A9E72)'
                  : cell.tone === 'muted'
                    ? 'var(--sp-text-3, rgba(232, 234, 237, 0.5))'
                    : 'var(--sp-text, #E8EAED)',
              }}>
                {cell.value}
              </div>
            </div>
          ))}
        </div>

        <div
          onClick={() => setPrincipleIdx((i) => (i + 1) % PRINCIPLES.length)}
          style={{
            padding: '18px 24px 24px',
            background: 'var(--sp-green-soft, rgba(90, 158, 114, 0.12))',
            borderLeft: '2px solid var(--sp-green, #5A9E72)',
            cursor: 'pointer',
          }}
        >
          <div style={{
            fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
            fontSize: '9px',
            fontWeight: 500,
            letterSpacing: '0.22em',
            textTransform: 'uppercase',
            color: 'var(--sp-green, #5A9E72)',
            marginBottom: '8px',
          }}>
            Sharp Principle
          </div>
          <div style={{
            fontFamily: '"IBM Plex Serif", Georgia, serif',
            fontSize: '15px',
            fontStyle: 'italic',
            lineHeight: 1.5,
            color: 'var(--sp-text, #E8EAED)',
          }}>
            {PRINCIPLES[principleIdx]}
          </div>
        </div>
      </div>

      <SectionEyebrow title="Market Intelligence" meta={miUpdated ? `UPDATED ${miUpdated.toUpperCase()}` : null} />

      <div
        onClick={onOpenMarketReport}
        role={onOpenMarketReport ? 'button' : undefined}
        tabIndex={onOpenMarketReport ? 0 : undefined}
        style={{
          background: 'var(--sp-surface, #121725)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '12px',
          padding: '14px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          marginBottom: '22px',
          position: 'relative',
          overflow: 'hidden',
          cursor: onOpenMarketReport ? 'pointer' : 'default',
        }}>
        <div style={{
          position: 'absolute',
          top: 0, bottom: 0, left: 0,
          width: '2px',
          background: 'var(--sp-green, #5A9E72)',
        }} />
        <div style={{
          flexShrink: 0,
          width: '36px',
          height: '36px',
          background: 'var(--sp-green-soft, rgba(90, 158, 114, 0.12))',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--sp-green, #5A9E72)',
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M3 17l6-6 4 4 8-8" />
          </svg>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontFamily: '"IBM Plex Serif", Georgia, serif',
            fontSize: '16px',
            fontWeight: 600,
            color: 'var(--sp-text, #E8EAED)',
            lineHeight: 1.3,
            marginBottom: '3px',
          }}>
            {gamesScanned} game{gamesScanned === 1 ? '' : 's'} · {edgeCount} edge{edgeCount === 1 ? '' : 's'} · {signals} signal{signals === 1 ? '' : 's'}
          </div>
          <div style={{
            fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
            fontSize: '11px',
            color: 'var(--sp-text-3, rgba(232, 234, 237, 0.5))',
            letterSpacing: '0.04em',
          }}>
            Density {density}%{mei != null ? ` · MEI ${mei}` : ''} · {regimeLabel}
          </div>
        </div>
        <svg
          width="18" height="18" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2"
          style={{ color: 'var(--sp-text-4, rgba(232, 234, 237, 0.35))', flexShrink: 0 }}
        >
          <path d="M9 18l6-6-6-6" />
        </svg>
      </div>

      {article && (
        <>
          <SectionEyebrow
            title="From the Journal"
            meta={`${article.readMinutes || 3} MIN READ`}
          />

          <div
            onClick={article.onClick}
            style={{
              background: 'var(--sp-surface, #121725)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '12px',
              padding: '18px 20px',
              marginBottom: '22px',
              cursor: article.onClick ? 'pointer' : 'default',
            }}
          >
            <div style={{
              display: 'flex',
              gap: '8px',
              alignItems: 'center',
              marginBottom: '12px',
              fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
              fontSize: '9px',
              fontWeight: 500,
              letterSpacing: '0.22em',
              textTransform: 'uppercase',
              color: 'var(--sp-text-3, rgba(232, 234, 237, 0.5))',
            }}>
              <span style={{ color: 'var(--sp-green, #5A9E72)' }}>{article.category || 'Insight'}</span>
              {article.source && (
                <>
                  <span style={{
                    width: '3px',
                    height: '3px',
                    background: 'var(--sp-text-5, rgba(232, 234, 237, 0.25))',
                    borderRadius: '50%',
                  }} />
                  <span>{article.source}</span>
                </>
              )}
            </div>
            <h3 style={{
              fontFamily: '"IBM Plex Serif", Georgia, serif',
              fontSize: '18px',
              fontWeight: 600,
              color: 'var(--sp-text, #E8EAED)',
              lineHeight: 1.3,
              marginBottom: '8px',
            }}>
              {article.title}
            </h3>
            {article.snippet && (
              <p style={{
                fontSize: '13px',
                lineHeight: 1.55,
                color: 'var(--sp-text-2, rgba(232, 234, 237, 0.7))',
                marginBottom: '14px',
              }}>
                {article.snippet}
              </p>
            )}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingTop: '12px',
              borderTop: '1px solid rgba(255, 255, 255, 0.05)',
            }}>
              <span style={{
                fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
                fontSize: '10px',
                color: 'var(--sp-text-4, rgba(232, 234, 237, 0.35))',
                letterSpacing: '0.04em',
              }}>
                {article.publishedDate || ''}
              </span>
              <span style={{
                fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
                fontSize: '10px',
                fontWeight: 500,
                letterSpacing: '0.22em',
                textTransform: 'uppercase',
                color: 'var(--sp-green, #5A9E72)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}>
                Read
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M9 18l6-6-6-6" />
                </svg>
              </span>
            </div>
          </div>
        </>
      )}

      <div style={{
        background: 'var(--sp-surface, #121725)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '12px',
        padding: '18px 20px',
        marginBottom: '24px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{
            fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
            fontSize: '10px',
            letterSpacing: '0.22em',
            textTransform: 'uppercase',
            color: 'var(--sp-text-3, rgba(232, 234, 237, 0.5))',
          }}>
            Next edge window · {sportUpper} slate opens
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
          <span style={{
            fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
            fontSize: '14px',
            fontWeight: 500,
            color: 'var(--sp-text, #E8EAED)',
            letterSpacing: '0.04em',
          }}>
            {nextWindow.openLocal || '—'}
          </span>
          <span style={{
            fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
            fontSize: '14px',
            fontWeight: 500,
            color: 'var(--sp-text-3, rgba(232, 234, 237, 0.5))',
            letterSpacing: '0.04em',
          }}>
            {countdown}
          </span>
        </div>
        <div style={{
          marginTop: '12px',
          height: '2px',
          background: 'var(--sp-surface-2, #1B2030)',
          borderRadius: '1px',
          overflow: 'hidden',
        }}>
          <div style={{
            height: '100%',
            width: `${progressPct}%`,
            background: 'var(--sp-green, #5A9E72)',
            borderRadius: '1px',
          }} />
        </div>
      </div>

      <div style={{
        textAlign: 'center',
        fontFamily: 'var(--sp-font-mono, "JetBrains Mono", monospace)',
        fontSize: '10px',
        lineHeight: 1.5,
        color: 'var(--sp-text-4, rgba(232, 234, 237, 0.35))',
        letterSpacing: '0.04em',
        padding: '0 24px',
      }}>
        For entertainment only. Past results do not guarantee future performance.
      </div>
    </div>
  );
}

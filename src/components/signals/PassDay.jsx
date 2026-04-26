import { useRef, useEffect, useState } from 'react';
import { inst as c } from '../../styles/tokens';
import ComplianceFooter from './shared/ComplianceFooter';
import HeroCard from './shared/HeroCard';
import MIPill from './shared/MIPill';
import SharpPrinciple from './shared/SharpPrinciple';
import CapitalCard from './shared/CapitalCard';
import FurtherReadingCard from './shared/FurtherReadingCard';
import CountdownCard from './shared/CountdownCard';

// Rotating Sharp Principles (per spec). Em-dashes get green color.
const PRINCIPLES = [
  `Pass days aren't missed opportunities<span style="color:#4ADE80;margin:0 4px;">—</span>they're proof the system is working.`,
  `The hardest edge to find is the patience to wait for one.`,
  `A bad bet at +EV beats a good bet at -EV. The market doesn't care which felt better.`,
  `Process over outcome. Always. Outcomes are noise; process is signal.`,
  `Discipline isn't doing more<span style="color:#4ADE80;margin:0 4px;">—</span>it's doing less, better.`,
  `Capital preserved is capital compounding. Zero risk on a non-edge is a win.`,
];

// Rotating market commentary. The first entry is dynamic and computed below.
function buildCommentary(gap) {
  const gapStr = gap > 0 ? gap.toFixed(1) : '0.0';
  return [
    `Market is pricing efficiently. Best opportunity fell ${gapStr}pp short of threshold.`,
    `Books have absorbed the public. No structural mispricing detected in tonight's slate.`,
    `Closing lines moved sharply<span style="color:#6B8AC4;">—</span>sharps already in. Edge gone.`,
    `Sample is too thin. Signal-to-noise ratio doesn't justify risk on this slate.`,
  ];
}

export default function PassDay({
  date = '',
  sport = 'NBA',
  gamesScanned = 0,
  signalsIssued = 0,
  tracked = 0,
  topEdgePct = 0,
  thresholdPct = 8.0,
  capitalPreservedUsd = 100,
  nextWindow = { hours: 0, minutes: 0, openLocal: '' },
  elapsedPct = 38,
  verdictText = '',
  marketReport,
  furtherReading,         // single article (legacy fallback)
  furtherReadings,        // array of articles for rotation (preferred)
}) {
  const containerRef = useRef(null);
  const [mounted, setMounted] = useState(false);

  const gap = Math.max(0, thresholdPct - topEdgePct);
  const commentary = buildCommentary(gap);

  // Rotation state
  const [principleIdx, setPrincipleIdx] = useState(0);
  const [commentaryIdx, setCommentaryIdx] = useState(0);
  const [articleIdx, setArticleIdx] = useState(0);

  const articles = (furtherReadings && furtherReadings.length > 0)
    ? furtherReadings
    : (furtherReading ? [furtherReading] : []);

  useEffect(() => { setMounted(true); }, []);

  // Auto-rotate principles every 6s
  useEffect(() => {
    const id = setInterval(() => {
      setPrincipleIdx(i => (i + 1) % PRINCIPLES.length);
    }, 6000);
    return () => clearInterval(id);
  }, []);

  // Auto-rotate commentary every 4.5s
  useEffect(() => {
    const id = setInterval(() => {
      setCommentaryIdx(i => (i + 1) % commentary.length);
    }, 4500);
    return () => clearInterval(id);
  }, [commentary.length]);

  // Auto-rotate articles every 7s (only if more than one)
  useEffect(() => {
    if (articles.length <= 1) return;
    const id = setInterval(() => {
      setArticleIdx(i => (i + 1) % articles.length);
    }, 7000);
    return () => clearInterval(id);
  }, [articles.length]);

  const heroStats = [
    { value: String(gamesScanned), label: 'Games' },
    { value: String(signalsIssued), label: 'Signals', color: signalsIssued === 0 ? 'dim' : undefined },
    { value: String(tracked), label: 'Tracked', color: tracked === 0 ? 'dim' : undefined },
    { value: `+${topEdgePct.toFixed(1)}%`, label: 'Top', color: 'green' },
  ];

  const edgeCount = marketReport?.edge_distribution
    ? (marketReport.edge_distribution.strong || 0) + (marketReport.edge_distribution.moderate || 0) + (marketReport.edge_distribution.weak || 0)
    : 0;

  const miSubline = `${gamesScanned} games \u00B7 ${edgeCount} edges \u00B7 ${signalsIssued} signals \u00B7 tap for edge map`;

  let delay = 0;
  const nextDelay = () => { const d = delay; delay += 50; return `${d}ms`; };

  const currentArticle = articles[articleIdx];

  return (
    <div ref={containerRef} style={{ padding: '0 16px' }}>
      {/* 1. Hero */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <HeroCard
          variant="pass"
          date={date}
          title="No qualifying edge."
          subtitle={`${gamesScanned} GAMES SCANNED \u00B7 TOP EDGE +${topEdgePct.toFixed(1)}% \u00B7 THRESHOLD +${thresholdPct.toFixed(1)}%`}
          verdictText={verdictText}
          commentary={commentary[commentaryIdx]}
          commentaryIdx={commentaryIdx}
          commentaryCount={commentary.length}
          onTapCommentary={() => setCommentaryIdx(i => (i + 1) % commentary.length)}
          stats={heroStats}
          tagline="One pick beats five."
        />
      </div>

      {/* 2. Market Intelligence */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <MIPill subline={miSubline} marketReport={marketReport} />
      </div>

      {/* 3. Sharp Principle (rotating) */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <SharpPrinciple
          label="Sharp Principle"
          index={principleIdx}
          total={PRINCIPLES.length}
          rotateKey={principleIdx}
          onTap={() => setPrincipleIdx(i => (i + 1) % PRINCIPLES.length)}
        >
          {PRINCIPLES[principleIdx]}
        </SharpPrinciple>
      </div>

      {/* 4. Capital Preserved */}
      {capitalPreservedUsd !== 0 && (
        <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
          <CapitalCard capitalPreservedUsd={capitalPreservedUsd} />
        </div>
      )}

      {/* 5. Article (rotating) + pagination */}
      {currentArticle && (
        <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
          <FurtherReadingCard
            {...currentArticle}
            rotateKey={articleIdx}
            onClick={(e) => {
              if (e && e.preventDefault) e.preventDefault();
              if (currentArticle.onClick) currentArticle.onClick(e);
            }}
          />
          {articles.length > 1 && (
            <div style={{
              display: 'flex',
              gap: 5,
              justifyContent: 'center',
              marginTop: 10,
              marginBottom: 18,
            }}>
              {articles.map((_, i) => (
                <span
                  key={i}
                  onClick={() => setArticleIdx(i)}
                  style={{
                    width: i === articleIdx ? 14 : 5,
                    height: 5,
                    borderRadius: i === articleIdx ? 3 : '50%',
                    background: i === articleIdx ? c.textSecondary : c.textMuted,
                    transition: 'width 0.2s, background 0.2s, border-radius 0.2s',
                    cursor: 'pointer',
                  }}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* 6. Countdown */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <CountdownCard
          header="Next Edge Window"
          title={`${sport.toUpperCase()} Slate Opens`}
          hours={nextWindow.hours}
          minutes={nextWindow.minutes}
          subtitle={nextWindow.openLocal}
          progressPct={elapsedPct}
        />
      </div>

      {/* 7. Compliance */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <ComplianceFooter />
      </div>
    </div>
  );
}

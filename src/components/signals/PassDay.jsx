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

// Stable date-seeded index so different articles surface on different days
// without shuffling on every render within the same day.
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

// Fallback Sharp Journal articles used when PicksTab supplies no real insights.
// PicksTab's pipeline is preserved; this only kicks in if `furtherReadings` is empty.
const FALLBACK_ARTICLES = [
  {
    category: 'Discipline',
    readMinutes: 4,
    publishedDate: 'Apr 25, 2026',
    title: 'The math of patience: why pass days are profitable',
    snippet: "When you skip a sub-threshold spot, you're not missing out \u2014 you're refusing to convert a coin flip into a tax on your bankroll.",
    source: 'Sharp Journal',
  },
  {
    category: 'Education',
    readMinutes: 6,
    publishedDate: 'Apr 24, 2026',
    title: 'How closing line value predicts long-term edge',
    snippet: "If you consistently beat the closing number, the market is telling you something the scoreboard can't.",
    source: 'Sharp Journal',
  },
  {
    category: 'How It Works',
    readMinutes: 3,
    publishedDate: 'Apr 22, 2026',
    title: 'Inside the threshold: what +8% really means',
    snippet: "Why SharpPicks won't tip a play under 8% edge \u2014 and how that number was calibrated against three seasons of backtest data.",
    source: 'Sharp Journal',
  },
  {
    category: 'Discipline',
    readMinutes: 5,
    publishedDate: 'Apr 19, 2026',
    title: "Tilt is a tax. Here's what it costs you per season.",
    snippet: 'Three years of data on chase bets, revenge plays, and overcorrection. The number is bigger than you think.',
    source: 'Sharp Journal',
  },
  {
    category: 'Education',
    readMinutes: 7,
    publishedDate: 'Apr 17, 2026',
    title: 'Reading line movement: when sharps tell on themselves',
    snippet: 'Steam moves, reverse line movement, and the difference between public-driven and money-driven shifts.',
    source: 'Sharp Journal',
  },
  {
    category: 'How It Works',
    readMinutes: 4,
    publishedDate: 'Apr 14, 2026',
    title: 'Why withdrawal is a feature, not a failure',
    snippet: "Pre-tip re-checks killed three signals last month. Here's the P&L impact of catching them in time.",
    source: 'Sharp Journal',
  },
];

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

  // Prefer real insights from PicksTab; fall back to brand copy when empty.
  const articles = (furtherReadings && furtherReadings.length > 0)
    ? furtherReadings
    : (furtherReading ? [furtherReading] : FALLBACK_ARTICLES);

  // Rotation state
  const [principleIdx, setPrincipleIdx] = useState(0);
  // Seed the initial article index by today's ET date so the first article
  // varies day-to-day instead of always landing on articles[0].
  const [articleIdx, setArticleIdx] = useState(() => dateSeedIndex(articles.length));

  // Two data-driven bullets describing why this is a pass. Replaces the
  // prior auto-rotating commentary carousel.
  const gap = Math.max(0, thresholdPct - topEdgePct);
  const bulletPoints = [
    `${gamesScanned} game${gamesScanned === 1 ? '' : 's'} scanned, 0 cleared the +${thresholdPct.toFixed(1)}% threshold`,
    topEdgePct > 0
      ? `Best edge +${topEdgePct.toFixed(1)}% fell ${gap.toFixed(1)}pp short`
      : 'No qualifying opportunity in tonight’s slate',
  ];

  useEffect(() => { setMounted(true); }, []);

  // Auto-rotate principles every 6s
  useEffect(() => {
    const id = setInterval(() => {
      setPrincipleIdx(i => (i + 1) % PRINCIPLES.length);
    }, 6000);
    return () => clearInterval(id);
  }, []);

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
    <div ref={containerRef} style={{ padding: '0' }}>
      {/* 1. Hero */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <HeroCard
          variant="pass"
          date={date}
          title="No qualifying edge."
          subtitle={`${gamesScanned} GAMES SCANNED \u00B7 TOP EDGE +${topEdgePct.toFixed(1)}% \u00B7 THRESHOLD +${thresholdPct.toFixed(1)}%`}
          verdictText={verdictText}
          bulletPoints={bulletPoints}
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

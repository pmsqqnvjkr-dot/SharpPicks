import { useRef, useEffect, useState } from 'react';
import SectionTitle from './shared/SectionTitle';
import SharpPrinciple from './shared/SharpPrinciple';
import ComplianceFooter from './shared/ComplianceFooter';
import HeroCard from './shared/HeroCard';
import MICard from './shared/MICard';
import EdgeMapCard from './shared/EdgeMapCard';
import CapitalCard from './shared/CapitalCard';
import CountdownCard from './shared/CountdownCard';

export default function PassDay({
  date = '',
  sport = 'NBA',
  gamesScanned = 0,
  signalsIssued = 0,
  tracked = 0,
  topEdgePct = 0,
  thresholdPct = 8.0,
  mei = 0,
  meiSevenDayAvg = 0,
  regime = 'Efficient',
  strengthCounts = { strong: 0, moderate: 0, weak: 0 },
  edgeMap = [],
  capitalPreservedUsd = 100,
  nextWindow = { hours: 0, minutes: 0, openLocal: '' },
  verdictText = '',
}) {
  const containerRef = useRef(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const gap = Math.max(0, thresholdPct - topEdgePct);
  const defaultVerdict = topEdgePct > 0
    ? `Market is pricing efficiently. Best opportunity fell ${gap.toFixed(1)}pp short of threshold.`
    : 'Market is pricing efficiently. No qualifying opportunities detected.';

  const heroStats = [
    { value: String(gamesScanned), label: 'Games' },
    { value: String(signalsIssued), label: 'Signals', color: signalsIssued === 0 ? 'dim' : undefined },
    { value: String(tracked), label: 'Tracked' },
    { value: `+${topEdgePct.toFixed(1)}%`, label: 'Top', color: 'green' },
  ];

  return (
    <div ref={containerRef} style={{ padding: '0 16px' }}>
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: '0ms' }}>
        <HeroCard
          variant="pass"
          date={date}
          title="No qualifying edge."
          subtitle={`${gamesScanned} GAMES SCANNED \u00B7 TOP EDGE +${topEdgePct.toFixed(1)}% \u00B7 THRESHOLD +${thresholdPct.toFixed(1)}%`}
          verdictText={verdictText || defaultVerdict}
          stats={heroStats}
        />
      </div>

      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: '50ms' }}>
        <SectionTitle tone="green" live>Market Intelligence &middot; Live</SectionTitle>
        <MICard
          mei={mei}
          regime={regime}
          topEdgePct={topEdgePct}
          sevenDayAvg={meiSevenDayAvg}
          strengthCounts={strengthCounts}
        />
      </div>

      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: '100ms' }}>
        <SharpPrinciple>
          Pass days aren't missed opportunities — they're proof the system is working.
        </SharpPrinciple>
      </div>

      {edgeMap.length > 0 && (
        <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: '150ms' }}>
          <SectionTitle tone="blue">Edge Map &middot; Today's Slate</SectionTitle>
          <EdgeMapCard edgeMap={edgeMap} thresholdPct={thresholdPct} />
        </div>
      )}

      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: '200ms' }}>
        <SectionTitle tone="green">Capital Preserved</SectionTitle>
        <CapitalCard capitalPreservedUsd={capitalPreservedUsd} />
      </div>

      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: '250ms' }}>
        <SectionTitle tone="blue">Next Edge Window</SectionTitle>
        <CountdownCard
          title={`${sport.toUpperCase()} Slate Opens`}
          hours={nextWindow.hours}
          minutes={nextWindow.minutes}
          subtitle={nextWindow.openLocal}
          progressPct={38}
        />
      </div>

      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: '300ms' }}>
        <ComplianceFooter />
      </div>
    </div>
  );
}

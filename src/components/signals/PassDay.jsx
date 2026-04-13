import { useRef, useEffect, useState } from 'react';
import SectionTitle from './shared/SectionTitle';
import SharpPrinciple from './shared/SharpPrinciple';
import ComplianceFooter from './shared/ComplianceFooter';
import HeroCard from './shared/HeroCard';
import MIPill from './shared/MIPill';
import CapitalCard from './shared/CapitalCard';
import FurtherReadingCard from './shared/FurtherReadingCard';
import CountdownCard from './shared/CountdownCard';

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
  furtherReading,
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

  const edgeCount = marketReport?.edge_distribution
    ? (marketReport.edge_distribution.strong || 0) + (marketReport.edge_distribution.moderate || 0) + (marketReport.edge_distribution.weak || 0)
    : 0;

  const miSubline = `${gamesScanned} games \u00B7 ${edgeCount} edges \u00B7 ${signalsIssued} signals \u00B7 tap for edge map`;

  let delay = 0;
  const nextDelay = () => { const d = delay; delay += 50; return `${d}ms`; };

  return (
    <div ref={containerRef} style={{ padding: '0 16px' }}>
      {/* 1. Hero */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <HeroCard
          variant="pass"
          date={date}
          title="No qualifying edge."
          subtitle={`${gamesScanned} GAMES SCANNED \u00B7 TOP EDGE +${topEdgePct.toFixed(1)}% \u00B7 THRESHOLD +${thresholdPct.toFixed(1)}%`}
          verdictText={verdictText || defaultVerdict}
          stats={heroStats}
        />
      </div>

      {/* 2. MI Pill (collapsed by default) */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <MIPill
          subline={miSubline}
          marketReport={marketReport}
        />
      </div>

      {/* 3. Sharp Principle */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <SharpPrinciple>
          Pass days aren't missed opportunities — they're proof the system is working.
        </SharpPrinciple>
      </div>

      {/* 4. Capital Preserved */}
      {capitalPreservedUsd !== 0 && (
        <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
          <SectionTitle tone="green">Capital Preserved</SectionTitle>
          <CapitalCard capitalPreservedUsd={capitalPreservedUsd} />
        </div>
      )}

      {/* 5. Further Reading */}
      {furtherReading && (
        <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
          <SectionTitle tone="dim">Further Reading</SectionTitle>
          <FurtherReadingCard {...furtherReading} />
        </div>
      )}

      {/* 6. Countdown */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <SectionTitle tone="blue">Next Edge Window</SectionTitle>
        <CountdownCard
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

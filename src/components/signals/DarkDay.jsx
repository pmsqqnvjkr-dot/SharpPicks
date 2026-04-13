import { useEffect, useState } from 'react';
import SectionTitle from './shared/SectionTitle';
import SharpPrinciple from './shared/SharpPrinciple';
import ComplianceFooter from './shared/ComplianceFooter';
import HeroCard from './shared/HeroCard';
import CountdownCard from './shared/CountdownCard';
import MIPill from './shared/MIPill';
import CrossSportCard from './shared/CrossSportCard';
import WeekRecapCard from './shared/WeekRecapCard';
import ScheduleCard from './shared/ScheduleCard';

export default function DarkDay({
  date = '',
  sport = 'NBA',
  returnDate = '',
  nextWindow = { hours: 0, minutes: 0, gamesCount: 0, openLocal: '' },
  elapsedPct = 0,
  crossSport,
  onSwitchSport,
  weekRecap = {
    netUsd: 0,
    record: '0-0',
    passDays: 0,
    signalsIssued: 0,
    daysCovered: 0,
    selectivityPct: 0,
    sparkline: [],
  },
  weekAhead = [],
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const countdownSubtitle = nextWindow.openLocal
    || (nextWindow.gamesCount > 0
      ? `${returnDate} \u00B7 ${nextWindow.gamesCount} games \u00B7 lines drop 11:00 AM ET`
      : returnDate);

  let delay = 0;
  const nextDelay = () => { const d = delay; delay += 50; return `${d}ms`; };

  return (
    <div style={{ padding: '0 16px' }}>
      {/* 1. Hero */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <HeroCard
          variant="dark"
          date={date}
          title="No games on the slate."
          subtitle={`${sport.toUpperCase()} \u00B7 SCHEDULED RETURN ${returnDate.toUpperCase()}`}
          verdictText={`Model is idle. The next ${sport.toUpperCase()} window opens ${nextWindow.openLocal || 'tomorrow'}.`}
        />
      </div>

      {/* 2. Countdown */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <SectionTitle tone="green">Next Edge Window</SectionTitle>
        <CountdownCard
          title={`${sport.toUpperCase()} Returns In`}
          hours={nextWindow.hours}
          minutes={nextWindow.minutes}
          subtitle={countdownSubtitle}
          progressPct={elapsedPct}
        />
      </div>

      {/* 3. MI Pill (zero-state) */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <MIPill
          subline="No games scheduled"
          zeroState
        />
      </div>

      {/* 4. Cross-sport */}
      {crossSport && (
        <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
          <SectionTitle tone="blue">Live Elsewhere</SectionTitle>
          <CrossSportCard
            sport={crossSport.sport}
            isBeta={crossSport.isBeta}
            matchup={crossSport.matchup}
            pick={crossSport.pick}
            tipoffLocal={crossSport.tipoffLocal}
            tier={crossSport.tier}
            edgePct={crossSport.edgePct}
            onSwitchSport={onSwitchSport}
          />
        </div>
      )}

      {/* 5. Sharp Principle */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <SharpPrinciple>
          The goal isn't just to win a bet; it's to build a sustainable edge.
        </SharpPrinciple>
      </div>

      {/* 6. Week Recap */}
      {(weekRecap.signalsIssued > 0 || weekRecap.daysCovered > 0) && (
        <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
          <SectionTitle tone="dim">Your Week So Far</SectionTitle>
          <WeekRecapCard
            sparkline={weekRecap.sparkline}
            netUsd={weekRecap.netUsd}
            record={weekRecap.record}
            passDays={weekRecap.passDays}
            signalsIssued={weekRecap.signalsIssued}
            daysCovered={weekRecap.daysCovered}
            selectivityPct={weekRecap.selectivityPct}
          />
        </div>
      )}

      {/* 7. 7-Day Look-Ahead */}
      {weekAhead.length > 0 && (
        <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
          <SectionTitle tone="dim">7-Day Look-Ahead &middot; {sport.toUpperCase()}</SectionTitle>
          <ScheduleCard weekAhead={weekAhead} />
        </div>
      )}

      {/* 8. Compliance */}
      <div className={mounted ? 'sp-fade-child' : ''} style={{ animationDelay: nextDelay() }}>
        <ComplianceFooter />
      </div>
    </div>
  );
}

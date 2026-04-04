import { useState, useEffect, useCallback } from 'react';
import { Capacitor } from '@capacitor/core';
import { useAuth } from '../../hooks/useAuth';
import { useApi, getAuthToken } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';
import teamAbbr, { teamCity } from '../../utils/teamAbbr';

const PT_API_BASE = Capacitor.isNativePlatform() ? 'https://app.sharppicks.ai' : '';
import PullToRefresh from '../shared/PullToRefresh';
import PickCard from './PickCard';
import OnboardingCard from './OnboardingCard';
import DailyMarketReport from './DailyMarketReport';
import { GameSlate } from './MarketView';
import AuthModal from './AuthModal';
import LoadingState from './LoadingState';
import ResolutionScreen from './ResolutionScreen';
import { InlineError } from './ErrorStates';


function isTodayGame(gameDate) {
  if (!gameDate) return false;
  const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  return gameDate.startsWith(today);
}

function formatDateShort(isoStr) {
  if (!isoStr) return '';
  if (typeof isoStr === 'string' && isoStr.match(/^\d{4}-\d{2}-\d{2}/)) {
    const [y, m, day] = isoStr.split('-');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    const dt = new Date(parseInt(y), parseInt(m) - 1, parseInt(day));
    return `${days[dt.getDay()]} ${months[parseInt(m) - 1]} ${parseInt(day)}`;
  }
  return isoStr;
}

function useCountdownTo(targetHourEt = 10) {
  const [text, setText] = useState('');
  useEffect(() => {
    const update = () => {
      try {
        const parts = new Intl.DateTimeFormat('en-CA', {
          timeZone: 'America/New_York',
          hour: 'numeric', minute: 'numeric', hour12: false,
        }).formatToParts(new Date());
        const hour = parseInt(parts.find(p => p.type === 'hour')?.value || '0', 10);
        const min = parseInt(parts.find(p => p.type === 'minute')?.value || '0', 10);
        const currentMins = hour * 60 + min;
        const targetMins = targetHourEt * 60;
        let minsUntil = targetMins - currentMins;
        if (minsUntil <= 0) minsUntil += 24 * 60;
        if (minsUntil < 60) setText(`${minsUntil}m`);
        else if (minsUntil < 1440) setText(`${Math.floor(minsUntil / 60)}h ${minsUntil % 60}m`);
        else setText(`${Math.floor(minsUntil / 1440)}d`);
      } catch { setText(''); }
    };
    update();
    const id = setInterval(update, 60000);
    return () => clearInterval(id);
  }, [targetHourEt]);
  return text;
}

export default function PicksTab({ onNavigate }) {
  const { user, loading: authLoading, enablePush, pushStatus } = useAuth();
  const { sport, setSport } = useSport();
  const { data: todayData, loading, error, refetch: refetchToday } = useApi(sportQuery('/picks/today', sport));
  const { data: stats, refetch: refetchStats } = useApi(sportQuery('/public/stats', sport));
  const { data: marketReport, refetch: refetchMarketReport } = useApi(sportQuery('/public/market-report', sport), { pollInterval: 300000 });
  const { data: killSwitch } = useApi(sportQuery('/public/kill-switch', sport), { pollInterval: 600000 });
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);
  const { data: lastResolved } = useApi(sportQuery('/picks/last-resolved', sport), { skip: !isPro });
  const { data: insightsData } = useApi('/insights?limit=3&rotate=1');
  const { data: allSportsStats } = useApi('/public/stats');
  const [showAuth, setShowAuth] = useState(false);
  const [showResolution, setShowResolution] = useState(false);
  const [resolutionPick, setResolutionPick] = useState(null);
  const [dismissedOutcomes, setDismissedOutcomes] = useState(() => {
    try {
      const raw = localStorage.getItem('sp_dismissed_outcomes');
      return new Set(raw ? JSON.parse(raw) : []);
    } catch { return new Set(); }
  });
  const [liveScore, setLiveScore] = useState(null);
  const [allLiveScores, setAllLiveScores] = useState([]);
  const [miExpanded, setMiExpanded] = useState(null);
  const [gameInfo, setGameInfo] = useState(null);
  const [tomorrowGames, setTomorrowGames] = useState(null);
  const [tomorrowDate, setTomorrowDate] = useState(null);
  const [tonightBets, setTonightBets] = useState(null);
  const modelRunHour = todayData?.model_run_hour || (sport === 'mlb' ? 11 : 10);
  const modelRunLabel = todayData?.model_runs_at || (modelRunHour <= 12 ? `${modelRunHour}:00 AM ET` : `${modelRunHour - 12}:00 PM ET`);
  const countdown = useCountdownTo(modelRunHour);

  useEffect(() => {
    setLiveScore(null);
    setAllLiveScores([]);
    setMiExpanded(null);
    setGameInfo(null);
  }, [sport]);

  const handleDismissResolution = (pickId) => {
    setDismissedOutcomes(prev => {
      const next = new Set(prev);
      next.add(pickId);
      const arr = [...next].slice(-50);
      localStorage.setItem('sp_dismissed_outcomes', JSON.stringify(arr));
      return new Set(arr);
    });
  };

  const handleShareResult = useCallback(async (pick) => {
    const apiRoot = Capacitor.isNativePlatform() ? 'https://app.sharppicks.ai' : '';
    const cardUrl = `${apiRoot}/api/cards/result/${pick.id}?v=4`;
    const filename = `sharppicks-result-${pick.id}.png`;
    try {
      const token = getAuthToken();
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(cardUrl, { headers, credentials: 'include' });
      if (!res.ok) return;
      const blob = await res.blob();
      if (Capacitor.isNativePlatform()) {
        const { Filesystem, Directory } = await import('@capacitor/filesystem');
        const { Share } = await import('@capacitor/share');
        const reader = new FileReader();
        const base64 = await new Promise((resolve, reject) => { reader.onloadend = () => resolve(reader.result.split(',')[1]); reader.onerror = reject; reader.readAsDataURL(blob); });
        const file = await Filesystem.writeFile({ path: filename, data: base64, directory: Directory.Cache });
        await Share.share({ title: 'Sharp Picks Result', text: 'sharppicks.ai', url: file.uri });
        try { await Filesystem.deleteFile({ path: filename, directory: Directory.Cache }); } catch {}
      } else {
        const file = new File([blob], filename, { type: 'image/png' });
        if (navigator.share && navigator.canShare?.({ files: [file] })) {
          await navigator.share({ files: [file], text: 'Sharp Picks result' });
        } else {
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
          URL.revokeObjectURL(url);
        }
      }
    } catch {}
  }, []);

  const fetchLiveForPick = useCallback(async () => {
    if (!todayData || todayData.type !== 'pick' || !todayData.home_team) {
      setLiveScore(null);
      return;
    }
    try {
      const resp = await fetch(`${PT_API_BASE}/api/picks/live-scores?sport=${sport}`);
      const json = await resp.json();
      if (json.scores) {
        setAllLiveScores(json.scores);
        const normalize = s => s.toLowerCase().replace(/[^a-z]/g, '');
        const homeKey = normalize(todayData.home_team);
        const match = json.scores.find(s => normalize(s.home) === homeKey);
        if (match && (match.state === 'STATUS_IN_PROGRESS' || match.state === 'STATUS_HALFTIME' || match.state === 'STATUS_FINAL')) {
          setLiveScore(match);
        } else {
          setLiveScore(null);
        }
      }
    } catch {}
  }, [todayData, sport]);

  useEffect(() => {
    fetchLiveForPick();
    const fast = liveScore && (liveScore.state === 'STATUS_IN_PROGRESS' || liveScore.state === 'STATUS_HALFTIME');
    const interval = setInterval(fetchLiveForPick, fast ? 15000 : 60000);
    return () => clearInterval(interval);
  }, [fetchLiveForPick, liveScore]);

  // Night mode detection: two scenarios
  // 1) Same-day: all today's games final + model ran today (pick/pass)
  // 2) Post-midnight: today is "waiting" (model hasn't run) + we have a recent resolved pick from yesterday
  const allTodayFinal = gameInfo?.allFinal === true;
  const todayHasEdges = gameInfo?.hasModel === true;
  const sameDayNight = allTodayFinal && todayHasEdges && (todayData?.type === 'pick' || todayData?.type === 'pass');

  const todayET = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  const yesterdayDate = (() => {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return d.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  })();
  const lastResolvedIsRecent = lastResolved?.game_date === yesterdayDate || lastResolved?.game_date === todayET;

  const etHour = (() => {
    try {
      const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York', hour: 'numeric', hour12: false }).formatToParts(new Date());
      return parseInt(parts.find(p => p.type === 'hour')?.value || '12', 10);
    } catch { return 12; }
  })();
  const postMidnightNight = todayData?.type === 'waiting' && etHour < 10;

  const isNightMode = sameDayNight || postMidnightNight;
  const hasRecapPick = lastResolvedIsRecent && lastResolved?.result && lastResolved.result !== 'pending';
  const nightRecapPick = sameDayNight ? todayData : (hasRecapPick ? lastResolved : null);
  const hasAnyRecapContent = !!(nightRecapPick && nightRecapPick.result && nightRecapPick.result !== 'pending')
    || !!(tonightBets && tonightBets.length > 0)
    || (sameDayNight && todayData?.type === 'pass')
    || (postMidnightNight && !hasRecapPick);

  useEffect(() => {
    if (!isNightMode) { setTomorrowGames(null); setTomorrowDate(null); setTonightBets(null); return; }

    const isPostMidnight = postMidnightNight;
    const fetchSlatePreview = async () => {
      if (isPostMidnight) {
        try {
          const resp = await fetch(`${PT_API_BASE}/api/picks/market?sport=${sport}`);
          const json = await resp.json();
          if (json.games) { setTomorrowGames(json.games); setTomorrowDate(json.date || null); }
        } catch { setTomorrowGames(null); setTomorrowDate(null); }
      } else {
        try {
          const tomorrow = new Date();
          tomorrow.setDate(tomorrow.getDate() + 1);
          const tStr = tomorrow.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
          const resp = await fetch(`${PT_API_BASE}/api/picks/market?sport=${sport}&date=${tStr}`);
          const json = await resp.json();
          if (json.games) { setTomorrowGames(json.games); setTomorrowDate(json.date || null); }
        } catch { setTomorrowGames(null); setTomorrowDate(null); }
      }
    };

    const fetchTonightBets = async () => {
      try {
        const token = getAuthToken();
        if (!token) { setTonightBets(null); return; }
        const resp = await fetch(`${PT_API_BASE}/api/bets?sport=${sport}`, {
          headers: { Authorization: `Bearer ${token}` },
          credentials: 'include',
        });
        const json = await resp.json();
        if (json.bets) {
          const yDate = (() => { const dd = new Date(); dd.setDate(dd.getDate() - 1); return dd.toLocaleDateString('en-CA', { timeZone: 'America/New_York' }); })();
          const tDate = new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
          const recapDate = isPostMidnight ? yDate : tDate;
          const resolved = json.bets.filter(b =>
            (b.result && b.result !== 'pending') &&
            b.linked_pick?.game_date?.startsWith(recapDate)
          );
          setTonightBets(resolved.length > 0 ? resolved : null);
        }
      } catch { setTonightBets(null); }
    };
    fetchSlatePreview();
    fetchTonightBets();
  }, [isNightMode, sport, postMidnightNight]);

  // Determine the 5-state: night, pre-model, pick, pass, off-day
  const pageState =
    isNightMode ? 'night' :
    todayData?.type === 'pick' ? 'pick' :
    todayData?.type === 'pass' ? 'pass' :
    todayData?.type === 'waiting' ? 'pre-model' :
    (todayData?.type === 'off_day' || todayData?.type === 'allstar_break') ? 'off-day' :
    (!todayData && !error) ? 'pre-model' :
    'pre-model';

  const isRevoked = todayData?.type === 'pick' && todayData?.result === 'revoked';
  const isResolved = todayData?.type === 'pick' && todayData?.result && todayData.result !== 'pending' && todayData.result !== 'revoked';

  if (loading || authLoading) {
    return <LoadingState />;
  }

  if (showResolution && resolutionPick) {
    return <ResolutionScreen pick={resolutionPick} onBack={() => { setShowResolution(false); setResolutionPick(null); }} onNavigate={onNavigate} />;
  }

  // MI card default state: collapsed on pick day, expanded on pass day
  const isMiExpanded = miExpanded !== null ? miExpanded : false;

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric',
    timeZone: 'America/New_York',
  });

  const sportName = (sport || 'nba').toUpperCase();
  const edgeCount = gameInfo?.edges || 0;
  const signalCount = gameInfo?.signals || 0;
  const totalGames = gameInfo?.total || (todayData?.games_analyzed || 0);
  const density = totalGames > 0 ? Math.round((signalCount / totalGames) * 100) : 0;

  const topEdge = todayData?.whatif?.edge_pct || (marketReport?.largest_edge) || 0;
  const threshold = 3.5;

  // Cross-sport data for off-day nudge
  const otherSports = ['nba', 'mlb', 'wnba'].filter(s => s !== sport);

  return (
    <div style={{ padding: '0' }}>
      <PullToRefresh onRefresh={async () => {
        await Promise.all([refetchToday(true), refetchStats(true), refetchMarketReport(true)]);
      }}>
      <div style={{ padding: '20px 20px 0' }}>

        {/* Kill Switch Banner */}
        {killSwitch?.active && isPro && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '10px 14px', marginBottom: '14px',
            borderRadius: '10px',
            background: 'rgba(251,191,36,0.06)',
            border: '1px solid rgba(251,191,36,0.2)',
          }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#FBBF24', flexShrink: 0 }} />
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, color: '#FBBF24', marginBottom: '2px' }}>Reduced Exposure Mode</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-tertiary)' }}>Position sizing adjusted to {killSwitch.position_size_pct}%. Circuit breaker active.</div>
            </div>
          </div>
        )}

        {/* Calibration Banner */}
        {todayData?.model_phase === 'calibration' && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '10px 14px', marginBottom: '14px',
            borderRadius: '10px',
            background: 'rgba(59,130,246,0.06)',
            border: '1px solid rgba(59,130,246,0.2)',
          }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#3B82F6', flexShrink: 0 }} />
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, color: '#3B82F6', marginBottom: '2px' }}>Model Phase: Calibration</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-tertiary)' }}>Edges are being tracked live. Early signals, full transparency.</div>
            </div>
          </div>
        )}

        {/* Trial Banner */}
        {user && user.subscription_status === 'trial' && user.trial_end_date && (() => {
          const daysLeft = Math.max(0, Math.ceil((new Date(user.trial_end_date) - new Date()) / (1000 * 60 * 60 * 24)));
          return daysLeft > 0 ? (
            <div style={{
              background: 'linear-gradient(135deg, rgba(10,13,20,0.95) 0%, rgba(15,20,30,0.95) 100%)',
              border: `1px solid ${daysLeft <= 2 ? 'rgba(251,191,36,0.25)' : daysLeft <= 5 ? 'rgba(251,191,36,0.15)' : 'var(--color-signal-border)'}`,
              borderRadius: '14px', padding: '16px 18px', marginBottom: '16px',
              position: 'relative', overflow: 'hidden',
              ...(daysLeft <= 1 ? { animation: 'trialPulse 3s ease-in-out infinite' } : {}),
            }}>
              <style>{`
                @keyframes trialPulse { 0%, 100% { box-shadow: 0 0 0 rgba(251,191,36,0); } 50% { box-shadow: 0 0 12px rgba(251,191,36,0.08); } }
              `}</style>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 700, color: daysLeft <= 2 ? '#FBBF24' : 'var(--green-profit)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>PRO TRIAL &bull; {daysLeft} {daysLeft === 1 ? 'DAY' : 'DAYS'} LEFT</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '22px', fontWeight: 800, color: daysLeft <= 2 ? '#FBBF24' : 'var(--green-profit)', lineHeight: 1 }}>{daysLeft}d</div>
              </div>
              <div style={{ fontFamily: 'var(--font-sans)', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '14px' }}>You're inside the full model. {daysLeft <= 1 ? 'Access narrows tomorrow.' : `In ${daysLeft} days, access narrows.`}</div>
              <button onClick={() => window.open('https://sharppicks.ai/#pricing', '_blank')} style={{ width: '100%', padding: '12px 24px', background: '#5A9E72', border: 'none', borderRadius: '8px', color: '#0A0D14', fontSize: '12px', fontWeight: 600, cursor: 'pointer', fontFamily: 'var(--font-mono)', letterSpacing: '1px' }}>View Plans</button>
              <div style={{ textAlign: 'center', marginTop: '8px', fontFamily: 'var(--font-sans)', fontSize: '11px', color: 'rgba(255,255,255,0.6)' }}>Full decision visibility ends after trial.</div>
            </div>
          ) : null;
        })()}

        {/* First MLB Visit onboarding card */}
        {sport === 'mlb' && (
          <OnboardingCard cardId="mlb" title="CALIBRATION BETA">
            MLB signals use the same pipeline as NBA but are building a live track record. Edges are real. Sizing is identical. Every signal is tracked and graded. The BETA label comes off when the data justifies it.
          </OnboardingCard>
        )}

        {/* Resolved Pick Banner (suppressed in night mode; recap handles it) */}
        {!isNightMode && lastResolved && lastResolved.id && !isResolved && !dismissedOutcomes.has(lastResolved.id) && (
          <ResolvedPickBanner
            pick={lastResolved}
            onViewDetails={() => { setResolutionPick(lastResolved); setShowResolution(true); }}
            onDismiss={() => handleDismissResolution(lastResolved.id)}
            onShare={isPro ? handleShareResult : undefined}
          />
        )}
        {!isNightMode && todayData?.type === 'pick' && isResolved && isPro && !dismissedOutcomes.has(todayData.id) && (
          <ResolvedPickBanner
            pick={todayData}
            onViewDetails={() => { setResolutionPick(todayData); setShowResolution(true); }}
            onDismiss={() => handleDismissResolution(todayData.id)}
            onShare={handleShareResult}
          />
        )}
        {!isNightMode && todayData?.type === 'pick' && isResolved && !isPro && (
          <FreePickNotice resolved onUpgrade={() => { if (user) { if (onNavigate) onNavigate('profile', 'upgrade'); } else { setShowAuth(true); } }} />
        )}
        {/* Contextual push notification prompt — after first resolved signal */}
        {!isNightMode && isResolved && user && pushStatus !== 'granted' && pushStatus !== 'denied' && localStorage.getItem('sp_push_prompt_dismissed') !== '1' && (
          <PushPromptInline onEnable={enablePush} onDismiss={() => localStorage.setItem('sp_push_prompt_dismissed', '1')} />
        )}
        {!isNightMode && isRevoked && (
          <RevokedPassCard pick={todayData} onViewDetails={() => { setResolutionPick(todayData); setShowResolution(true); }} />
        )}


        {/* ═══════════════ STATE 0: NIGHT MODE ═══════════════ */}
        {pageState === 'night' && (
          <>
            {/* ── DATE RECAP ── */}
            {hasAnyRecapContent && (
              <div style={{
                fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', fontWeight: 700,
                letterSpacing: '2px', textTransform: 'uppercase', color: '#8494a7',
                padding: '0 0 8px',
              }}>{formatDateShort(postMidnightNight ? yesterdayDate : todayET)} RECAP</div>
            )}

            {/* Signal Result Card */}
            {nightRecapPick && nightRecapPick.result && nightRecapPick.result !== 'pending' && nightRecapPick.result !== 'revoked' && (() => {
              const rp = nightRecapPick;
              const isWin = rp.result === 'win';
              const isPushR = rp.result === 'push';
              const borderAccent = isWin ? '#5A9E72' : isPushR ? '#8494a7' : '#D4787B';
              const resultLabel = isWin ? 'WIN' : isPushR ? 'PUSH' : 'LOSS';
              const resultBg = isWin ? 'rgba(90,158,114,0.15)' : isPushR ? 'rgba(132,148,167,0.15)' : 'rgba(212,120,123,0.15)';
              const resultColor = isWin ? '#5A9E72' : isPushR ? '#8494a7' : '#D4787B';
              const sideLabel = rp.side && rp.line != null && rp.side.includes(String(Math.abs(rp.line)))
                ? rp.side : `${rp.side} ${rp.line > 0 ? '+' : ''}${rp.line}`;
              const pnl = rp.profit_units != null ? Number(rp.profit_units) : (isWin ? 0.9 : isPushR ? 0 : -1.0);
              const coverMargin = (rp.home_score != null && rp.away_score != null && rp.line != null)
                ? (() => {
                    const sLow = (rp.side || '').toLowerCase();
                    const isHome = sLow.includes((rp.home_team || '').split(' ').pop().toLowerCase());
                    const margin = isHome
                      ? (rp.home_score - rp.away_score) + rp.line
                      : (rp.away_score - rp.home_score) + rp.line;
                    return margin;
                  })()
                : null;
              return (
                <div onClick={() => { setResolutionPick(rp); setShowResolution(true); }} style={{
                  background: '#111e33', border: '0.5px solid #1e3050',
                  borderLeft: `3px solid ${borderAccent}`,
                  borderRadius: 8, padding: 12, marginBottom: 12, cursor: 'pointer',
                }}>
                  <div style={{
                    fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', fontWeight: 700,
                    letterSpacing: '0.1em', textTransform: 'uppercase', color: '#5A9E72', marginBottom: 8,
                  }}>SIGNAL RESULT</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div style={{ fontFamily: "'Inter', var(--font-sans), sans-serif", fontSize: '14px', fontWeight: 600, color: '#E8ECF4' }}>{sideLabel}</div>
                    <span style={{
                      fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', fontWeight: 700,
                      padding: '2px 8px', borderRadius: 4, background: resultBg, color: resultColor,
                    }}>{resultLabel}</span>
                  </div>
                  {rp.home_score != null && rp.away_score != null && (
                    <div style={{
                      fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '11px', color: '#9aa5b4',
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8,
                    }}>
                      <span>{teamAbbr(rp.away_team)} {rp.away_score} &middot; {teamAbbr(rp.home_team)} {rp.home_score}</span>
                      <span style={{ color: resultColor, fontWeight: 600 }}>{pnl >= 0 ? '+' : ''}{pnl.toFixed(1)}u</span>
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {rp.edge_pct != null && (
                      <span style={{ fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', padding: '3px 8px', borderRadius: 4, background: 'rgba(30,48,80,0.4)', color: '#9aa5b4' }}>Edge +{Number(rp.edge_pct).toFixed(1)}%</span>
                    )}
                    {rp.clv != null && (
                      <span style={{ fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', padding: '3px 8px', borderRadius: 4, background: 'rgba(30,48,80,0.4)', color: parseFloat(rp.clv) > 0 ? '#5A9E72' : '#9aa5b4' }}>CLV {parseFloat(rp.clv) > 0 ? '+' : ''}{parseFloat(rp.clv).toFixed(1)}</span>
                    )}
                    {coverMargin != null && (
                      <span style={{ fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', padding: '3px 8px', borderRadius: 4, background: 'rgba(30,48,80,0.4)', color: coverMargin > 0 ? '#5A9E72' : '#D4787B' }}>Cover by {Math.abs(coverMargin).toFixed(1)}</span>
                    )}
                  </div>
                </div>
              );
            })()}

            {/* Signal Withdrawn recap — show from todayData OR nightRecapPick */}
            {(() => {
              const revokedPick = (todayData?.type === 'pick' && todayData?.result === 'revoked') ? todayData
                : (nightRecapPick?.result === 'revoked' ? nightRecapPick : null);
              if (!revokedPick) return null;
              return (
                <div onClick={() => { setResolutionPick(revokedPick); setShowResolution(true); }} style={{
                  background: '#111e33', border: '0.5px solid #1e3050',
                  borderLeft: '3px solid #8494a7',
                  borderRadius: 8, padding: 12, marginBottom: 12, cursor: 'pointer',
                }}>
                  <div style={{
                    fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', fontWeight: 700,
                    letterSpacing: '0.1em', textTransform: 'uppercase', color: '#8494a7', marginBottom: 8,
                  }}>SIGNAL WITHDRAWN</div>
                  <div style={{ fontFamily: "'Inter', var(--font-sans), sans-serif", fontSize: '14px', fontWeight: 600, color: '#E8ECF4', marginBottom: 4 }}>
                    {revokedPick.side} {revokedPick.line > 0 ? '+' : ''}{revokedPick.line}
                  </div>
                  <div style={{ fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '11px', color: '#8494a7' }}>
                    Withdrawn before tip. Capital preserved.
                  </div>
                  {revokedPick.edge_pct != null && (
                    <div style={{ marginTop: 8 }}>
                      <span style={{ fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', padding: '3px 8px', borderRadius: 4, background: 'rgba(30,48,80,0.4)', color: '#9aa5b4' }}>Edge at entry +{Number(revokedPick.edge_pct).toFixed(1)}%</span>
                    </div>
                  )}
                </div>
              );
            })()}

            {/* Full Slate Results (tracked bets resolved tonight) */}
            {tonightBets && tonightBets.length > 0 && (() => {
              const wins = tonightBets.filter(b => (b.profit_units || 0) > 0 || b.result === 'win' || b.pick_result === 'W').length;
              const losses = tonightBets.filter(b => (b.profit_units || 0) < 0 || b.result === 'loss' || b.pick_result === 'L').length;
              const netUnits = tonightBets.reduce((sum, b) => sum + (b.profit_units || 0), 0);
              return (
                <div style={{
                  background: '#111e33', border: '0.5px solid #1e3050',
                  borderLeft: '3px solid #2a3a52',
                  borderRadius: 8, padding: 12, marginBottom: 12,
                }}>
                  <div style={{
                    fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', fontWeight: 700,
                    letterSpacing: '0.1em', textTransform: 'uppercase', color: '#8494a7', marginBottom: 8,
                  }}>FULL SLATE RESULTS</div>
                  {tonightBets.map((bet, i) => {
                    const units = bet.profit_units || 0;
                    const isW = units > 0 || bet.result === 'win' || bet.pick_result === 'W';
                    const badgeColor = isW ? '#5A9E72' : '#D4787B';
                    const badgeBg = isW ? 'rgba(90,158,114,0.15)' : 'rgba(212,120,123,0.15)';
                    const sideStr = bet.linked_pick?.side || bet.pick || '';
                    const sideTeam = sideStr.replace(/\s*[+-]?\d+\.?\d*$/, '');
                    const lineVal = bet.line_at_bet ?? bet.linked_pick?.line;
                    const lineStr = lineVal != null ? `${lineVal > 0 ? '+' : ''}${lineVal}` : '';
                    const label = `${teamAbbr(sideTeam)} ${lineStr}`;
                    return (
                      <div key={bet.id || i} style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        padding: '5px 0',
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{
                            fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', fontWeight: 700,
                            padding: '2px 6px', borderRadius: 3, background: badgeBg, color: badgeColor,
                          }}>{isW ? 'W' : 'L'}</span>
                          <span style={{ fontFamily: "'Inter', var(--font-sans), sans-serif", fontSize: '12px', color: '#9aa5b4' }}>{label}</span>
                        </div>
                        <span style={{
                          fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '12px', fontWeight: 600,
                          color: units >= 0 ? '#5A9E72' : '#D4787B',
                        }}>{units >= 0 ? '+' : ''}{units.toFixed(1)}u</span>
                      </div>
                    );
                  })}
                  <div style={{
                    borderTop: '0.5px solid rgba(30,48,80,0.5)', marginTop: 8, paddingTop: 8,
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}>
                    <span style={{ fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '12px', color: '#9aa5b4' }}>
                      {wins}-{losses}
                    </span>
                    <span style={{
                      fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '12px', fontWeight: 600,
                      color: netUnits >= 0 ? '#5A9E72' : '#D4787B',
                    }}>{netUnits >= 0 ? '+' : ''}{netUnits.toFixed(1)}u</span>
                  </div>
                </div>
              );
            })()}

            {/* Pass day recap — when model ran but no signal was issued, or signal was withdrawn */}
            {(() => {
              const isPassRecap = sameDayNight && todayData?.type === 'pass';
              const isRevokedRecap = sameDayNight && todayData?.type === 'pick' && todayData?.result === 'revoked';
              const isPostMidnightNoSignal = postMidnightNight && !hasRecapPick && !(todayData?.type === 'pick');
              const isPostMidnightRevoked = postMidnightNight && nightRecapPick?.result === 'revoked';
              if (!isPassRecap && !isPostMidnightNoSignal && !isRevokedRecap && !isPostMidnightRevoked) return null;
              const gamesCount = todayData?.games_analyzed || totalGames || 0;
              return (
                <div style={{
                  background: '#111e33', border: '0.5px solid #1e3050',
                  borderLeft: '3px solid #6b7a8d',
                  borderRadius: 8, padding: 12, marginBottom: 12,
                }}>
                  <div style={{
                    fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', fontWeight: 700,
                    letterSpacing: '0.1em', textTransform: 'uppercase', color: '#8494a7', marginBottom: 8,
                  }}>PASS DAY</div>
                  <div style={{ fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '12px', color: '#9aa5b4', lineHeight: 1.6 }}>
                    {gamesCount > 0 ? `${gamesCount} games analyzed, none above threshold.` : 'Model analysis complete. No edge above threshold.'} Capital preserved.
                  </div>
                </div>
              );
            })()}

            {/* ── UPCOMING SLATE ── */}
            <div style={{
              fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', fontWeight: 700,
              letterSpacing: '2px', textTransform: 'uppercase', color: '#8494a7',
              padding: '16px 0 8px',
            }}>UPCOMING SLATE</div>

            {/* Countdown Card */}
            <div style={{
              background: '#111e33', border: '0.5px solid #1e3050',
              borderRadius: 8, padding: 12, marginBottom: 12, textAlign: 'center',
            }}>
              <div style={{
                fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', fontWeight: 700,
                letterSpacing: '0.1em', textTransform: 'uppercase', color: '#8494a7', marginBottom: 6,
              }}>EDGES PUBLISH AT {modelRunLabel}</div>
              <div style={{
                fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '28px', fontWeight: 600,
                color: '#e8ecf0', marginBottom: 6,
              }}>{countdown}</div>
              <div style={{
                fontFamily: "'Inter', var(--font-sans), sans-serif", fontSize: '11px', color: '#8494a7',
              }}>Lines are live from 6 books</div>
            </div>

            {/* MI Card */}
            <div onClick={() => onNavigate && onNavigate('picks')} style={{
              padding: '12px 16px', marginBottom: 12,
              background: '#111e33', border: '0.5px solid #1e3050',
              borderRadius: 10, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <div style={{
                width: 32, height: 32, borderRadius: 6,
                background: 'rgba(122,132,148,0.1)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8C9AB0" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 5-9"/>
                </svg>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#E8ECF4' }}>Market Intelligence</div>
                <div style={{ fontSize: '11px', color: '#8C9AB0', marginTop: '1px' }}>
                  {tomorrowGames ? `${tomorrowGames.length} games on the upcoming slate` : 'Upcoming slate'} &middot; Analysis pending
                </div>
              </div>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8C9AB0" strokeWidth="2"><polyline points="9 18 15 12 9 6"/></svg>
            </div>

            {/* Compressed Game List — city names, date + time ET, no badges */}
            {tomorrowGames && tomorrowGames.length > 0 && (
              <div style={{
                background: '#111e33', border: '0.5px solid #1e3050',
                borderRadius: 10, padding: '10px 16px', marginBottom: 12,
              }}>
                <div style={{
                  fontFamily: "'IBM Plex Mono', var(--font-mono), monospace",
                  fontSize: '10px', color: '#8494a7', marginBottom: 8,
                }}>Edges publish after the {modelRunLabel} model run</div>
                {(() => {
                  const datePart = tomorrowDate ? formatDateShort(tomorrowDate) : '';
                  const sorted = [...tomorrowGames].sort((a, b) => (a.game_time_sort || a.time || '').localeCompare(b.game_time_sort || b.time || ''));
                  return sorted.map((g, i) => {
                    const away = teamCity(g.away_team || g.away || '');
                    const home = teamCity(g.home_team || g.home || '');
                    const timeStr = g.time || '';
                    const dateTime = datePart && timeStr ? `${datePart} \u00b7 ${timeStr}` : (timeStr || datePart || 'TBD');
                    return (
                      <div key={g.id || i} style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        padding: '8px 0',
                        borderBottom: i < sorted.length - 1 ? '0.5px solid rgba(30,48,80,0.5)' : 'none',
                      }}>
                        <div style={{ fontFamily: "'Inter', var(--font-sans), sans-serif", fontSize: '13px', fontWeight: 600, color: '#E8ECF4' }}>
                          {away} @ {home}
                        </div>
                        <span style={{ fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '11px', color: '#8C9AB0', flexShrink: 0 }}>
                          {dateTime}
                        </span>
                      </div>
                    );
                  });
                })()}
              </div>
            )}
          </>
        )}

        {/* ═══════════════ STATE 1: PRE-MODEL ═══════════════ */}
        {pageState === 'pre-model' && (
          <>
            {/* Model Status Banner */}
            <div style={{
              background: '#111e33',
              border: '0.5px solid #1e3050',
              borderLeft: '3px solid #5A9E72',
              borderRadius: '10px',
              padding: '16px 18px',
              marginBottom: '16px',
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
                letterSpacing: '0.1em', textTransform: 'uppercase',
                color: '#5A9E72', marginBottom: '6px',
              }}>MODEL RUNS AT {modelRunLabel}</div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '24px', fontWeight: 600,
                color: '#c8cdd4', marginBottom: '8px',
              }}>{countdown}</div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '11px',
                color: '#6b7a8d', lineHeight: 1.5,
              }}>Lines are live from 6 books. Edges publish after the run.</div>
            </div>

            {/* MI Card — pending state */}
            <div style={{
              padding: '12px 16px', marginBottom: '16px',
              background: '#111e33', border: '0.5px solid #1e3050',
              borderRadius: '10px',
              display: 'flex', alignItems: 'center', gap: '10px',
            }}>
              <div style={{
                width: 32, height: 32, borderRadius: 6,
                background: 'rgba(122,132,148,0.1)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#7A8494" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 5-9"/>
                </svg>
              </div>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#E8ECF4' }}>Market Intelligence</div>
                <div style={{ fontSize: '11px', color: '#7A8494', marginTop: '1px' }}>
                  {totalGames > 0 ? `${totalGames} games on today's slate` : "Today's slate"} &middot; Analysis pending
                </div>
              </div>
            </div>

            {/* Section: TODAY'S SLATE */}
            {totalGames > 0 && (
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
                letterSpacing: '0.12em', textTransform: 'uppercase',
                color: '#7A8494', marginBottom: '14px',
              }}>
                TODAY'S SLATE &middot; {today.toUpperCase()}
              </div>
            )}
          </>
        )}


        {/* ═══════════════ STATE 2: PICK DAY ═══════════════ */}
        {pageState === 'pick' && (
          <>
            <OnboardingCard cardId="signal" title="YOUR FIRST SIGNAL">
              The model found a qualifying edge. Tap the card below for the full breakdown: market vs. model line, quant reasoning, and sizing. Use Track to log it to your record.
            </OnboardingCard>
            {/* MI Card — collapsed/expandable (always visible on pick day) */}
            <button
              onClick={() => setMiExpanded(!isMiExpanded)}
              style={{
                width: '100%', padding: '12px 16px', marginBottom: '16px',
                background: '#111e33', border: '0.5px solid #1e3050',
                borderLeft: '3px solid #5A9E72',
                borderRadius: '10px', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 6,
                  background: 'rgba(90,158,114,0.1)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#5A9E72" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 5-9"/>
                  </svg>
                </div>
                <div style={{ textAlign: 'left' }}>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: '#E8ECF4' }}>Market Intelligence</div>
                  <div style={{ fontSize: '11px', color: '#7A8494', marginTop: '1px' }}>
                    {totalGames} games &middot; {edgeCount} edges &middot; {signalCount} signal{signalCount !== 1 ? 's' : ''} &middot; {density}% density
                  </div>
                </div>
              </div>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#7A8494" strokeWidth="2" style={{ transform: isMiExpanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }}><polyline points="9 18 15 12 9 6"/></svg>
            </button>

            {isMiExpanded && (
              <div style={{ marginBottom: '16px' }}>
                <DailyMarketReport report={marketReport} />
              </div>
            )}

            {/* Signal card (only when not revoked/resolved — those have their own cards above) */}
            {!isResolved && !isRevoked && (
              <>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 500,
                  letterSpacing: '1.5px', textTransform: 'uppercase',
                  color: '#7A8494', marginBottom: '8px',
                  display: 'flex', alignItems: 'center', gap: '8px',
                }}>
                  Daily Top Signal
                  {liveScore && (liveScore.state === 'STATUS_IN_PROGRESS' || liveScore.state === 'STATUS_HALFTIME') && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#5A9E72' }}>
                      <span style={{ fontSize: '10px' }}>&middot;</span>
                      <span style={{ width: 5, height: 5, borderRadius: '50%', backgroundColor: '#5A9E72', animation: 'live-pulse 2s ease-in-out infinite', display: 'inline-block' }} />
                      Live
                    </span>
                  )}
                </div>

                {isPro ? (
                  <PickCard pick={todayData} isPro={isPro} liveScore={liveScore} onUpgrade={() => setShowAuth(true)} onNavigate={onNavigate} unitSize={user?.unit_size || 100} onTrack={() => {
                    if (onNavigate) onNavigate('profile', 'bets', {
                      pickToTrack: { id: todayData.id, away_team: todayData.away_team, home_team: todayData.home_team, game_date: todayData.game_date, side: todayData.side, line: todayData.line, edge_pct: todayData.edge_pct, market_odds: todayData.market_odds }
                    });
                  }} />
                ) : (
                  <FreePickNotice onUpgrade={() => { if (user) { if (onNavigate) onNavigate('profile', 'upgrade'); } else { setShowAuth(true); } }} />
                )}
              </>
            )}

            {/* Section: TODAY'S SLATE */}
            {totalGames > 0 && (
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
                letterSpacing: '0.12em', textTransform: 'uppercase',
                color: '#7A8494', marginTop: '28px', marginBottom: '14px',
              }}>TODAY'S SLATE</div>
            )}
          </>
        )}


        {/* ═══════════════ STATE 3: PASS DAY ═══════════════ */}
        {pageState === 'pass' && (
          <>
            {sport === 'nba' && (
              <OnboardingCard cardId="pass" title="PASS DAYS">
                No signal today, but the full analysis is below. Every game's edge, the Daily Market Brief, and the reasoning on each game. This is the most common screen. No Edge. No Pick.
              </OnboardingCard>
            )}
            {/* Pass Day Card */}
            <div style={{
              background: '#0F1424',
              border: '1px solid rgba(212,168,67,0.15)',
              borderLeft: '3px solid #D4A843',
              borderRadius: '10px',
              padding: '24px 20px',
              marginBottom: '16px',
              textAlign: 'center',
            }}>
              <div style={{
                width: 40, height: 40, borderRadius: '50%',
                background: 'rgba(212,168,67,0.1)',
                border: '1px solid rgba(212,168,67,0.25)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 14px',
              }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 700, color: '#D4A843' }}>&mdash;</span>
              </div>
              <div style={{
                fontFamily: 'var(--font-sans)', fontSize: '18px', fontWeight: 700,
                color: '#E8ECF4', marginBottom: '8px',
              }}>No Qualifying Edge</div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '12px',
                color: '#7A8494', lineHeight: 1.5, marginBottom: '18px',
              }}>
                {todayData?.games_analyzed > 0
                  ? `${todayData.games_analyzed} games analyzed. ${
                      todayData.pass_reason
                        ? `${todayData.pass_reason}${todayData.pass_reason.endsWith('.') ? '' : '.'}`
                        : topEdge >= threshold
                          ? `Top edge: ${topEdge}% — did not pass signal filters.`
                          : `Closest edge: ${topEdge}% (below ${threshold}% threshold).`
                    }`
                  : 'Model analysis complete. No edge above threshold.'}
              </div>

              {/* Stats row */}
              <div style={{
                display: 'flex', justifyContent: 'center', gap: '20px',
                marginBottom: '14px',
              }}>
                <PassStat value={todayData?.games_analyzed || totalGames || 0} label="GAMES" />
                <PassStat value={edgeCount} label="EDGES" />
                <PassStat value={signalCount} label="SIGNALS" />
                <PassStat value={`${topEdge}%`} label="TOP EDGE" />
              </div>

              <div style={{
                fontFamily: 'var(--font-serif, Georgia, serif)', fontSize: '13px',
                fontStyle: 'italic', color: '#7A8494',
              }}>Selective by design.</div>
            </div>

            {/* Daily Market Brief — expanded by default */}
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
              letterSpacing: '0.12em', textTransform: 'uppercase',
              color: '#7A8494', marginBottom: '10px',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span>DAILY MARKET BRIEF</span>
              <span style={{ fontWeight: 500, letterSpacing: '0.5px' }}>
                {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', timeZone: 'America/New_York' })}
              </span>
            </div>
            <div style={{ marginBottom: '24px' }}>
              <DailyMarketReport report={marketReport} />
            </div>

            {/* Section: TODAY'S SLATE */}
            {totalGames > 0 && (
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
                letterSpacing: '0.12em', textTransform: 'uppercase',
                color: '#7A8494', marginBottom: '14px',
              }}>TODAY'S SLATE</div>
            )}
          </>
        )}


        {/* ═══════════════ STATE 4: OFF DAY ═══════════════ */}
        {pageState === 'off-day' && (
          <>
            {/* No games header */}
            <div style={{
              fontFamily: 'var(--font-sans)', fontSize: '16px', fontWeight: 700,
              color: '#E8ECF4', marginBottom: '4px',
            }}>No games scheduled today.</div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '12px',
              color: '#7A8494', marginBottom: '20px',
            }}>
              {todayData?.resume_date
                ? <>Next slate: {new Date(todayData.resume_date + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}{todayData.next_game_count ? ` \u00B7 ${todayData.next_game_count} games` : ''}</>
                : `Next ${sportName} slate coming soon`}
            </div>

            {/* SEASON SNAPSHOT */}
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
              letterSpacing: '0.12em', textTransform: 'uppercase',
              color: '#7A8494', marginBottom: '10px',
            }}>SEASON SNAPSHOT</div>
            <div style={{
              background: '#0F1424',
              border: '1px solid rgba(90,158,114,0.12)',
              borderRadius: '10px',
              padding: '20px',
              marginBottom: '16px',
            }}>
              {/* Per-sport stat lines */}
              <div style={{ marginBottom: '16px' }}>
                {(() => {
                  const sportStats = stats || allSportsStats;
                  const lines = [
                    { key: sport, data: sportStats },
                  ];
                  return lines.map(({ key, data }) => {
                    if (!data) return null;
                    const picks = data.total_picks || 0;
                    const wr = data.win_rate || 0;
                    const clv = data.avg_clv;
                    const phase = data.model_phase;
                    return (
                      <div key={key} style={{
                        fontFamily: 'var(--font-mono)', fontSize: '12px',
                        color: '#E8ECF4', lineHeight: 1.8,
                      }}>
                        <span style={{ fontWeight: 700, color: '#5A9E72' }}>{key.toUpperCase()}</span>
                        <span style={{ color: '#7A8494' }}>:</span>{' '}
                        {picks} signal{picks !== 1 ? 's' : ''} &middot; {wr}% win rate &middot;{' '}
                        {phase === 'calibration'
                          ? <span style={{ color: '#D4A843' }}>calibrating</span>
                          : clv != null
                            ? <span style={{ color: clv > 0 ? '#5A9E72' : '#7A8494' }}>{clv > 0 ? '+' : ''}{Number(clv).toFixed(1)} avg CLV</span>
                            : <span style={{ color: '#7A8494' }}>--</span>
                        }
                      </div>
                    );
                  });
                })()}
              </div>

              {/* Stat grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '16px' }}>
                <PortfolioStat value={`${(stats?.pnl || 0) >= 0 ? '+' : ''}${Number(stats?.pnl || 0).toFixed(1)}u`} label="UNITS" highlight />
                <PortfolioStat value={stats?.record || `${stats?.wins || 0}-${stats?.losses || 0}`} label="RECORD" />
                <PortfolioStat value={stats?.selectivity ? `${stats.selectivity}%` : '--'} label="SELECTIVITY" />
              </div>

              {/* Mini equity curve */}
              {stats && (
                <div style={{
                  height: 48, borderRadius: 6,
                  background: 'rgba(90,158,114,0.04)',
                  display: 'flex', alignItems: 'flex-end', padding: '0 4px 4px',
                  overflow: 'hidden',
                }}>
                  <MiniEquityCurve stats={stats} />
                </div>
              )}

              <button
                onClick={() => onNavigate && onNavigate('performance')}
                style={{
                  display: 'block', width: '100%', marginTop: '12px',
                  background: 'none', border: 'none', cursor: 'pointer',
                  fontFamily: 'var(--font-mono)', fontSize: '12px',
                  color: '#5A9E72', textAlign: 'center',
                }}
              >View full results &rarr;</button>
            </div>

            {/* Cross-Sport Nudge */}
            {otherSports.map(otherSport => {
              const label = otherSport.toUpperCase();
              return (
                <button
                  key={otherSport}
                  onClick={() => setSport(otherSport)}
                  style={{
                    width: '100%', padding: '14px 18px', marginBottom: '10px',
                    background: '#0F1424',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '10px', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  }}
                >
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: '#E8ECF4' }}>
                    {label} has games today
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: '#5A9E72', fontWeight: 600 }}>
                    Switch to {label} &rarr;
                  </span>
                </button>
              );
            })}

            {/* CATCH UP — Journal articles (exclude market notes) */}
            {insightsData?.insights?.length > 0 && (() => {
              const evg = insightsData.insights.filter(a => a.category !== 'market_notes');
              if (!evg.length) return null;
              return (
              <>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
                  letterSpacing: '0.12em', textTransform: 'uppercase',
                  color: '#7A8494', marginTop: '8px', marginBottom: '10px',
                }}>CATCH UP</div>
                {evg.slice(0, 2).map((article, i) => {
                  const catLabels = { philosophy: 'Philosophy', discipline: 'Discipline', market_notes: 'Market Notes', how_it_works: 'How It Works', founder_note: 'Signal Notes' };
                  const catLabel = catLabels[article.category] || article.category || 'Journal';
                  return (
                    <button
                      key={article.id || i}
                      onClick={() => onNavigate && onNavigate('insights', null, { insight: article })}
                      style={{
                        width: '100%', padding: '16px', marginBottom: '8px',
                        background: '#0F1424',
                        border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: '12px', cursor: 'pointer',
                        textAlign: 'left', display: 'block',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
                        <span style={{
                          fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                          letterSpacing: '0.05em', textTransform: 'uppercase',
                          color: '#5A9E72', backgroundColor: 'rgba(90,158,114,0.1)',
                          padding: '3px 8px', borderRadius: '4px',
                        }}>{catLabel}</span>
                        <span style={{ fontSize: '10px', color: '#616A8A', fontFamily: 'var(--font-mono)' }}>&middot;</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: '#616A8A' }}>
                          {article.reading_time_minutes || article.read_time || 4} min
                        </span>
                      </div>
                      <div style={{ fontFamily: 'var(--font-sans)', fontSize: '15px', fontWeight: 600, color: '#E8ECF4', lineHeight: 1.4 }}>{article.title}</div>
                    </button>
                  );
                })}
              </>
              );
            })()}
          </>
        )}


        {/* ═══════════════ GAME SLATE (pre-model, pick, pass) ═══════════════ */}
        {/* Always render to drive onGameCount; hidden visually in night/off-day */}
        <div style={pageState === 'night' || pageState === 'off-day' ? { position: 'absolute', width: 0, height: 0, overflow: 'hidden', opacity: 0, pointerEvents: 'none' } : undefined}>
          <GameSlate
            preModel={pageState === 'pre-model'}
            onGameCount={setGameInfo}
          />
        </div>

        {/* Recommended Reads — after today's slate (all states except off-day, which has its own) */}
        {pageState !== 'off-day' && insightsData?.insights?.length > 0 && (() => {
          const evergreen = insightsData.insights.filter(a => a.category !== 'market_notes');
          if (!evergreen.length) return null;
          return (
          <div style={{ marginTop: '20px', marginBottom: '20px' }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
              letterSpacing: '0.12em', textTransform: 'uppercase',
              color: '#7A8494', marginBottom: '10px',
            }}>{pageState === 'pre-model' ? 'WHILE YOU WAIT' : 'RECOMMENDED READS'}</div>
            {evergreen.slice(0, 2).map((article, i) => {
              const catLabels = { philosophy: 'Philosophy', discipline: 'Discipline', market_notes: 'Market Notes', how_it_works: 'How It Works', founder_note: 'Signal Notes' };
              const catLabel = catLabels[article.category] || article.category || 'Journal';
              return (
                <button
                  key={article.id || i}
                  onClick={() => {
                    if (onNavigate) onNavigate('insights', null, { insight: article });
                  }}
                  style={{
                    width: '100%', padding: '16px', marginBottom: '8px',
                    background: '#0F1424',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '12px', cursor: 'pointer',
                    textAlign: 'left', display: 'block',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
                    <span style={{
                      fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
                      letterSpacing: '0.05em', textTransform: 'uppercase',
                      color: '#5A9E72', backgroundColor: 'rgba(90,158,114,0.1)',
                      padding: '3px 8px', borderRadius: '4px',
                    }}>{catLabel}</span>
                    <span style={{ fontSize: '10px', color: '#616A8A', fontFamily: 'var(--font-mono)' }}>&middot;</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: '#616A8A' }}>
                      {article.reading_time_minutes || article.read_time || 4} min
                    </span>
                  </div>
                  <div style={{ fontFamily: 'var(--font-sans)', fontSize: '15px', fontWeight: 600, color: '#E8ECF4', lineHeight: 1.4 }}>{article.title}</div>
                </button>
              );
            })}
          </div>
          );
        })()}

        {/* Portfolio Context Line (pick & pass days) */}
        {(pageState === 'pick' || pageState === 'pass') && stats && (
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px',
            color: '#7A8494', textAlign: 'center',
            marginTop: '20px', lineHeight: 1.6,
          }}>
            Season: {stats.total_picks || 0} signals &middot; {stats.win_rate || 0}% &middot; {stats.avg_clv != null ? `${stats.avg_clv > 0 ? '+' : ''}${Number(stats.avg_clv).toFixed(1)} avg CLV` : ''}
            {isResolved && todayData && (() => {
              const pnl = todayData.profit_units != null ? Number(todayData.profit_units) : (todayData.result === 'win' ? 0.9 : todayData.result === 'push' ? 0 : -1.0);
              const wl = todayData.result === 'win' ? 'W' : todayData.result === 'push' ? 'P' : 'L';
              return <span> &middot; Tonight: {wl} {pnl >= 0 ? '+' : ''}{pnl.toFixed(1)}u</span>;
            })()}
            {pageState === 'pass' && (
              <div style={{ marginTop: '4px' }}>
                Capital preserved today: +${(stats.avg_unit_size || 100)} from avoided sub-threshold bets
              </div>
            )}
          </div>
        )}

        {error && (
          <InlineError title="Data delay" message="Unable to load today's analysis. This typically resolves within a few minutes." />
        )}
      </div>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
      </PullToRefresh>
    </div>
  );
}


// ═══════════════ SUB-COMPONENTS ═══════════════

function PassStat({ value, label }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '18px', fontWeight: 700, color: '#E8ECF4', fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 500, letterSpacing: '0.08em', color: '#7A8494', marginTop: '2px' }}>{label}</div>
    </div>
  );
}

function PortfolioStat({ value, label, highlight }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '22px', fontWeight: 700, fontVariantNumeric: 'tabular-nums', color: highlight ? '#5A9E72' : '#E8ECF4' }}>{value}</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 500, letterSpacing: '0.08em', color: '#7A8494', marginTop: '4px' }}>{label}</div>
    </div>
  );
}

function MiniEquityCurve({ stats }) {
  const w = 340, h = 40;
  const pnl = Number(stats?.pnl || 0);
  if (pnl === 0) return <div style={{ width: '100%', height: '100%' }} />;
  const points = [];
  const totalPicks = stats?.total_picks || 1;
  for (let i = 0; i <= 10; i++) {
    const x = (i / 10) * w;
    const y = h - (h * 0.3) - (pnl > 0 ? 1 : -1) * Math.sin((i / 10) * Math.PI) * (h * 0.4);
    points.push(`${x},${y}`);
  }
  return (
    <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: 'block' }}>
      <polyline points={points.join(' ')} fill="none" stroke="#5A9E72" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function RevokedPassCard({ pick, onViewDetails }) {
  const sideLabel = pick.side && pick.line != null && pick.side.includes(String(Math.abs(pick.line)))
    ? pick.side
    : `${pick.side} ${pick.line > 0 ? '+' : ''}${pick.line}`;
  return (
    <div onClick={onViewDetails} style={{
      background: '#0F1424',
      border: '1px solid rgba(142,154,175,0.15)',
      borderLeft: '3px solid #7A8494',
      borderRadius: '10px',
      padding: '12px 16px',
      marginBottom: '14px',
      cursor: 'pointer',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: 0 }}>
        <svg viewBox="0 0 24 24" width="16" height="16" stroke="#7A8494" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontFamily: "'IBM Plex Mono', var(--font-mono), monospace", fontSize: '10px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#7A8494', marginBottom: '2px' }}>Signal Withdrawn</div>
          <div style={{ fontFamily: "'Inter', var(--font-sans), sans-serif", fontSize: '13px', fontWeight: 600, color: '#E8ECF4', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {sideLabel} <span style={{ color: '#7A8494', fontWeight: 400, fontSize: '11px' }}>&middot; {pick.away_team} @ {pick.home_team}</span>
          </div>
        </div>
      </div>
      <svg viewBox="0 0 24 24" width="14" height="14" stroke="#7A8494" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginLeft: 8 }}>
        <polyline points="9 18 15 12 9 6"/>
      </svg>
    </div>
  );
}

const PROCESS_COPY = {
  win: [
    'Process unchanged. Next signal when the edge is there.',
    'Edge confirmed. Same system tomorrow.',
    'The model saw value. The result confirmed it.',
  ],
  loss: [
    'Outcome within expected range. One result does not define a process.',
    'Variance, not signal. The process continues.',
    'One data point. The sample grows.',
  ],
  push: [
    'Landed on the number. Stake returned.',
    'Push. The spread landed on the number. Next signal when the edge is there.',
  ],
};

function getProcessCopy(result, pickId) {
  const copies = PROCESS_COPY[result] || PROCESS_COPY.loss;
  const idx = pickId ? Math.abs(typeof pickId === 'number' ? pickId : [...String(pickId)].reduce((a, c) => a + c.charCodeAt(0), 0)) % copies.length : 0;
  return copies[idx];
}

function clvNarrative(pick) {
  const clvVal = pick.clv != null ? parseFloat(pick.clv) : (pick.closing_spread != null && pick.line != null ? parseFloat(pick.line) - parseFloat(pick.closing_spread) : null);
  if (clvVal == null) return null;
  const isWin = pick.result === 'win';
  const isLoss = pick.result === 'loss';
  const lineStr = pick.line > 0 ? `+${pick.line}` : `${pick.line}`;
  const closeStr = pick.closing_spread != null ? (pick.closing_spread > 0 ? `+${pick.closing_spread}` : `${pick.closing_spread}`) : lineStr;
  const movement = Math.abs(clvVal).toFixed(1);

  let narrative;
  if (clvVal > 0 && isLoss) {
    narrative = 'Positive CLV despite the loss.';
  } else if (clvVal < 0 && isWin) {
    narrative = 'Win captured, but closing line moved away. Edge may have been overestimated.';
  } else if (clvVal > 0) {
    narrative = 'The market agreed with the pricing.';
  } else if (clvVal < 0) {
    narrative = 'Market moved against the position.';
  } else {
    narrative = 'Closing line matched the pick line.';
  }

  return { clvVal, lineStr, closeStr, movement, narrative };
}

function ResolvedPickBanner({ pick, onViewDetails, onDismiss, onShare }) {
  const isWin = pick.result === 'win';
  const isLoss = pick.result === 'loss';
  const isPush = pick.result === 'push';

  const brandGreen = '#5A9E72';
  const neutral = '#616a8a';
  const muted = '#4a5274';

  const borderColor = isWin ? brandGreen : muted;
  const dotColor = isWin ? brandGreen : neutral;
  const labelColor = isWin ? brandGreen : neutral;
  const statValColor = isWin ? brandGreen : '#9098b3';

  const profitDisplay = pick.profit_units != null ? `${pick.profit_units >= 0 ? '+' : ''}${Number(pick.profit_units).toFixed(1)}u` : isPush ? '0.0u' : isWin ? '+0.9u' : '-1.0u';
  const edgePct = pick.edge_pct || '--';
  const modelProb = pick.edge_pct ? `${Math.round(50 + pick.edge_pct)}%` : '--';
  const sideDisplay = pick.side && pick.line != null && pick.side.includes(String(Math.abs(pick.line))) ? pick.side : `${pick.side} ${pick.line > 0 ? '+' : ''}${pick.line}`;
  const edgeDisplay = pick.edge_pct != null ? `+${Number(pick.edge_pct).toFixed(1)}%` : null;
  const resultLabel = isPush ? 'OUTCOME RESOLVED \u00B7 PUSH' : isWin ? 'OUTCOME RESOLVED \u00B7 WIN' : 'OUTCOME RESOLVED \u00B7 LOSS';
  const reviewText = getProcessCopy(pick.result, pick.id);
  const clv = clvNarrative(pick);

  const scoreDisplay = (pick.home_score != null && pick.away_score != null)
    ? { away: pick.away_team, home: pick.home_team, awayScore: pick.away_score, homeScore: pick.home_score }
    : null;

  return (
    <div style={{
      background: 'var(--surface-1)', border: '1px solid var(--color-border)',
      borderLeft: `3px solid ${borderColor}`,
      borderRadius: '12px', overflow: 'hidden', marginBottom: 'var(--space-md)',
    }}>
      {/* Header: OUTCOME RESOLVED · WIN/LOSS/PUSH + dismiss */}
      <div style={{ padding: '20px 20px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '0.12em', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '6px', color: labelColor }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: dotColor, flexShrink: 0 }} />
          {resultLabel}
        </div>
        {onDismiss && <button onClick={(e) => { e.stopPropagation(); onDismiss(); }} style={{ background: 'none', border: 'none', color: '#4a5274', cursor: 'pointer', fontSize: '16px', padding: '4px', lineHeight: 1 }} aria-label="Dismiss">&times;</button>}
      </div>

      {/* Side + Edge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '8px 20px 0' }}>
        <div style={{ fontFamily: 'var(--font-sans)', fontSize: '17px', fontWeight: 600, color: 'var(--text-primary)' }}>{sideDisplay}</div>
        {edgeDisplay && <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 500, color: brandGreen }}>{edgeDisplay}</div>}
      </div>

      {/* Final Score Bar */}
      {scoreDisplay && (
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: 'rgba(74,85,104,0.1)', border: '0.5px solid rgba(74,85,104,0.2)',
          borderRadius: 5, padding: '6px 10px', margin: '10px 20px 0',
        }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', color: '#4a5568' }}>FINAL</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'var(--font-mono)' }}>
            <span style={{ fontSize: '10px', color: '#7A8494' }}>{teamAbbr(scoreDisplay.away)}</span>
            <span style={{ fontSize: '15px', fontWeight: 500, color: '#E8ECF4' }}>{scoreDisplay.awayScore}</span>
            <span style={{ fontSize: '10px', color: '#4a5568' }}>&middot;</span>
            <span style={{ fontSize: '10px', color: '#7A8494' }}>{teamAbbr(scoreDisplay.home)}</span>
            <span style={{ fontSize: '15px', fontWeight: 500, color: '#E8ECF4' }}>{scoreDisplay.homeScore}</span>
          </div>
        </div>
      )}

      {/* Process Copy */}
      <div style={{ fontFamily: 'var(--font-sans)', fontSize: '13px', color: '#616a8a', padding: '10px 20px 0', lineHeight: 1.55, fontStyle: 'italic' }}>{reviewText}</div>

      {/* Stats Grid: P&L | Edge at Entry | Model Prob */}
      <div style={{ display: 'flex', margin: '16px 20px 0', border: '1px solid var(--color-border)', borderRadius: '8px', overflow: 'hidden' }}>
        {[{ val: profitDisplay, lbl: 'P&L' }, { val: typeof edgePct === 'number' ? `${edgePct}%` : edgePct, lbl: 'EDGE AT ENTRY' }, { val: modelProb, lbl: 'MODEL PROB' }].map((s, i) => (
          <div key={i} style={{ flex: 1, padding: '10px 12px', textAlign: 'center', borderRight: i < 2 ? '1px solid var(--color-border)' : 'none' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 500, color: i === 0 ? statValColor : '#9098b3' }}>{s.val}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', letterSpacing: '0.1em', textTransform: 'uppercase', color: '#4a5274', marginTop: '2px' }}>{s.lbl}</div>
          </div>
        ))}
      </div>

      {/* CLV Block */}
      {clv && (
        <div style={{
          margin: '12px 20px 0', padding: '10px 12px',
          background: 'rgba(15,20,36,0.6)', border: '1px solid var(--color-border)', borderRadius: '8px',
        }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#9098b3', lineHeight: 1.6 }}>
            CLV: Pick at {clv.lineStr}, closed at {clv.closeStr}
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#9098b3', lineHeight: 1.6 }}>
            Line moved {clv.movement} pts {clv.clvVal > 0 ? 'toward' : 'against'} model.
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px', lineHeight: 1.6, marginTop: '2px',
            color: clv.clvVal > 0 ? brandGreen : clv.clvVal < 0 ? '#9098b3' : '#9098b3',
          }}>
            {clv.narrative}
          </div>
        </div>
      )}

      {/* Footer: View outcome log + Share Result */}
      <div style={{ padding: '0 20px', marginTop: '14px' }}>
        <div onClick={onViewDetails} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
          padding: '12px 0',
          fontFamily: 'var(--font-mono)', fontSize: '11px', letterSpacing: '0.04em', color: brandGreen, cursor: 'pointer',
        }}>
          View outcome log &rarr;
        </div>
        {onShare && (
          <button onClick={(e) => { e.stopPropagation(); onShare(pick); }} style={{
            width: '100%', padding: '10px', marginBottom: '16px',
            borderRadius: '8px', cursor: 'pointer',
            fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '11px',
            letterSpacing: '0.06em', textTransform: 'uppercase',
            color: '#9098b3', background: 'transparent',
            border: '1px solid var(--color-border)',
          }}>
            SHARE RESULT
          </button>
        )}
        {!onShare && <div style={{ height: '4px' }} />}
      </div>
    </div>
  );
}

function PushPromptInline({ onEnable, onDismiss }) {
  const [loading, setLoading] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;
  return (
    <div style={{
      background: '#111e33', border: '0.5px solid #1e3050',
      borderLeft: '3px solid #5A9E72', borderRadius: '8px',
      padding: '12px 14px', marginBottom: '12px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px',
    }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '12px', color: '#e8ecf0', lineHeight: '1.5', fontWeight: 500 }}>
          Want to know the moment the model finds an edge?
        </div>
      </div>
      <button
        onClick={async () => {
          setLoading(true);
          await onEnable();
          setLoading(false);
          setDismissed(true);
          if (onDismiss) onDismiss();
        }}
        disabled={loading}
        style={{
          padding: '8px 14px', borderRadius: '6px',
          border: '1.5px solid #5A9E72', background: 'transparent',
          color: '#5A9E72', fontFamily: 'var(--font-mono)',
          fontSize: '10px', fontWeight: 600, letterSpacing: '0.5px',
          cursor: 'pointer', whiteSpace: 'nowrap',
          opacity: loading ? 0.6 : 1,
        }}
      >
        {loading ? 'Enabling...' : 'Enable Notifications'}
      </button>
    </div>
  );
}

function FreePickNotice({ onUpgrade, resolved, pick }) {
  return (
    <div style={{ backgroundColor: 'var(--surface-1)', border: '1px solid var(--color-border)', borderRadius: '16px', padding: '24px 20px' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--color-signal)', marginBottom: '14px' }}>QUALIFIED EDGE DETECTED</div>
      {pick && (
        <>
          <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '1.6px', color: 'rgba(169,180,207,0.85)', textTransform: 'uppercase', marginBottom: '8px' }}>
            {pick.away_team || 'Away'} vs {pick.home_team || 'Home'}
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-tertiary)', marginBottom: '16px' }}>
            {pick.game_date} · {pick.start_time ? new Date(pick.start_time).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/New_York' }) + ' ET' : ''}
          </div>
        </>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '1px', background: 'rgba(255,255,255,0.06)', borderRadius: '6px', overflow: 'hidden', marginBottom: '16px' }}>
        {['SIDE', 'LINE', 'EDGE', 'SIZE'].map(label => (
          <div key={label} style={{ background: 'var(--surface-1)', padding: '10px 8px', textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', letterSpacing: '1px', color: 'var(--text-tertiary)', marginBottom: '6px' }}>{label}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 500, color: '#4a5a6e' }}>[Pro]</div>
          </div>
        ))}
      </div>
      <button onClick={() => window.open('https://sharppicks.ai/#pricing', '_blank')} style={{ width: '100%', padding: '12px', borderRadius: '6px', border: '1.5px solid #5A9E72', background: 'transparent', color: '#5A9E72', fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 600, letterSpacing: '1px', cursor: 'pointer', textAlign: 'center' }}>View Plans</button>
      <div style={{ textAlign: 'center', marginTop: '8px', fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-tertiary)' }}>Full details at sharppicks.ai</div>
    </div>
  );
}

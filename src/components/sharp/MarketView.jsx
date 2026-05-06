import { useState, useMemo, useEffect, useCallback } from 'react';
import { Capacitor } from '@capacitor/core';
import { useAuth } from '../../hooks/useAuth';
import { useApi } from '../../hooks/useApi';
import { useSport, sportQuery } from '../../hooks/useSport';
import PullToRefresh from '../shared/PullToRefresh';
import DailyMarketReport from './DailyMarketReport';
import { trackEvent } from '../../utils/eventTracker';
import teamAbbr from '../../utils/teamAbbr';
import sportDisplay from '../../utils/sportDisplay';
import openSignup from '../../utils/openSignup';
import inferGameStatus from '../../utils/inferGameStatus';

const PROD_URL = 'https://app.sharppicks.ai';
const MV_API_BASE = Capacitor.isNativePlatform() ? PROD_URL : '';

const pulseKeyframes = `
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}`;
if (typeof document !== 'undefined' && !document.getElementById('sp-pulse-anim')) {
  const style = document.createElement('style');
  style.id = 'sp-pulse-anim';
  style.textContent = pulseKeyframes;
  document.head.appendChild(style);
}

function fmtSpread(val) {
  if (val == null || val === '') return '—';
  const n = parseFloat(val);
  return n > 0 ? `+${n}` : `${n}`;
}

function fmtML(val) {
  if (val == null || val === '') return '—';
  const n = parseInt(val, 10);
  return n > 0 ? `+${n}` : `${n}`;
}

function fmtTotal(val) {
  if (val == null || val === '') return 'Pending';
  const n = parseFloat(val);
  return Number.isInteger(n) ? `${n}` : n.toFixed(1);
}

// `line` is the picked-side spread (negative when picked side is favored,
// positive when dog), so the same formula works for home and away picks.
function computeLiveCover(pickSide, line, homeScore, awayScore) {
  if (line == null || pickSide == null) return null;
  const isHomePick = String(pickSide).toLowerCase().includes('home');
  const margin = isHomePick ? (homeScore - awayScore) : (awayScore - homeScore);
  const adjusted = margin + parseFloat(line);
  return {
    status: adjusted > 0 ? 'covering' : 'not_covering',
    margin: Math.round(Math.abs(adjusted) * 10) / 10,
  };
}

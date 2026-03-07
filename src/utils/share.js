import { Capacitor } from '@capacitor/core';

const API_BASE = Capacitor.isNativePlatform()
  ? 'https://app.sharppicks.ai'
  : '';

function fmtSpread(val) {
  if (val == null) return '';
  const n = parseFloat(val);
  if (Number.isInteger(n)) return n > 0 ? `+${n}` : `${n}`;
  return n > 0 ? `+${n.toFixed(1)}` : `${n.toFixed(1)}`;
}

export function signalShareText(pick) {
  const model = pick.cover_prob || pick.model_confidence;
  const market = pick.implied_prob;
  const modelPct = model ? `${(model * 100).toFixed(1)}%` : '';
  const marketPct = market ? `${(market * 100).toFixed(1)}%` : '';
  const edge = pick.edge_pct ? `+${parseFloat(pick.edge_pct).toFixed(1)}%` : '';
  const probs = modelPct && marketPct ? `Model: ${modelPct} vs Market: ${marketPct}` : '';

  return [
    'SharpPicks Signal',
    '',
    pick.side || '',
    [edge ? `Edge: ${edge}` : '', probs].filter(Boolean).join(' | '),
    '',
    'Selective by design.',
    'sharppicks.ai',
  ].filter(l => l !== undefined).join('\n');
}

export function resultShareText(pick) {
  const isWin = pick.result === 'win';
  const isPush = pick.result === 'push';
  const icon = isWin ? '✔' : (isPush ? '—' : '✘');
  const label = (pick.result || 'PENDING').toUpperCase();
  const units = pick.profit_units != null ? `${pick.profit_units > 0 ? '+' : ''}${parseFloat(pick.profit_units).toFixed(1)}u` : '';
  const clv = pick.clv != null ? `CLV: ${pick.clv > 0 ? '+' : ''}${parseFloat(pick.clv).toFixed(1)}` : '';
  const edge = pick.edge_pct ? `Edge: +${parseFloat(pick.edge_pct).toFixed(1)}%` : '';

  return [
    'SharpPicks Result',
    '',
    `${icon} ${pick.side || ''} | ${label}${units ? ` ${units}` : ''}`,
    [clv, edge].filter(Boolean).join(' | '),
    '',
    'Proof over hype.',
    'sharppicks.ai',
  ].join('\n');
}

export function userResultsShareText(stats) {
  const pnl = stats?.pnl != null ? `${stats.pnl >= 0 ? '+' : ''}${stats.pnl}u profit` : '';
  const roi = stats?.roi != null ? `${stats.roi}% ROI` : '';
  const record = stats?.record || '';
  const grade = stats?.discipline_grade || '';

  return [
    'My SharpPicks results:',
    '',
    [pnl, roi, record ? `${record} record` : ''].filter(Boolean).join(' | '),
    grade ? `Discipline Score: ${grade}` : '',
    '',
    'sharppicks.ai',
  ].filter(Boolean).join('\n');
}

export function marketReportShareText(data) {
  return [
    'SharpPicks Market Report',
    '',
    `${data.games_analyzed} games analyzed. ${data.edges_detected} edges detected. ${data.qualified_signals} signal${data.qualified_signals !== 1 ? 's' : ''}.`,
    '',
    data.qualified_signals === 0 ? 'Passing is a position.' : 'Selective by design.',
    'sharppicks.ai',
  ].join('\n');
}

export async function shareCard({ cardUrl, text, title = 'SharpPicks' }) {
  try {
    const fullUrl = `${API_BASE}${cardUrl}`;
    const response = await fetch(fullUrl);
    if (!response.ok) throw new Error('Failed to fetch card image');

    const blob = await response.blob();
    const file = new File([blob], 'sharppicks.png', { type: 'image/png' });

    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({ text, files: [file] });
      return true;
    }

    if (navigator.share) {
      await navigator.share({ text, url: 'https://sharppicks.ai' });
      return true;
    }

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sharppicks.png';
    a.click();
    URL.revokeObjectURL(url);
    return true;
  } catch (e) {
    if (e.name === 'AbortError') return false;
    console.error('Share failed:', e);
    return false;
  }
}

// SharpPicks Command Center — admin dashboard.
// Ported wholesale from docs/phase-3/command-center-mockup.html
// Tab toggling, segment chips, compare/internal toggles, Chart.js defaults,
// and chart definitions are the mockup's locked behavior.
//
// Live data overlay (bindLiveData, below) fetches /api/admin/metrics on
// page load and replaces specific Math.random / hardcoded mockup values
// with real Phase 2 data where available. Sources still using mockup
// placeholders are flagged with TODO comments and become follow-up work
// (Phase 3 spec steps 3.5/3.6/3.7).

  function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    const tabBtn = document.querySelector(`.tab[data-tab="${tabName}"]`);
    if (tabBtn) tabBtn.classList.add('active');
    const panel = document.getElementById('panel-' + tabName);
    if (panel) panel.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Deep-link cards (e.g. "View full user activity → users tab")
  document.querySelectorAll('[data-deep-link]').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      switchTab(link.dataset.deepLink);
    });
  });

  // Toggle interactions
  document.querySelector('.toggle-switch').addEventListener('click', function() {
    this.classList.toggle('on');
  });
  document.querySelector('.compare-toggle').addEventListener('click', function() {
    const states = ['vs 7d ago', 'vs 30d ago'];
    const current = this.textContent.trim();
    const next = states[(states.indexOf(current) + 1) % states.length];
    this.textContent = next;
  });

  // Segment chip toggles — single-select within each parent .segment-chips group
  document.querySelectorAll('.segment-chips').forEach(group => {
    group.querySelectorAll('.segment-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        group.querySelectorAll('.segment-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
      });
    });
  });

  // Chart defaults
  Chart.defaults.color = '#8B92A5';
  Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
  Chart.defaults.font.family = "'JetBrains Mono', monospace";
  Chart.defaults.font.size = 10;

  const baseGrid = {
    grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false },
    ticks: { color: '#525a6e', font: { size: 9 } }
  };
  const noLegend = { plugins: { legend: { display: false } } };

  // MRR chart - stacked area, Stripe + RevenueCat
  new Chart(document.getElementById('chart-mrr'), {
    type: 'line',
    data: {
      labels: Array.from({length: 90}, (_, i) => i),
      datasets: [
        {
          label: 'Stripe',
          data: Array.from({length: 90}, (_, i) => 1100 + i * 4 + Math.sin(i/8)*30),
          borderColor: '#4F86F7',
          backgroundColor: 'rgba(79, 134, 247, 0.12)',
          fill: 'origin',
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 1.5,
        },
        {
          label: 'RevenueCat',
          data: Array.from({length: 90}, (_, i) => 1100 + i * 4 + 600 + i * 2.8 + Math.cos(i/6)*40),
          borderColor: '#34D399',
          backgroundColor: 'rgba(52, 211, 153, 0.12)',
          fill: '-1',
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 1.5,
        },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: true, position: 'bottom', labels: { boxWidth: 8, boxHeight: 8, padding: 12, font: { size: 10 } } } },
      scales: { x: { ...baseGrid, ticks: { display: false } }, y: { ...baseGrid, ticks: { ...baseGrid.ticks, callback: v => '$' + v } } }
    }
  });

  // DAU chart
  new Chart(document.getElementById('chart-dau'), {
    type: 'bar',
    data: {
      labels: Array.from({length: 30}, (_, i) => i),
      datasets: [{
        data: Array.from({length: 30}, () => 30 + Math.floor(Math.random() * 30)),
        backgroundColor: '#4F86F7',
        borderWidth: 0,
        barPercentage: 0.7,
        categoryPercentage: 0.85,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, ...noLegend,
      scales: { x: { ...baseGrid, ticks: { display: false } }, y: { ...baseGrid, beginAtZero: true } }
    }
  });

  // Traffic
  new Chart(document.getElementById('chart-traffic'), {
    type: 'line',
    data: {
      labels: Array.from({length: 30}, (_, i) => i),
      datasets: [{
        data: Array.from({length: 30}, (_, i) => 350 + Math.sin(i/5) * 80 + Math.random() * 40),
        borderColor: '#4F86F7',
        backgroundColor: 'rgba(79, 134, 247, 0.08)',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 1.5,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, ...noLegend,
      scales: { x: { ...baseGrid, ticks: { display: false } }, y: { ...baseGrid, beginAtZero: true } }
    }
  });

  // Users tab — DAU 90d (bigger window than Command tab's 30d)
  new Chart(document.getElementById('chart-users-dau'), {
    type: 'bar',
    data: {
      labels: Array.from({length: 90}, (_, i) => i),
      datasets: [{
        data: Array.from({length: 90}, (_, i) => {
          // bake in the april 18 lift
          const base = 28 + Math.floor(Math.random() * 18);
          return i > 60 ? base + 10 + Math.floor(Math.random() * 8) : base;
        }),
        backgroundColor: (ctx) => ctx.dataIndex > 60 ? '#34D399' : '#4F86F7',
        borderWidth: 0,
        barPercentage: 0.85,
        categoryPercentage: 0.95,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, ...noLegend,
      scales: { x: { ...baseGrid, ticks: { display: false } }, y: { ...baseGrid, beginAtZero: true } }
    }
  });

  // Users tab — login frequency histogram
  new Chart(document.getElementById('chart-login-freq'), {
    type: 'bar',
    data: {
      labels: ['0', '1', '2-3', '4-5', '6-9', '10-14', '15-19', '20-29', '30+'],
      datasets: [{
        data: [72, 86, 132, 88, 56, 38, 18, 8, 2],
        backgroundColor: (ctx) => {
          // Highlight power user tiers (15+) in green
          return ctx.dataIndex >= 6 ? '#34D399' : '#4F86F7';
        },
        borderWidth: 0,
        barPercentage: 0.85,
        categoryPercentage: 0.95,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, ...noLegend,
      scales: {
        x: { ...baseGrid, grid: { display: false } },
        y: { ...baseGrid, beginAtZero: true }
      }
    }
  });

  // Win rate
  new Chart(document.getElementById('chart-winrate'), {
    type: 'line',
    data: {
      labels: Array.from({length: 90}, (_, i) => i),
      datasets: [
        {
          label: 'NBA (rolling 14d)',
          data: Array.from({length: 90}, (_, i) => 50 + Math.sin(i/12) * 6 + 4),
          borderColor: '#4F86F7',
          tension: 0.4,
          pointRadius: 0,
          borderWidth: 2,
          fill: false,
        },
        {
          label: 'MLB (rolling 14d)',
          data: Array.from({length: 90}, (_, i) => i < 50 ? null : 50 + Math.cos(i/8) * 8 + 6),
          borderColor: '#34D399',
          borderDash: [4, 4],
          tension: 0.4,
          pointRadius: 0,
          borderWidth: 2,
          fill: false,
        },
        {
          label: 'Break-even (52.4%)',
          data: Array.from({length: 90}, () => 52.4),
          borderColor: '#525a6e',
          borderDash: [2, 4],
          pointRadius: 0,
          borderWidth: 1,
          fill: false,
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: true, position: 'bottom', labels: { boxWidth: 8, boxHeight: 8, padding: 12, font: { size: 10 } } } },
      scales: { x: { ...baseGrid, ticks: { display: false } }, y: { ...baseGrid, min: 40, max: 65, ticks: { ...baseGrid.ticks, callback: v => v + '%' } } }
    }
  });

  // MEI tier hit rate
  new Chart(document.getElementById('chart-meihit'), {
    type: 'bar',
    data: {
      labels: ['0.50-0.65', '0.65-0.75', '0.75-0.85', '≥ 0.85'],
      datasets: [{
        data: [49, 52, 56, 61],
        backgroundColor: ['#525a6e', '#525a6e', '#4F86F7', '#34D399'],
        borderWidth: 0,
        barPercentage: 0.6,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, ...noLegend,
      scales: {
        x: { ...baseGrid, grid: { display: false } },
        y: { ...baseGrid, min: 40, max: 70, ticks: { ...baseGrid.ticks, callback: v => v + '%' } }
      }
    }
  });

  // Calibration plots
  function calibrationData(jitter) {
    const buckets = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9];
    return buckets.map(p => ({ x: p, y: p + (Math.random() - 0.5) * jitter }));
  }
  function calibrationConfig(data, color) {
    return {
      type: 'scatter',
      data: {
        datasets: [
          {
            label: 'Observed',
            data: data,
            backgroundColor: color,
            borderColor: color,
            pointRadius: 4,
            pointHoverRadius: 5,
          },
          {
            label: 'Perfect calibration',
            type: 'line',
            data: [{x:0.5,y:0.5},{x:0.9,y:0.9}],
            borderColor: '#525a6e',
            borderDash: [3, 3],
            pointRadius: 0,
            borderWidth: 1,
            fill: false,
          }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false, ...noLegend,
        scales: {
          x: { ...baseGrid, type: 'linear', min: 0.45, max: 0.95, ticks: { ...baseGrid.ticks, stepSize: 0.1, callback: v => v.toFixed(1) } },
          y: { ...baseGrid, type: 'linear', min: 0.45, max: 0.95, ticks: { ...baseGrid.ticks, stepSize: 0.1, callback: v => v.toFixed(1) } }
        }
      }
    };
  }
  new Chart(document.getElementById('chart-cal-nba'), calibrationConfig(calibrationData(0.04), '#4F86F7'));
  new Chart(document.getElementById('chart-cal-mlb'), calibrationConfig(calibrationData(0.08), '#34D399'));

  // MEI distribution
  new Chart(document.getElementById('chart-mei'), {
    type: 'bar',
    data: {
      labels: ['0.30', '0.35', '0.40', '0.45', '0.50', '0.55', '0.60', '0.65', '0.70', '0.75', '0.80', '0.85', '0.90', '0.95'],
      datasets: [{
        data: [2, 5, 9, 14, 22, 28, 30, 26, 18, 11, 6, 3, 1, 1],
        backgroundColor: (ctx) => ctx.dataIndex >= 11 ? '#34D399' : '#4F86F7',
        borderWidth: 0,
        barPercentage: 0.85,
        categoryPercentage: 0.95,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, ...noLegend,
      scales: { x: { ...baseGrid, grid: { display: false } }, y: { ...baseGrid, beginAtZero: true } }
    }
  });

  // Latency
  new Chart(document.getElementById('chart-latency'), {
    type: 'line',
    data: {
      labels: Array.from({length: 168}, (_, i) => i),
      datasets: [
        {
          label: 'p50',
          data: Array.from({length: 168}, () => 80 + Math.random() * 40),
          borderColor: '#4F86F7',
          tension: 0.3, pointRadius: 0, borderWidth: 1.5, fill: false,
        },
        {
          label: 'p95',
          data: Array.from({length: 168}, () => 280 + Math.random() * 80),
          borderColor: '#E4A03B',
          tension: 0.3, pointRadius: 0, borderWidth: 1.5, fill: false,
        },
        {
          label: 'p99',
          data: Array.from({length: 168}, () => 520 + Math.random() * 200),
          borderColor: '#E48181',
          tension: 0.3, pointRadius: 0, borderWidth: 1.5, fill: false,
        },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: true, position: 'bottom', labels: { boxWidth: 8, boxHeight: 8, padding: 12, font: { size: 10 } } } },
      scales: { x: { ...baseGrid, ticks: { display: false } }, y: { ...baseGrid, beginAtZero: true, ticks: { ...baseGrid.ticks, callback: v => v + 'ms' } } }
    }
  });

// ─────────────────────────────────────────────────────────────────────────
// Live data overlay — wires real /api/admin/metrics into the rendered DOM.
// Runs after the mockup's Chart.defaults + chart constructors above. Each
// updater is defensive: if the API source errored or is missing, the
// mockup's placeholder stays visible (with a stale indicator).
// ─────────────────────────────────────────────────────────────────────────

const SP_FMT = {
  money: (cents) => '$' + (cents / 100).toLocaleString(undefined, { maximumFractionDigits: 0 }),
  num:   (n) => (n == null ? '—' : n.toLocaleString()),
  pct:   (n) => (n == null ? '—' : n.toFixed(1) + '%'),
};

function setStat(label, value) {
  // Find a .stat-row whose .label text matches `label` (case-insensitive),
  // and replace its .value text node while preserving any .value-suffix.
  const rows = document.querySelectorAll('.stat-row');
  for (const row of rows) {
    const lbl = row.querySelector('.label');
    if (!lbl) continue;
    if (lbl.textContent.trim().toLowerCase() !== label.toLowerCase()) continue;
    const val = row.querySelector('.value');
    if (!val) continue;
    const suffix = val.querySelector('.value-suffix');
    val.textContent = value;
    if (suffix) val.appendChild(suffix);
    return true;
  }
  return false;
}

function setMovedRow(label, value, deltaText, deltaClass) {
  const rows = document.querySelectorAll('.moved-row');
  for (const row of rows) {
    const lbl = row.querySelector('.moved-label');
    if (!lbl || lbl.textContent.trim().toLowerCase() !== label.toLowerCase()) continue;
    const val = row.querySelector('.moved-value');
    const delta = row.querySelector('.moved-delta');
    if (val) val.textContent = value;
    if (delta && deltaText !== undefined) {
      delta.textContent = deltaText;
      delta.className = 'moved-delta' + (deltaClass ? ' ' + deltaClass : '');
    }
    return true;
  }
  return false;
}

function bindLiveData(metrics) {
  if (!metrics) return;

  // -- Headline + actions (Phase 3.3) --
  // services/headline.py emits {sentence, color} for the headline and a
  // sorted list of {message, priority} for the actions. Replace the
  // mockup's hardcoded copy in-place.
  const headline = metrics.headline;
  if (headline && headline.sentence) {
    const headlineEl = document.querySelector('#panel-command .headline');
    if (headlineEl) headlineEl.textContent = headline.sentence;
  }

  const actions = Array.isArray(metrics.actions) ? metrics.actions : [];
  if (actions.length) {
    const actionsEl = document.querySelector('#panel-command .actions');
    if (actionsEl) {
      actionsEl.innerHTML = '';
      const PRIORITY_CLASS = { warn: '', info: 'priority-info', good: 'priority-good' };
      actions.forEach(a => {
        const p = document.createElement('p');
        p.className = ('action ' + (PRIORITY_CLASS[a.priority] || '')).trim();
        p.textContent = a.message;
        actionsEl.appendChild(p);
      });
    }
  }

  // -- Hero MRR (combined Stripe + RevenueCat) --
  const stripeMrr = metrics.stripe?.payload?.mrr_cents || 0;
  const rcMrr     = metrics.revenuecat?.payload?.mrr_cents || 0;
  const totalMrr  = stripeMrr + rcMrr;
  const heroNum   = document.querySelector('.hero-number');
  if (heroNum && totalMrr > 0) heroNum.textContent = SP_FMT.money(totalMrr);

  // -- Revenue snapshot stats --
  if (totalMrr)  setStat('Mrr',                SP_FMT.money(totalMrr));
  if (stripeMrr) setStat('Stripe (web)',       SP_FMT.money(stripeMrr));
  if (rcMrr)     setStat('Revenuecat (ios)',   SP_FMT.money(rcMrr));
  const stripeSubs = metrics.stripe?.payload?.active_subs;
  const rcSubs     = metrics.revenuecat?.payload?.active_ios_subs;
  if (stripeSubs != null || rcSubs != null) {
    setStat('Active subs', SP_FMT.num((stripeSubs || 0) + (rcSubs || 0)));
  }

  // -- What Moved: only update rows where we have real data --
  const newSubs7d = (metrics.stripe?.payload?.new_subs_7d || 0) + (metrics.revenuecat?.payload?.new_subs_7d || 0);
  // 24h data isn't yet broken out; leave New subs today on placeholder for now.
  const failedPay = metrics.stripe?.payload?.failed_payments_7d;
  if (failedPay != null) {
    setMovedRow('Failed payments 7d', SP_FMT.num(failedPay), failedPay === 0 ? 'clean' : 'attention', failedPay === 0 ? 'up' : 'down');
  }
  const trafficSource = metrics.ga4?.payload || metrics.cloudflare?.payload;
  const traffic24h = trafficSource?.visitors_24h ?? trafficSource?.sessions_24h;
  if (traffic24h != null) setMovedRow('Traffic last 24h', SP_FMT.num(traffic24h));

  // Bet taps last 24h: events source returns by-surface dict; sum it.
  const betTapsBySurface = metrics.events?.payload?.bet_taps || {};
  const betTaps24h = Object.values(betTapsBySurface).reduce((a, b) => a + b, 0);
  if (Object.keys(betTapsBySurface).length) {
    setMovedRow('Bet taps last 24h', SP_FMT.num(betTaps24h));
  }

  // -- Funnel (last 7d) — replace mockup numbers with real funnel --
  const funnel = metrics.events?.payload?.funnel;
  if (Array.isArray(funnel) && funnel.length) {
    // Funnel rendering uses .funnel-step rows in DOM order matching the
    // events.funnel array. Update label/users/conversion in place.
    const steps = document.querySelectorAll('#panel-command .funnel-step');
    funnel.forEach((step, i) => {
      const node = steps[i];
      if (!node) return;
      const valEl  = node.querySelector('.funnel-value, .moved-value');
      const convEl = node.querySelector('.funnel-conv');
      if (valEl)  valEl.textContent  = SP_FMT.num(step.users);
      if (convEl && step.conversion_pct != null) convEl.textContent = step.conversion_pct + '%';
    });
  }

  // -- Freshness line at bottom of Command panel --
  // Walk every Phase 2 source and render fetched_at + STALE flag.
  const freshnessEl = document.querySelector('#panel-command .freshness');
  if (freshnessEl) {
    const SOURCES = ['stripe', 'revenuecat', 'events', 'ga4', 'gsc', 'cloudflare'];
    const parts = SOURCES.map(name => {
      const env = metrics[name];
      if (!env) return null;
      const stale = env.last_error != null;
      const cls = stale ? 'stale' : 'ok';
      const tag = stale ? 'STALE' : 'OK';
      return `<span class="${cls}">${name}: ${tag}</span>`;
    }).filter(Boolean);
    if (parts.length) freshnessEl.innerHTML = parts.join(' · ');
  }

  // TODO Phase 3.4+:
  //   - 90-day MRR chart needs metrics.stripe.payload.mrr_daily_90d (not yet shipped)
  //   - DAU bar chart needs daily_active_users from a new events helper
  //   - Sparkline needs 14-day MRR series
  // TODO Phase 3.5: cohort retention, user list, tier counts (new endpoints)
  // TODO Phase 3.6: model perf, calibration plots, last 10 signals (new endpoint)
  // TODO Phase 3.7: infra health chips, deploy history, pipeline status (new endpoint)
}

// Kick off the live data fetch on page load. Failure is silent and leaves
// the mockup placeholders visible — the freshness line will reflect any
// per-source error if the fetch itself succeeded.
fetch('/api/admin/metrics?range=7d&include_internal=false', { credentials: 'same-origin' })
  .then(r => r.ok ? r.json() : null)
  .then(data => { if (data) bindLiveData(data); })
  .catch(() => { /* placeholders remain; freshness untouched */ });

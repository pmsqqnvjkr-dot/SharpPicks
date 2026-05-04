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

  // Failed payments — segmented by user. The headline number is
  // distinct USERS with failed payments 7d; we annotate with the total
  // attempt count when retries inflate it (one user with 14 retries
  // would otherwise look like 14 churn-risk customers).
  const sp = metrics.stripe?.payload || {};
  const failedUsers7d = sp.failed_payment_users_7d;
  const failedAttempts7d = sp.failed_payment_attempts_7d;
  if (failedUsers7d != null) {
    const annotation = (failedAttempts7d > failedUsers7d)
      ? `${failedAttempts7d} attempts across ${failedUsers7d} user${failedUsers7d === 1 ? '' : 's'}`
      : (failedUsers7d === 0 ? 'clean' : 'attention');
    setMovedRow('Failed payments 7d', SP_FMT.num(failedUsers7d), annotation, failedUsers7d === 0 ? 'up' : 'down');
  }

  // -- Trial pipeline section (Phase 3 audit follow-up) --
  const setText = (id, val) => {
    const el = document.getElementById(id);
    if (el && val != null) el.textContent = val;
  };
  if (sp.trials != null)                       setText('stat-trials-in-flight',       SP_FMT.num(sp.trials));
  if (sp.trials_likely_to_convert != null)     setText('stat-trials-likely-convert',  SP_FMT.num(sp.trials_likely_to_convert));
  if (sp.trials_with_cancel_scheduled != null) setText('stat-trials-cancel-scheduled', SP_FMT.num(sp.trials_with_cancel_scheduled));
  if (sp.trial_conversions_7d != null)         setText('stat-trial-conv-7d',          SP_FMT.num(sp.trial_conversions_7d));
  if (sp.trial_conversions_30d != null)        setText('stat-trial-conv-30d',         SP_FMT.num(sp.trial_conversions_30d));
  if (sp.paid_with_cancel_scheduled != null)   setText('stat-paid-cancel-scheduled',  SP_FMT.num(sp.paid_with_cancel_scheduled));
  if (sp.canceled_30d != null)                 setText('stat-canceled-30d',           SP_FMT.num(sp.canceled_30d));

  // -- Failing payment customers list (top 10 by attempt count) --
  const failingList = document.getElementById('failing-customers-list');
  if (failingList && Array.isArray(sp.failing_users)) {
    failingList.innerHTML = '';
    if (sp.failing_users.length === 0) {
      const row = document.createElement('div');
      row.className = 'top-list-row';
      row.innerHTML = `<span class="top-list-rank">—</span><span class="top-list-label">No failed payments in the last 30 days.</span><span class="top-list-value">clean</span>`;
      failingList.appendChild(row);
    } else {
      sp.failing_users.forEach((fu, i) => {
        const row = document.createElement('div');
        row.className = 'top-list-row';
        const who = fu.email || fu.customer_id;
        const recent = fu.attempts_24h > 0 ? ` · ${fu.attempts_24h} in 24h` : '';
        row.innerHTML = `
          <span class="top-list-rank">${i + 1}</span>
          <span class="top-list-label">${who}${recent}</span>
          <span class="top-list-value">${fu.attempts_30d} attempts</span>
        `;
        failingList.appendChild(row);
      });
    }
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

// ─────────────────────────────────────────────────────────────────────────
// Users tab data binding (Phase 3.5)
// Two endpoints: /api/admin/users/activity and /api/admin/users/list
// Replaces the mockup's hardcoded snapshot stats, login frequency
// histogram, cohort retention table, and user list rows with real data.
// ─────────────────────────────────────────────────────────────────────────

function bindUsersActivity(data) {
  if (!data) return;

  // Snapshot stats
  const s = data.snapshot || {};
  setStat('Dau today', SP_FMT.num(s.dau));
  setStat('Wau (7d)',   SP_FMT.num(s.wau));
  setStat('Mau (30d)',  SP_FMT.num(s.mau));
  setStat('New users 7d', SP_FMT.num(s.new_7d));

  // Power user count comes from tier_counts (more accurate than mockup's 28)
  const tiers = data.tier_counts || {};
  if (tiers.power != null) setStat('Power users', SP_FMT.num(tiers.power));

  // Replace the DAU 90d bar chart with real daily counts
  const dauCanvas = document.getElementById('chart-users-dau');
  const dauChart = dauCanvas && Chart.getChart(dauCanvas);
  if (dauChart && Array.isArray(data.dau_daily_90d)) {
    dauChart.data.labels = data.dau_daily_90d.map(d => d.date.slice(5));
    dauChart.data.datasets[0].data = data.dau_daily_90d.map(d => d.users);
    dauChart.update('none');
  }

  // Replace login frequency histogram with real bucket counts
  const freqCanvas = document.getElementById('chart-login-freq');
  const freqChart = freqCanvas && Chart.getChart(freqCanvas);
  if (freqChart && data.login_frequency_buckets) {
    const ORDER = ['0', '1', '2-3', '4-5', '6-9', '10-14', '15-19', '20-29', '30+'];
    freqChart.data.labels = ORDER;
    freqChart.data.datasets[0].data = ORDER.map(k => data.login_frequency_buckets[k] || 0);
    freqChart.update('none');
  }

  // Cohort retention heatmap: rebuild the .cohort-grid contents
  const grid = document.querySelector('.cohort-grid');
  if (grid && Array.isArray(data.cohort_retention)) {
    const header = ['cohort', 'size', 'wk 0', 'wk 1', 'wk 2', 'wk 3', 'wk 4', 'wk 5', 'wk 6', 'wk 7', 'wk 8'];
    // Match the mockup grid: 100px label col + repeat(8, 50px) — but we
    // emit week 0..8 (9 cols) plus label + size. The CSS already supports
    // the cohort-cell.label-col / .header / .heat-N classes.
    grid.style.gridTemplateColumns = '100px 50px repeat(9, 50px)';
    grid.innerHTML = '';
    header.forEach((h, i) => {
      const cell = document.createElement('div');
      cell.className = 'cohort-cell ' + (i === 0 ? 'label-col header' : 'header');
      cell.textContent = h;
      grid.appendChild(cell);
    });
    data.cohort_retention.forEach(row => {
      const labelCell = document.createElement('div');
      labelCell.className = 'cohort-cell label-col';
      labelCell.textContent = row.cohort_week.slice(5); // MM-DD
      grid.appendChild(labelCell);

      const sizeCell = document.createElement('div');
      sizeCell.className = 'cohort-cell';
      sizeCell.textContent = SP_FMT.num(row.size);
      grid.appendChild(sizeCell);

      row.retention_by_week.forEach(pct => {
        const cell = document.createElement('div');
        let heat = 'empty';
        if (pct >= 60) heat = 'heat-5';
        else if (pct >= 45) heat = 'heat-4';
        else if (pct >= 30) heat = 'heat-3';
        else if (pct >= 18) heat = 'heat-2';
        else if (pct >= 8)  heat = 'heat-1';
        else if (pct > 0)   heat = 'heat-0';
        cell.className = 'cohort-cell ' + heat;
        cell.textContent = pct > 0 ? pct + '%' : '·';
        grid.appendChild(cell);
      });
    });
  }
}

// Friendly label for each tag class. Anything not listed renders the
// raw tag with underscores -> spaces.
const TAG_LABEL = {
  founding:         'founding member',
  paid_annual:      'paid annual',
  paid_monthly:     'paid monthly',
  paid:             'paid',
  trial:            'trial',
  cancel_scheduled: 'cancel scheduled',
  pending_verify:   'pending verify',
  past_due:         'past due',
  churned:          'churned',
  free:             'free',
  power:            'power',
  ios:              'ios',
  internal:         'internal',
};

function _renderTag(tag) {
  const label = TAG_LABEL[tag] || tag.replace(/_/g, ' ');
  return `<span class="user-tag ${tag}">${label}</span>`;
}

function bindUsersList(data) {
  if (!data || !Array.isArray(data.users)) return;
  const lists = document.querySelectorAll('#panel-users .user-row');
  // The mockup has two demo user rows; the list is rendered in their
  // parent container. Find that container by climbing from one row.
  const sample = lists[0];
  if (!sample) return;
  const container = sample.parentNode;
  // Wipe existing user-row elements (preserve the header row above it).
  container.querySelectorAll('.user-row').forEach(n => n.remove());
  data.users.forEach(u => {
    const row = document.createElement('div');
    row.className = 'user-row';
    // Render up to 4 tags so a paid_annual + cancel_scheduled + ios
    // user shows all three context flags without truncation.
    const tagsHtml = (u.tags || []).slice(0, 4).map(_renderTag).join('');
    // If a cancel is scheduled, surface the effective date inline so
    // operators can see how much save-window is left.
    let cancelHint = '';
    if (u.cancel_scheduled_at && u.cancel_effective_at) {
      const eff = new Date(u.cancel_effective_at);
      const today = new Date();
      const days = Math.max(0, Math.ceil((eff - today) / (1000 * 60 * 60 * 24)));
      cancelHint = `<span class="user-cancel-hint">drops ${u.cancel_effective_at.slice(5, 10)} (${days}d)</span>`;
    }
    row.innerHTML = `
      <div class="user-identity">
        <span class="user-email">${u.email}</span>
        <div class="user-tags">${tagsHtml}${cancelHint}</div>
      </div>
      <div class="user-numeric" data-label="Logins 30d">${u.logins_30d}</div>
      <div class="user-numeric muted" data-label="Bet taps">${u.bet_taps_30d}</div>
      <div class="user-numeric muted" data-label="Days active">${u.days_active_30d}</div>
      <div class="user-numeric faint" data-label="Last seen">${u.last_seen_at ? u.last_seen_at.slice(5, 10) : '—'}</div>
    `;
    container.appendChild(row);
  });
}

// Fetch Users tab data only when the user actually clicks into the tab —
// saves a query on initial load. Cache the response so re-clicks don't
// re-fetch.
let _usersDataPromise = null;
function loadUsersTabData() {
  if (_usersDataPromise) return _usersDataPromise;
  _usersDataPromise = Promise.all([
    fetch('/api/admin/users/activity?range=30d', { credentials: 'same-origin' }).then(r => r.ok ? r.json() : null),
    fetch('/api/admin/users/list?segment=all&limit=50', { credentials: 'same-origin' }).then(r => r.ok ? r.json() : null),
  ]).then(([activity, list]) => {
    bindUsersActivity(activity);
    bindUsersList(list);
  }).catch(() => { _usersDataPromise = null; /* allow retry on next click */ });
  return _usersDataPromise;
}

document.querySelector('.tab[data-tab="users"]')?.addEventListener('click', loadUsersTabData);
document.querySelectorAll('[data-deep-link="users"]').forEach(l => l.addEventListener('click', loadUsersTabData));

// ─────────────────────────────────────────────────────────────────────────
// Model tab data binding (Phase 3.6)
// /api/admin/model/perf returns {win_rate_by_sport_daily,
// hit_rate_by_edge_tier, calibration, edge_distribution, last_10_signals}
// ─────────────────────────────────────────────────────────────────────────

function bindModelPerf(data) {
  if (!data) return;

  // Win rate vs market chart (NBA + MLB rolling 14d)
  const winChart = Chart.getChart(document.getElementById('chart-winrate'));
  if (winChart && data.win_rate_by_sport_daily) {
    const sports = Object.keys(data.win_rate_by_sport_daily);
    const labels = (data.win_rate_by_sport_daily[sports[0]] || []).map(d => d.date.slice(5));
    const datasets = sports.map((s, i) => {
      const series = data.win_rate_by_sport_daily[s].map(d => d.win_rate);
      const isMlb = s.toLowerCase().includes('mlb');
      return {
        label: `${s.toUpperCase()} (rolling 14d)`,
        data: series,
        borderColor: isMlb ? '#34D399' : '#4F86F7',
        borderDash: isMlb ? [4, 4] : [],
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2,
        fill: false,
      };
    });
    winChart.data.labels = labels;
    winChart.data.datasets = datasets;
    winChart.update('none');
  }

  // Hit rate by edge tier
  const meiChart = Chart.getChart(document.getElementById('chart-meihit'));
  if (meiChart && Array.isArray(data.hit_rate_by_edge_tier)) {
    meiChart.data.labels = data.hit_rate_by_edge_tier.map(t => t.tier);
    meiChart.data.datasets[0].data = data.hit_rate_by_edge_tier.map(t => t.hit_rate || 0);
    meiChart.update('none');
  }

  // Calibration plots: NBA + MLB
  ['nba', 'mlb'].forEach(sport => {
    const chart = Chart.getChart(document.getElementById('chart-cal-' + sport));
    if (!chart) return;
    const series = (data.calibration || {})[sport] || (data.calibration || {})[sport.toUpperCase()] || [];
    if (!series.length) return;
    chart.data.labels = series.map(p => p.predicted);
    chart.data.datasets[0].data = series.map(p => ({ x: p.predicted, y: p.observed }));
    chart.update('none');
  });

  // Edge distribution histogram
  const meiDist = Chart.getChart(document.getElementById('chart-mei'));
  if (meiDist && Array.isArray(data.edge_distribution)) {
    meiDist.data.labels = data.edge_distribution.map(b => b.tier);
    meiDist.data.datasets[0].data = data.edge_distribution.map(b => b.count);
    meiDist.update('none');
  }

  // Last 10 signals table
  if (Array.isArray(data.last_10_signals)) {
    // The mockup renders signals as .top-list or .pipeline-row style.
    // Find a target container in the Model panel.
    const tbl = document.querySelector('#panel-model .top-list');
    if (tbl) {
      tbl.innerHTML = '';
      data.last_10_signals.forEach((s, i) => {
        const row = document.createElement('div');
        row.className = 'top-list-row';
        const RESULT_LABEL = { won: 'WIN', lost: 'LOSS', push: 'PUSH', pending: 'PEND' };
        const resultBadge = RESULT_LABEL[s.result] || 'PEND';
        row.innerHTML = `
          <span class="top-list-rank">${i + 1}</span>
          <span class="top-list-label">${s.matchup} · ${s.side} ${s.line}</span>
          <span class="top-list-value">${resultBadge} ${s.edge_pct ? s.edge_pct.toFixed(1) : '—'}%</span>
        `;
        tbl.appendChild(row);
      });
    }
  }
}

let _modelDataPromise = null;
function loadModelTabData() {
  if (_modelDataPromise) return _modelDataPromise;
  _modelDataPromise = fetch('/api/admin/model/perf?range=90d', { credentials: 'same-origin' })
    .then(r => r.ok ? r.json() : null)
    .then(bindModelPerf)
    .catch(() => { _modelDataPromise = null; });
  return _modelDataPromise;
}

document.querySelector('.tab[data-tab="model"]')?.addEventListener('click', loadModelTabData);

// ─────────────────────────────────────────────────────────────────────────
// Infra tab data binding (Phase 3.7)
// Two endpoints:
//   /api/admin/infra/health -> chips, latency_series, recent_deploys, database_health
//   /api/admin/cron-health  -> pipeline status (existing endpoint, reused)
// ─────────────────────────────────────────────────────────────────────────

function bindInfraHealth(data) {
  if (!data) return;
  const c = data.chips || {};

  // Update health-chip values by their .label text
  function setChipValue(label, value, kindClass) {
    const chips = document.querySelectorAll('#panel-infra .health-chip');
    for (const chip of chips) {
      const lbl = chip.querySelector('.label');
      if (!lbl || lbl.textContent.trim().toLowerCase() !== label.toLowerCase()) continue;
      const v = chip.querySelector('.v');
      if (v) v.textContent = value;
      if (kindClass) {
        chip.classList.remove('ok', 'warn', 'danger');
        chip.classList.add(kindClass);
      }
      return;
    }
  }
  setChipValue('Uptime 30d', (c.uptime_30d_pct ?? '—') + '%',
               c.uptime_30d_pct >= 99.5 ? 'ok' : c.uptime_30d_pct >= 98 ? 'warn' : 'danger');
  setChipValue('p95 latency', (c.p95_24h_ms ?? '—') + 'ms',
               (c.p95_24h_ms || 0) < 300 ? 'ok' : (c.p95_24h_ms || 0) < 1000 ? 'warn' : 'danger');
  setChipValue('Errors 24h', SP_FMT.num(c.errors_24h),
               (c.errors_24h || 0) === 0 ? 'ok' : (c.errors_24h || 0) < 10 ? 'warn' : 'danger');
  if (c.cpu_pct != null) setChipValue('Cpu', c.cpu_pct + '%',
                                       c.cpu_pct < 50 ? 'ok' : c.cpu_pct < 80 ? 'warn' : 'danger');
  if (c.mem_pct != null) setChipValue('Memory', c.mem_pct + '%',
                                       c.mem_pct < 70 ? 'ok' : c.mem_pct < 85 ? 'warn' : 'danger');
  if (c.requests_24h != null) setChipValue('Requests 24h', SP_FMT.num(c.requests_24h));

  // Latency chart (p50/p95/p99 hourly)
  const latChart = Chart.getChart(document.getElementById('chart-latency'));
  if (latChart && Array.isArray(data.latency_series)) {
    latChart.data.labels = data.latency_series.map(p => p.hour.slice(5, 13));
    // Mockup chart has 3 datasets — replace each
    if (latChart.data.datasets.length >= 3) {
      latChart.data.datasets[0].data = data.latency_series.map(p => p.p50);
      latChart.data.datasets[1].data = data.latency_series.map(p => p.p95);
      latChart.data.datasets[2].data = data.latency_series.map(p => p.p99);
    }
    latChart.update('none');
  }

  // Recent deploys
  const deployContainer = document.querySelector('#panel-infra .deploy-row')?.parentNode;
  if (deployContainer && Array.isArray(data.recent_deploys)) {
    deployContainer.querySelectorAll('.deploy-row').forEach(n => n.remove());
    data.recent_deploys.forEach(d => {
      const row = document.createElement('div');
      row.className = 'deploy-row';
      row.innerHTML = `
        <span class="sha">${d.sha}</span>
        <span>${(d.date || '').slice(0, 10)}</span>
        <span class="msg">${d.message}</span>
        <span class="status ${d.status === 'success' ? 'success' : 'failed'}">${d.status}</span>
      `;
      deployContainer.appendChild(row);
    });
  }

  // Database health stat-rows
  const dh = data.database_health || {};
  if (dh.connections_active != null) setStat('Connections active', SP_FMT.num(dh.connections_active));
  if (dh.connections_idle != null)   setStat('Connections idle',   SP_FMT.num(dh.connections_idle));
  if (dh.database_size_mb != null)   setStat('Database size',      dh.database_size_mb + ' MB');
  if (dh.longest_running_query_seconds != null) {
    setStat('Longest query', dh.longest_running_query_seconds + 's');
  }
}

function bindCronHealth(data) {
  if (!data || !Array.isArray(data.jobs)) return;
  const container = document.querySelector('#panel-infra .pipeline-row')?.parentNode;
  if (!container) return;
  container.querySelectorAll('.pipeline-row').forEach(n => n.remove());
  data.jobs.forEach(job => {
    const row = document.createElement('div');
    row.className = 'pipeline-row';
    const dotClass = job.health === 'ok' ? '' : (job.health === 'warn' ? 'warn' : 'fail');
    const ago = job.hours_ago != null ? job.hours_ago + 'h ago' : 'never';
    row.innerHTML = `
      <span class="pipeline-name">${job.name}</span>
      <span class="pipeline-time">${ago}</span>
      <span class="pipeline-status-dot ${dotClass}" aria-label="${job.health}"></span>
    `;
    container.appendChild(row);
  });
}

let _infraDataPromise = null;
function loadInfraTabData() {
  if (_infraDataPromise) return _infraDataPromise;
  _infraDataPromise = Promise.all([
    fetch('/api/admin/infra/health', { credentials: 'same-origin' }).then(r => r.ok ? r.json() : null),
    fetch('/api/admin/cron-health',  { credentials: 'same-origin' }).then(r => r.ok ? r.json() : null),
  ]).then(([health, cron]) => {
    bindInfraHealth(health);
    bindCronHealth(cron);
  }).catch(() => { _infraDataPromise = null; });
  return _infraDataPromise;
}

document.querySelector('.tab[data-tab="infra"]')?.addEventListener('click', loadInfraTabData);

// Wire segment chip clicks to refetch the user list with the new segment.
document.querySelectorAll('#panel-users .segment-chips .segment-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const seg = (chip.dataset.segment || chip.textContent.trim().split(/\s+/)[0] || 'all').toLowerCase();
    fetch(`/api/admin/users/list?segment=${seg}&limit=50`, { credentials: 'same-origin' })
      .then(r => r.ok ? r.json() : null)
      .then(bindUsersList)
      .catch(() => {});
  });
});

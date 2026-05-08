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

  // Search Performance: dual-axis line chart, clicks (left) + impressions (right)
  const searchEl = document.getElementById('chart-search');
  if (searchEl) {
    new Chart(searchEl, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Clicks',
            data: [],
            borderColor: '#4F86F7',
            backgroundColor: 'rgba(79, 134, 247, 0.08)',
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 1.5,
            yAxisID: 'yClicks',
          },
          {
            label: 'Impressions',
            data: [],
            borderColor: '#34D399',
            backgroundColor: 'transparent',
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 1.5,
            borderDash: [3, 3],
            yAxisID: 'yImpressions',
          },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false, ...noLegend,
        scales: {
          x: { ...baseGrid, ticks: { display: false } },
          yClicks:      { ...baseGrid, beginAtZero: true, position: 'left' },
          yImpressions: { ...baseGrid, beginAtZero: true, position: 'right', grid: { drawOnChartArea: false } },
        },
      },
    });
  }

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

function setStat(label, value, suffixText) {
  // Find every .stat-row whose .label text matches `label` (case-insensitive),
  // replace its .value text, and optionally update the .value-suffix.
  // If suffixText is omitted, an existing suffix in markup is preserved
  // as-is. If suffixText is null, the suffix is removed.
  //
  // Walks ALL matches because admin.html intentionally duplicates rows
  // across tabs (Command "user activity" and Users "activity overview"
  // both render Dau today / Wau (7d) / etc). Stopping at the first match
  // left the second tab stuck on whatever value shipped in the HTML.
  const rows = document.querySelectorAll('.stat-row');
  let updated = 0;
  for (const row of rows) {
    const lbl = row.querySelector('.label');
    if (!lbl) continue;
    if (lbl.textContent.trim().toLowerCase() !== label.toLowerCase()) continue;
    const val = row.querySelector('.value');
    if (!val) continue;
    const suffix = val.querySelector('.value-suffix');
    val.textContent = value;
    if (suffixText === null) {
      // explicit removal
    } else if (suffixText !== undefined) {
      // overwrite or create
      const sNode = suffix || document.createElement('span');
      if (!suffix) sNode.className = 'value-suffix';
      sNode.textContent = suffixText;
      val.appendChild(sNode);
    } else if (suffix) {
      // preserve existing
      val.appendChild(suffix);
    }
    updated++;
  }
  return updated > 0;
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

// Stash the latest metrics payload so per-tab binds (Users / Model /
// Infra) can reach into Stripe + RC + events numbers when they need
// to (e.g., the Users tab Paid/Trial segment chips read from Stripe
// active_subs / trial_subs, which is the source-of-truth count of
// paying customers — not subscription_status='active' from User table,
// which has webhook-ordering drift).
window.__SP_METRICS = null;

function bindLiveData(metrics) {
  if (!metrics) return;
  window.__SP_METRICS = metrics;

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

  // -- Per-section summaries (Phase 3 audit follow-up) --
  // services/headline.py.compute_summaries() returns a dict of
  // section-id -> sentence. Replace each .section-summary inner text
  // by section ID so we don't accidentally update mockup copy that
  // never had a real-data equivalent.
  const summaries = metrics.summaries || {};
  Object.entries(summaries).forEach(([sectionId, sentence]) => {
    if (!sentence) return;
    const sec = document.getElementById(sectionId);
    if (!sec) return;
    const summaryEl = sec.querySelector('.section-summary');
    if (summaryEl) summaryEl.textContent = sentence;
  });

  // -- Hero MRR (combined Stripe + RevenueCat) --
  // Real MRR = paying customers only. Trialing subs have a card on
  // file but no money has changed hands; they're broken out below.
  const stripeMrr = metrics.stripe?.payload?.mrr_cents || 0;
  const rcMrr     = metrics.revenuecat?.payload?.mrr_cents || 0;
  const totalMrr  = stripeMrr + rcMrr;
  const heroNum   = document.querySelector('.hero-number');
  if (heroNum && totalMrr > 0) heroNum.textContent = SP_FMT.money(totalMrr);

  // Annotate the hero meta with the expected MRR upside if it differs
  // (i.e., trials are pending conversion).
  const stripeExpected = metrics.stripe?.payload?.expected_mrr_cents || stripeMrr;
  const expectedTotal = stripeExpected + rcMrr;
  if (expectedTotal > totalMrr) {
    const upside = expectedTotal - totalMrr;
    const heroMeta = document.querySelector('.hero-meta .label');
    if (heroMeta) {
      heroMeta.textContent = `current mrr · combined web + ios · +${SP_FMT.money(upside)} expected if trials convert`;
    }
  }

  // Revenue chart — wire real Stripe mrr_daily_90d series, drop the
  // placeholder RevenueCat dataset when iOS is not yet live.
  const mrrChart = Chart.getChart(document.getElementById('chart-mrr'));
  const iosLive = !!metrics.revenuecat?.payload?.ios_prod_live;
  if (mrrChart) {
    const stripeDaily = metrics.stripe?.payload?.mrr_daily_90d;
    if (Array.isArray(stripeDaily) && stripeDaily.length > 0) {
      // Replace mockup labels with real dates (MM-DD).
      mrrChart.data.labels = stripeDaily.map(d => d.date.slice(5));
      // Find or create the Stripe dataset and load real values.
      const stripeIdx = mrrChart.data.datasets.findIndex(
        ds => (ds.label || '').toLowerCase().includes('stripe')
      );
      const stripeDataset = stripeIdx >= 0 ? mrrChart.data.datasets[stripeIdx] : null;
      if (stripeDataset) {
        stripeDataset.data = stripeDaily.map(d => (d.mrr_cents || 0) / 100);
      }
    }

    if (!iosLive) {
      // Drop any RevenueCat / iOS dataset entirely while iOS is gated off.
      const before = mrrChart.data.datasets.length;
      mrrChart.data.datasets = mrrChart.data.datasets.filter(
        ds => !(ds.label || '').toLowerCase().includes('revenuecat')
          && !(ds.label || '').toLowerCase().includes('ios')
      );
      if (mrrChart.data.datasets.length !== before) {
        // Stripe dataset was previously fill='-1' (stacked above RC).
        // With RC removed, fill from origin so the area still shades.
        mrrChart.data.datasets.forEach(ds => {
          if ((ds.label || '').toLowerCase().includes('stripe')) {
            ds.fill = 'origin';
          }
        });
      }
    }
    mrrChart.update('none');
  }

  // -- Revenue snapshot stats --
  // Always set every row so the mockup placeholders never leak.
  // For RevenueCat: when iOS is gated off (IOS_PROD_LIVE=0), show
  // "—" with an explicit suffix so the operator knows it's not
  // missing data, just not yet live.
  setStat('Mrr',          SP_FMT.money(totalMrr));
  setStat('Stripe (web)', SP_FMT.money(stripeMrr));
  if (iosLive) {
    setStat('Revenuecat (ios)', SP_FMT.money(rcMrr));
  } else {
    // Hide the row entirely — cleaner than showing a fake "—"
    const rows = document.querySelectorAll('#panel-command .stat-row');
    for (const row of rows) {
      const lbl = row.querySelector('.label');
      if (lbl && lbl.textContent.trim().toLowerCase() === 'revenuecat (ios)') {
        row.style.display = 'none';
        break;
      }
    }
    // And drop ' + revenuecat' from the Revenue section meta so the
    // header doesn't claim a source we're not showing.
    const revMeta = document.querySelector('#section-revenue .section-meta');
    if (revMeta) revMeta.textContent = 'stripe · live';
  }
  const stripeSubs = metrics.stripe?.payload?.active_subs;
  const rcSubs     = metrics.revenuecat?.payload?.active_ios_subs;
  setStat('Active subs', SP_FMT.num((stripeSubs || 0) + (rcSubs || 0)));
  // Surface trial-card-on-file count separately from paying subs.
  const stripeTrials = metrics.stripe?.payload?.trial_subs;
  if (stripeTrials != null) setStat('Trials in flight', SP_FMT.num(stripeTrials));

  // -- What Moved: bind every row with real data. Sources cross-cut
  // multiple metrics envelopes; some rows (DAU, Logins 24h) come in via
  // bindUsersActivity which fires after this on page load.
  const newSubs24h = (metrics.stripe?.payload?.new_subs_24h ?? 0) + (metrics.revenuecat?.payload?.new_subs_24h ?? 0);
  const newSubs7d = (metrics.stripe?.payload?.new_subs_7d || 0) + (metrics.revenuecat?.payload?.new_subs_7d || 0);
  const newSubs7dAvg = newSubs7d / 7.0;
  const newSubsDelta = newSubs24h - newSubs7dAvg;
  const newSubsDeltaText = Math.abs(newSubsDelta) < 0.5
    ? 'on track'
    : (newSubsDelta > 0 ? `+${Math.round(newSubsDelta)} vs avg` : `${Math.round(newSubsDelta)} vs avg`);
  const newSubsDeltaClass = newSubsDelta > 0 ? 'up' : (newSubsDelta < 0 ? 'down' : '');
  setMovedRow('New subscribers today', SP_FMT.num(newSubs24h), newSubsDeltaText, newSubsDeltaClass);

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
  if (sp.comped_pro_users != null)             setText('stat-comped-pro',             SP_FMT.num(sp.comped_pro_users));

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

  // -- Traffic section overview stats. Every label-row below was
  // hardcoded mockup (2,840 / 1,820 / 9,120 / 486 / 12.4k / 14.2) and
  // never bound to a source. Wire each from its real upstream.
  const ga4 = metrics.ga4?.payload || {};
  const cf = metrics.cloudflare?.payload || {};
  const gsc = metrics.gsc?.payload || {};
  if (ga4.sessions != null)         setStat('Sessions (ga4)',          SP_FMT.num(ga4.sessions));
  if (ga4.engaged_sessions != null) {
    // Engaged sessions row has a percent suffix in the markup; preserve
    // it by formatting the value to include the engagement_rate.
    const pct = ga4.engagement_rate != null ? Math.round(ga4.engagement_rate * 100) : null;
    setStat('Engaged sessions', SP_FMT.num(ga4.engaged_sessions), pct != null ? `${pct}%` : undefined);
  }
  if (cf.page_views != null)        setStat('Requests (cloudflare)',  SP_FMT.num(cf.page_views));
  if (gsc.clicks != null)           setStat('Gsc clicks 28d',          SP_FMT.num(gsc.clicks));
  if (gsc.impressions != null)      setStat('Gsc impressions 28d',     SP_FMT.num(gsc.impressions));
  if (gsc.avg_position != null)     setStat('Avg position',            gsc.avg_position.toFixed(1));

  // -- Search Performance section. Dedicated GSC view with totals,
  // 28-day trend chart (clicks + impressions dual-axis), top queries,
  // top pages. Source: gsc payload, cached 12h on the server (the
  // GSC API itself updates daily so polling more often is wasted).
  if (gsc.clicks != null)      setStat('Clicks',               SP_FMT.num(gsc.clicks));
  if (gsc.impressions != null) setStat('Impressions',          SP_FMT.num(gsc.impressions));
  if (gsc.ctr != null)         setStat('Ctr',                  (gsc.ctr * 100).toFixed(1), '%');
  if (gsc.avg_position != null) setStat('Avg position (search)', gsc.avg_position.toFixed(1));

  const searchSummary = gsc.clicks != null
    ? `${SP_FMT.num(gsc.clicks)} clicks on ${SP_FMT.num(gsc.impressions || 0)} impressions over the last 28 days. Average position ${gsc.avg_position?.toFixed(1) || '—'}, click-through rate ${((gsc.ctr || 0) * 100).toFixed(1)}%. Data lags 2-3 days.`
    : 'GSC data not available. Check the Google Search Console connection.';
  _setSummary('section-search', searchSummary);

  // 28d trend chart
  const searchChart = document.getElementById('chart-search');
  const searchChartObj = searchChart && Chart.getChart(searchChart);
  if (searchChartObj && Array.isArray(gsc.daily) && gsc.daily.length > 0) {
    searchChartObj.data.labels = gsc.daily.map(d => (d.date || '').slice(5));
    searchChartObj.data.datasets[0].data = gsc.daily.map(d => d.clicks || 0);
    searchChartObj.data.datasets[1].data = gsc.daily.map(d => d.impressions || 0);
    searchChartObj.update('none');
  }

  // Top queries (10)
  const queriesEl = document.getElementById('gsc-top-queries');
  if (queriesEl && Array.isArray(gsc.top_queries)) {
    queriesEl.innerHTML = '';
    if (gsc.top_queries.length === 0) {
      queriesEl.innerHTML = '<div class="top-list-row"><span class="top-list-rank">—</span><span class="top-list-label">No query data yet.</span><span class="top-list-value">—</span></div>';
    } else {
      gsc.top_queries.slice(0, 10).forEach((q, i) => {
        const row = document.createElement('div');
        row.className = 'top-list-row';
        row.innerHTML = `
          <span class="top-list-rank">${i + 1}.</span>
          <span class="top-list-label">${q.query}</span>
          <span class="top-list-value">${q.clicks} click${q.clicks === 1 ? '' : 's'}</span>
        `;
        queriesEl.appendChild(row);
      });
    }
  }

  // Top pages (10)
  const pagesEl = document.getElementById('gsc-top-pages');
  if (pagesEl && Array.isArray(gsc.top_pages)) {
    pagesEl.innerHTML = '';
    if (gsc.top_pages.length === 0) {
      pagesEl.innerHTML = '<div class="top-list-row"><span class="top-list-rank">—</span><span class="top-list-label">No page data yet.</span><span class="top-list-value">—</span></div>';
    } else {
      gsc.top_pages.slice(0, 10).forEach((p, i) => {
        const row = document.createElement('div');
        row.className = 'top-list-row';
        // Strip the protocol+host for display brevity.
        const path = (p.page || '').replace(/^https?:\/\/[^/]+/, '') || p.page;
        row.innerHTML = `
          <span class="top-list-rank">${i + 1}.</span>
          <span class="top-list-label">${path}</span>
          <span class="top-list-value">${p.clicks} click${p.clicks === 1 ? '' : 's'}</span>
        `;
        pagesEl.appendChild(row);
      });
    }
  }

  // Bet taps last 24h: events source returns by-surface dict for the
  // requested range (7d or 30d). The value here is taps in that window,
  // not strictly 24h, but it's the best we have until events source
  // exposes a 24h slice. Bind unconditionally so a zero shows zero
  // instead of leaving the mockup '1'.
  const betTapsBySurface = metrics.events?.payload?.bet_taps || {};
  const betTaps = Object.values(betTapsBySurface).reduce((a, b) => a + b, 0);
  const betTapsDelta = betTaps === 0
    ? 'below threshold'
    : (betTaps <= 3 ? 'on track' : 'above typical');
  setMovedRow('Bet taps last 24h', SP_FMT.num(betTaps), betTapsDelta);

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

  // -- Hero MRR sparkline (last 14 days). Source: stripe.mrr_daily_90d.
  // The mockup hardcodes an SVG polyline; replace with real-data points
  // mapped to the 600x56 viewBox. Skip if the daily series is missing
  // or every value is zero (don't blank the placeholder with a flat line).
  const sparkPolyline = document.querySelector('.sparkline-wrap svg polyline');
  if (sparkPolyline && Array.isArray(metrics.stripe?.payload?.mrr_daily_90d)) {
    const last14 = metrics.stripe.payload.mrr_daily_90d.slice(-14);
    const cents = last14.map(d => d.mrr_cents || 0);
    const maxC = Math.max(...cents);
    const minC = Math.min(...cents);
    if (maxC > 0 && last14.length >= 2) {
      // Map each point to (x, y) in the 600x56 viewBox. y inverts so
      // higher MRR sits higher on the chart. Add 4px padding top+bottom.
      const range = maxC - minC || 1;
      const w = 600, h = 56, pad = 4;
      const points = last14.map((d, i) => {
        const x = (i / (last14.length - 1)) * w;
        const y = h - pad - ((d.mrr_cents - minC) / range) * (h - pad * 2);
        return `${x.toFixed(0)},${y.toFixed(1)}`;
      }).join(' ');
      sparkPolyline.setAttribute('points', points);
    }
  }

  // -- Traffic chart (Command tab, last 30 days, line series). Source:
  // cloudflare.daily array of {date, page_views, visits}. Falls back
  // gracefully if cf source is stale or missing.
  const cfDaily = metrics.cloudflare?.payload?.daily;
  const trafficCanvas = document.getElementById('chart-traffic');
  const trafficChart = trafficCanvas && Chart.getChart(trafficCanvas);
  if (trafficChart && Array.isArray(cfDaily) && cfDaily.length > 0) {
    const counts = cfDaily.map(d => d.visits ?? d.page_views ?? 0);
    if (_hasRealValues(counts, 5)) {
      trafficChart.data.labels = cfDaily.map(d => (d.date || '').slice(5));
      trafficChart.data.datasets[0].data = counts;
      trafficChart.update('none');
    }
  }

  // -- Top signals by tap rate · 30d (events.top_signals) --
  // events_source returns up to 10 {signal_id, taps} entries sorted by
  // tap count. Render into #top-signals-list as a top-list.
  const topSignals = metrics.events?.payload?.top_signals;
  const topListEl = document.getElementById('top-signals-list');
  if (topListEl && Array.isArray(topSignals)) {
    topListEl.innerHTML = '';
    if (topSignals.length === 0) {
      topListEl.innerHTML = '<div class="top-list-row"><span class="top-list-rank">—</span><span class="top-list-label">No bet taps in the last 30 days.</span><span class="top-list-value">—</span></div>';
    } else {
      topSignals.slice(0, 4).forEach((sig, i) => {
        const row = document.createElement('div');
        row.className = 'top-list-row';
        row.innerHTML = `
          <span class="top-list-rank">${i + 1}.</span>
          <span class="top-list-label">${sig.signal_id}</span>
          <span class="top-list-value">${sig.taps} tap${sig.taps === 1 ? '' : 's'}</span>
        `;
        topListEl.appendChild(row);
      });
    }
  }

  // -- Recent bet taps (events.recent_bet_taps) --
  // events_source emits the last 5 bet_tap events with timestamps and
  // surfaces. Renders into #recent-bet-taps, replacing the empty
  // placeholder.
  const recentTaps = metrics.events?.payload?.recent_bet_taps;
  const tapsEl = document.getElementById('recent-bet-taps');
  if (tapsEl && Array.isArray(recentTaps)) {
    tapsEl.innerHTML = '';
    if (recentTaps.length === 0) {
      tapsEl.innerHTML = '<div class="recent-row empty"><span class="meta">No bet taps in the last 7 days.</span></div>';
    } else {
      recentTaps.forEach(t => {
        const row = document.createElement('div');
        row.className = 'recent-row';
        const ts = t.at ? _agoLabel(t.at) : '—';
        const surface = t.surface || 'unknown';
        const sigId = t.signal_id ? ` · ${t.signal_id}` : '';
        const tagText = t.is_internal ? 'internal' : 'external';
        const tagClass = t.is_internal ? 'tag internal' : 'tag';
        row.innerHTML = `<span class="ts">${ts}</span><span class="meta">${surface}${sigId}</span><span class="${tagClass}">${tagText}</span>`;
        tapsEl.appendChild(row);
      });
    }
  }

  // -- Recent signals (events.recent_signals → last 10 issued picks) --
  const recentSigs = metrics.events?.payload?.recent_signals;
  const sigsEl = document.getElementById('recent-signals');
  if (sigsEl && Array.isArray(recentSigs)) {
    sigsEl.innerHTML = '';
    if (recentSigs.length === 0) {
      sigsEl.innerHTML = '<div class="recent-row empty"><span class="meta">No signals issued recently.</span></div>';
    } else {
      recentSigs.forEach(s => {
        const row = document.createElement('div');
        row.className = 'recent-row';
        const ts = s.at ? s.at.slice(5, 10) : '—';
        // Pick.result values in the DB: 'win' | 'loss' | 'push' | 'revoked'
        // | 'pending' (which arrives here as null after the source maps it).
        let tag, tagStyle = '';
        const r = s.result;
        if (r === 'win' || r === 'won')         { tag = 'hit';     tagStyle = 'class="tag power"'; }
        else if (r === 'loss' || r === 'lost')  { tag = 'miss';    tagStyle = 'class="tag" style="color: var(--danger); border-color: rgba(228,129,129,0.3);"'; }
        else if (r === 'push')                  { tag = 'push';    tagStyle = 'class="tag"'; }
        else if (r === 'revoked')               { tag = 'revoked'; tagStyle = 'class="tag" style="color: var(--text-faint); border-color: var(--border);"'; }
        else                                    { tag = 'live';    tagStyle = 'class="tag"'; }
        row.innerHTML = `<span class="ts">${ts}</span><span class="meta">${s.meta}</span><span ${tagStyle}>${tag}</span>`;
        sigsEl.appendChild(row);
      });
    }
  }

  // -- Header refresh timestamp --
  const refreshEl = document.querySelector('.last-refresh');
  if (refreshEl && metrics.generated_at) {
    refreshEl.textContent = `refreshed ${_agoLabel(metrics.generated_at)}`;
  }
}

// "14m ago", "2h ago", "3d ago" — short relative-time formatter for the
// recent-rows. Falls back to the raw string if the date is malformed.
function _agoLabel(iso) {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  if (isNaN(t)) return iso;
  const diff = Math.max(0, Date.now() - t);
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

// Reusable fetcher for the unified /api/admin/metrics endpoint. Pass
// {nocache: true} to bust the server-side per-source cache (Stripe,
// Cloudflare, etc.) before fetching — used by the manual refresh button.
function refreshLiveData({ nocache = false } = {}) {
  const url = nocache
    ? '/api/admin/metrics?range=7d&include_internal=false&nocache=1'
    : '/api/admin/metrics?range=7d&include_internal=false';
  return fetch(url, { credentials: 'same-origin' })
    .then(r => r.ok ? r.json() : null)
    .then(data => { if (data) bindLiveData(data); })
    .catch(() => { /* placeholders remain; freshness untouched */ });
}

// Refresh everything visible. Hits every tab's data source so a single
// 60s tick keeps Command, Users, Model, and Infra all current. Each
// loader function uses an in-flight promise so concurrent triggers
// coalesce, then clears so the next call re-fetches fresh.
function refreshAll({ nocache = false } = {}) {
  refreshLiveData({ nocache });
  loadUsersTabData();
  loadModelTabData();
  loadInfraTabData();
}

// Initial load. Failure is silent and leaves placeholders visible.
refreshLiveData();
// Note: the eager loadUsersTabData() fire is at the bottom of this file,
// AFTER the `let _usersDataPromise` declaration. Calling it here would
// throw a ReferenceError because the let binding is in TDZ until line
// 1223 executes — function decls hoist, `let`s do not.

// Auto-poll every 60 seconds while the tab is visible. The Stripe and
// RevenueCat caches are 60s; this cadence makes "refreshed Xm ago"
// stay accurate without spamming the upstream APIs.
const POLL_INTERVAL_MS = 60_000;
setInterval(() => {
  if (document.visibilityState === 'visible') refreshAll();
}, POLL_INTERVAL_MS);
// Refresh immediately when the tab regains focus (e.g. you switched
// away to Slack and came back five minutes later).
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') refreshAll();
});

// Make the "refreshed Xm ago" indicator a manual-refresh button.
// Clicking it bypasses the server-side cache so values come straight
// from upstream (Stripe, Cloudflare, etc.).
(() => {
  const refreshEl = document.querySelector('.last-refresh');
  if (!refreshEl) return;
  refreshEl.style.cursor = 'pointer';
  refreshEl.title = 'Click to refresh now (bypasses server cache)';
  refreshEl.addEventListener('click', () => {
    const original = refreshEl.textContent;
    refreshEl.textContent = 'refreshing…';
    refreshAll({ nocache: true });
    // The bindLiveData call inside refreshLiveData will overwrite the
    // text on success; this fallback restores it if the fetch fails.
    setTimeout(() => {
      if (refreshEl.textContent === 'refreshing…') refreshEl.textContent = original;
    }, 8000);
  });
})();

// ─────────────────────────────────────────────────────────────────────────
// Users tab data binding (Phase 3.5)
// Two endpoints: /api/admin/users/activity and /api/admin/users/list
// Replaces the mockup's hardcoded snapshot stats, login frequency
// histogram, cohort retention table, and user list rows with real data.
// ─────────────────────────────────────────────────────────────────────────

// Helper: replaces the .section-summary inside a section ID with new text.
function _setSummary(sectionId, sentence) {
  if (!sentence) return;
  const sec = document.getElementById(sectionId);
  if (!sec) return;
  const el = sec.querySelector('.section-summary');
  if (el) el.textContent = sentence;
}

// Helper: replaces .section-summary by matching the section's title
// text (case-insensitive substring). Useful for sections without an
// explicit ID — Users / Model / Infra tabs all have section-title
// labels but no IDs.
function _bySectionTitle(titleSubstring, sentence) {
  if (!sentence) return;
  const sections = document.querySelectorAll('.section');
  const needle = titleSubstring.toLowerCase();
  for (const sec of sections) {
    const titleEl = sec.querySelector('.section-title');
    if (titleEl && titleEl.textContent.toLowerCase().includes(needle)) {
      const el = sec.querySelector('.section-summary');
      if (el) el.textContent = sentence;
      return;
    }
  }
}

function bindUsersActivity(data) {
  if (!data) return;

  // Snapshot stats — Activity Overview row labels in admin.html are
  // exact matches: "Dau today", "Wau (7d)", "Mau (30d)", "Total registered",
  // "Stickiness", "New 7d". setStat is case-insensitive label match.
  const s = data.snapshot || {};
  setStat('Dau today',       SP_FMT.num(s.dau));
  setStat('Wau (7d)',        SP_FMT.num(s.wau));
  setStat('Mau (30d)',       SP_FMT.num(s.mau));
  setStat('Total registered', SP_FMT.num(s.total_registered));
  if (s.stickiness_pct != null) setStat('Stickiness', SP_FMT.num(s.stickiness_pct));
  setStat('New 7d',          SP_FMT.num(s.new_7d));

  // -- Two "what moved" rows that depend on user-activity data
  // (bindLiveData runs first but doesn't have access to these). DAU
  // delta vs 7d avg, logins 24h delta vs 7d avg.
  if (s.dau != null && s.dau_7d_avg != null) {
    const dauDelta = s.dau - s.dau_7d_avg;
    const dauPct = s.dau_7d_avg > 0 ? Math.round(100 * dauDelta / s.dau_7d_avg) : 0;
    const dauText = Math.abs(dauPct) < 5
      ? 'on track'
      : (dauPct > 0 ? `+${dauPct}% vs avg` : `${dauPct}% vs avg`);
    const dauClass = dauPct > 0 ? 'up' : (dauPct < 0 ? 'down' : '');
    setMovedRow('Daily active users', SP_FMT.num(s.dau), dauText, dauClass);
  }
  if (s.logins_24h != null && s.logins_7d_avg != null) {
    const lDelta = s.logins_24h - s.logins_7d_avg;
    const lPct = s.logins_7d_avg > 0 ? Math.round(100 * lDelta / s.logins_7d_avg) : 0;
    const lText = Math.abs(lPct) < 5
      ? 'on track'
      : (lPct > 0 ? `+${lPct}% vs avg` : `${lPct}% vs avg`);
    const lClass = lPct > 0 ? 'up' : (lPct < 0 ? 'down' : '');
    setMovedRow('Logins last 24h', SP_FMT.num(s.logins_24h), lText, lClass);
  }

  // Login Frequency tier counts — labels match: "Power (15+)",
  // "Engaged (5-14)", "Light (1-4)", "Dormant (0)".
  const tiers = data.tier_counts || {};
  if (tiers.power   != null) setStat('Power (15+)',     SP_FMT.num(tiers.power));
  if (tiers.engaged != null) setStat('Engaged (5-14)',  SP_FMT.num(tiers.engaged));
  if (tiers.light   != null) setStat('Light (1-4)',     SP_FMT.num(tiers.light));
  if (tiers.dormant != null) setStat('Dormant (0)',     SP_FMT.num(tiers.dormant));
  if (data.avg_logins != null)    setStat('Avg logins/user', SP_FMT.num(data.avg_logins));
  if (data.median_logins != null) setStat('Median logins',   SP_FMT.num(data.median_logins));

  // ── Users tab headline (h1.headline at top of panel) ──
  // Composes 3-4 facts: MAU, paying customers (Stripe truth), power
  // tier, attention items. Honest framing when the metrics are sparse.
  (() => {
    const headlineEl = document.querySelector('#panel-users .headline');
    if (!headlineEl) return;
    const sp = window.__SP_METRICS?.stripe?.payload || {};
    const mau = s.mau ?? null;
    const paying = sp.active_subs ?? null;
    const power = tiers.power ?? null;
    const cancelTrials = sp.trials_with_cancel_scheduled || 0;
    const cancelPaid = sp.paid_with_cancel_scheduled || 0;
    const attn = cancelTrials + cancelPaid;
    const bits = [];
    if (mau != null && mau > 0) bits.push(`${mau} monthly active${mau === 1 ? '' : 's'}`);
    if (paying != null) bits.push(`${paying} paying`);
    let sentence;
    if (bits.length === 0) {
      sentence = 'No active users in the last 30 days. Either the events table is empty or every user is internal.';
    } else {
      sentence = bits.join(', ') + '.';
      if (power != null && power > 0) sentence += ` ${power} power user${power === 1 ? '' : 's'} drive disproportionate engagement.`;
      if (attn > 0) sentence += ` ${attn} cancellation${attn === 1 ? '' : 's'} scheduled. Save window open.`;
    }
    headlineEl.textContent = sentence;
  })();

  // ── Update every Users-tab segment chip count from real data ──
  // Two distinct chip groups exist on the Users tab:
  //   #section-power-users    : All / Paid / Trial / Free  (15+ login users)
  //   #section-all-users      : All / Paid / Trial / Power / Dormant / Churned
  // Each chip's "All" reflects a different denominator, so they're scoped
  // to specific sections rather than the panel-wide selector.
  //
  // Source-of-truth rules (All Users group):
  //   All     -> snapshot.total_registered (real users only)
  //   Paid    -> Stripe.active_subs (PAYING customers, not DB drift)
  //   Trial   -> Stripe.trial_subs (cards on file, not yet billed)
  //   Power   -> tier_counts.power  (logins_30d >= 15)
  //   Dormant -> tier_counts.dormant
  //   Churned -> derived from a separate /list call below
  const metrics = window.__SP_METRICS;
  const stripePayload = metrics?.stripe?.payload || {};
  const total = s.total_registered;
  const paid = stripePayload.active_subs;
  const trial = stripePayload.trial_subs;
  const power = tiers.power;
  const dormant = tiers.dormant;

  const ALL_USERS_CHIPS = '#section-all-users .segment-chips';
  _setSegmentCount(ALL_USERS_CHIPS, 'All', total);
  _setSegmentCount(ALL_USERS_CHIPS, 'Paid', paid);
  _setSegmentCount(ALL_USERS_CHIPS, 'Trial', trial);
  _setSegmentCount(ALL_USERS_CHIPS, 'Power', power);
  _setSegmentCount(ALL_USERS_CHIPS, 'Dormant', dormant);

  // Power Users chips: "All" = power tier headline, "Paid"/"Trial"/"Free"
  // need a per-power-user split from the actual list. We don't have the
  // breakdown here yet; bindPowerUsersList fills these from its data.
  const POWER_CHIPS = '#section-power-users .segment-chips';
  _setSegmentCount(POWER_CHIPS, 'All', power);

  // Churned count needs its own /list call since the activity payload
  // doesn't aggregate it. Lightweight: limit=1 just to read .filtered.
  fetch('/api/admin/users/list?segment=churned&limit=1', { credentials: 'same-origin' })
    .then(r => r.ok ? r.json() : null)
    .then(d => {
      if (d && d.filtered != null) {
        _setSegmentCount(ALL_USERS_CHIPS, 'Churned', d.filtered);
      }
    })
    .catch(() => {});

  // -- Users tab section summaries (real data from this endpoint) --
  // section-users-snapshot, section-login-frequency, section-cohort-retention
  // (the section IDs aren't yet on the markup; we target by .section-title
  // text content as a fallback so these populate even without explicit IDs.)

  // Activity snapshot summary — top of Users tab
  // The Users tab uses "activity overview" as the section title;
  // the Command tab uses "user activity · 30d". Set both — the
  // server-side compute_summaries also sets section-user-activity
  // by ID (Command tab); this title-match catches the Users-tab
  // section.
  if (s.dau != null) {
    const dauActive = s.dau > 0 ? `${s.dau} DAU today` : 'no DAU today';
    const stickiness = s.mau > 0 ? `${s.stickiness_pct}% stickiness (DAU/MAU)` : '';
    const newUsers = s.new_7d > 0 ? `${s.new_7d} new in the last 7 days` : 'no new signups this week';
    const power = (tiers.power || 0);
    const powerStr = power > 0 ? `${power} power user${power === 1 ? '' : 's'} (15+ logins)` : 'no power-tier users yet';
    _bySectionTitle('activity overview', `${dauActive}. ${stickiness ? stickiness + '. ' : ''}${newUsers}. ${powerStr}.`);
  }

  // Login frequency summary + chart visibility. The metric reads
  // session_start events (instrumented since 2026-03-24), so the '0'
  // bucket reflects users who genuinely haven't opened the app in 30d
  // rather than missing instrumentation. Hide the histogram only if
  // fewer than 20% of users have any activity (true cold-start).
  const buckets = data.login_frequency_buckets || {};
  const totalUsers = Object.values(buckets).reduce((a, b) => a + b, 0);
  const zeroBucket = buckets['0'] || 0;
  const loggedInUsers = totalUsers - zeroBucket;
  const loggedInPct = totalUsers > 0 ? (100 * loggedInUsers / totalUsers) : 0;

  const freqSection = Array.from(document.querySelectorAll('.section')).find(s => {
    const t = s.querySelector('.section-title');
    return t && t.textContent.toLowerCase().includes('login frequency');
  });
  const freqChartWrap = freqSection?.querySelector('.chart-wrap');

  if (totalUsers === 0) {
    _bySectionTitle('login frequency', 'No users in the metrics scope yet.');
    if (freqChartWrap) freqChartWrap.style.display = 'none';
  } else if (loggedInPct < 20) {
    _bySectionTitle('login frequency',
      `Only ${loggedInUsers} of ${totalUsers} users active in the last 30 days. Histogram suppressed below the 20% engagement floor.`);
    if (freqChartWrap) freqChartWrap.style.display = 'none';
  } else {
    if (freqChartWrap) freqChartWrap.style.display = '';
    const power = (buckets['15-19'] || 0) + (buckets['20-29'] || 0) + (buckets['30+'] || 0);
    const light = (buckets['1'] || 0) + (buckets['2-3'] || 0) + (buckets['4-5'] || 0);
    const lightPct = Math.round(100 * light / totalUsers);
    const powerPct = Math.round(100 * power / totalUsers);
    _bySectionTitle('login frequency',
      `${loggedInUsers} of ${totalUsers} users active this month. Light tier (1-5 logins) is ${lightPct}%, power tier (15+) is ${powerPct}%.`);
  }

  // Cohort retention summary — section title is "retention · weekly cohorts"
  const cohorts = Array.isArray(data.cohort_retention) ? data.cohort_retention : [];
  if (cohorts.length > 0) {
    const avgWeek1 = Math.round(
      cohorts.map(c => (c.retention_by_week || [])[1] || 0).reduce((a, b) => a + b, 0) / cohorts.length
    );
    const avgWeek4 = Math.round(
      cohorts.map(c => (c.retention_by_week || [])[4] || 0).reduce((a, b) => a + b, 0) / cohorts.length
    );
    if (avgWeek1 === 0 && avgWeek4 === 0) {
      _bySectionTitle('retention', `No cohort retention yet. Table will fill in as users return week-over-week.`);
    } else {
      _bySectionTitle('retention', `Week-1 retention averages ${avgWeek1}% across the last ${cohorts.length} cohorts. Week-4 averages ${avgWeek4}%.`);
    }
  }

  // Power Users leaderboard summary — needs the user list to derive
  // tag breakdown. We have tier_counts.power for the headline number;
  // the iOS-vs-web split needs more data. For now, single-fact summary.
  if (tiers.power != null) {
    if (tiers.power === 0) {
      _bySectionTitle('power users', `No power-tier users yet (15+ logins in 30 days). Power tier surfaces the heaviest-using accounts as data accrues.`);
    } else {
      _bySectionTitle('power users', `${tiers.power} user${tiers.power === 1 ? '' : 's'} in the power tier (15+ logins in 30 days). They drive disproportionate engagement on the funnel below.`);
    }
  }

  // Replace the DAU 90d bar chart (Users tab) with real daily counts.
  // Series is backed by session_start events (instrumented 2026-03-24);
  // need >= 7 days of activity before we'll render over the placeholder,
  // so brand-new installs show the mockup until enough data accrues.
  const dauCanvas = document.getElementById('chart-users-dau');
  const dauChart = dauCanvas && Chart.getChart(dauCanvas);
  if (dauChart && Array.isArray(data.dau_daily_90d)) {
    const counts = data.dau_daily_90d.map(d => d.users);
    if (_hasRealValues(counts, 7)) {
      dauChart.data.labels = data.dau_daily_90d.map(d => d.date.slice(5));
      dauChart.data.datasets[0].data = counts;
      dauChart.update('none');
    }
  }

  // Same data, the trimmed-to-30d view that lives on the Command tab.
  // Different canvas id, same threshold gate.
  const dauCmdCanvas = document.getElementById('chart-dau');
  const dauCmdChart = dauCmdCanvas && Chart.getChart(dauCmdCanvas);
  if (dauCmdChart && Array.isArray(data.dau_daily_90d)) {
    const last30 = data.dau_daily_90d.slice(-30);
    const counts = last30.map(d => d.users);
    if (_hasRealValues(counts, 7)) {
      dauCmdChart.data.labels = last30.map(d => d.date.slice(5));
      dauCmdChart.data.datasets[0].data = counts;
      dauCmdChart.update('none');
    }
  }

  // Replace login frequency histogram with real bucket counts —
  // ONLY when there's enough data for the non-zero buckets to be
  // visible (otherwise the '0' bar dominates and the chart looks
  // broken). Same 20% threshold as the section-summary text above.
  const freqCanvas = document.getElementById('chart-login-freq');
  const freqChart = freqCanvas && Chart.getChart(freqCanvas);
  if (freqChart && data.login_frequency_buckets) {
    const ORDER = ['0', '1', '2-3', '4-5', '6-9', '10-14', '15-19', '20-29', '30+'];
    const counts = ORDER.map(k => data.login_frequency_buckets[k] || 0);
    const totalU = counts.reduce((a, b) => a + b, 0);
    const nonZeroBuckets = counts.slice(1).reduce((a, b) => a + b, 0);
    if (totalU > 0 && (nonZeroBuckets / totalU) >= 0.20) {
      freqChart.data.labels = ORDER;
      freqChart.data.datasets[0].data = counts;
      freqChart.update('none');
    }
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
  comped:           'comped',
  trial:            'trial',
  trial_annual:     'trial → annual',
  trial_monthly:    'trial → monthly',
  trial_founding:   'trial → founding',
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

// Update segment-chip counts from real data. Targets the chip whose
// label text starts with the given word (case-insensitive).
function _setSegmentCount(scopeSelector, labelWord, count) {
  if (count == null) return;
  const scope = document.querySelector(scopeSelector);
  if (!scope) return;
  const chips = scope.querySelectorAll('.segment-chip');
  for (const chip of chips) {
    const text = chip.textContent.trim().toLowerCase();
    if (text.startsWith(labelWord.toLowerCase())) {
      const countEl = chip.querySelector('.count');
      if (countEl) countEl.textContent = SP_FMT.num(count);
      return;
    }
  }
}

// Tags that describe a user's billing state. Replaced by the single
// descriptive billing label below; we still render overlay tags
// (power, ios, internal, comped, pending_verify) alongside it so the
// row keeps surfacing platform/activity flags.
const BILLING_TAG_SET = new Set([
  'founding', 'paid', 'paid_annual', 'paid_monthly',
  'trial', 'trial_annual', 'trial_monthly', 'trial_founding',
  'cancel_scheduled', 'past_due', 'churned', 'free',
]);

function _fmtMonthDay(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch { return ''; }
}

// Build the descriptive billing-state label per the operator spec:
//   Free
//   Trialing · converts to Pro {date}
//   Trialing · cancel scheduled {date}
//   Paid · Monthly
//   Paid · Annual
//   Paid · {plan} · cancels {date}
//   Founding · #N
// Returned `kind` maps to the existing user-tag CSS classes so colour
// stays consistent (founding gold, paid blue, trial amber, cancel
// amber-warn, churned red, free muted).
function _billingStatus(u) {
  const status = (u.subscription_status || '').toLowerCase();
  const plan = (u.subscription_plan || '').toLowerCase();
  const isAnnual = plan.includes('annual') || plan.includes('year') || plan.includes('founding');
  const isMonthly = plan.includes('month');

  if (u.founding_member) {
    const num = u.founding_number ? ` · #${u.founding_number}` : '';
    return { kind: 'founding', label: `Founding${num}` };
  }
  if (status === 'active') {
    if (isAnnual)  return { kind: 'paid_annual',  label: 'Paid · Annual' };
    if (isMonthly) return { kind: 'paid_monthly', label: 'Paid · Monthly' };
    return { kind: 'paid', label: 'Paid' };
  }
  if (status === 'cancelling') {
    const eff = _fmtMonthDay(u.cancel_effective_at);
    const planLabel = isAnnual ? 'Annual' : isMonthly ? 'Monthly' : '';
    const head = planLabel ? `Paid · ${planLabel}` : 'Paid';
    const tail = eff ? ` · cancels ${eff}` : ' · cancel scheduled';
    return { kind: 'cancel_scheduled', label: `${head}${tail}` };
  }
  if (status === 'trial' || status === 'trialing') {
    if (u.cancel_scheduled_at) {
      const eff = _fmtMonthDay(u.cancel_effective_at);
      const tail = eff ? ` ${eff}` : '';
      return { kind: 'cancel_scheduled', label: `Trialing · cancel scheduled${tail}` };
    }
    const end = _fmtMonthDay(u.trial_end_date);
    const tail = end ? ` ${end}` : '';
    return { kind: 'trial', label: `Trialing · converts to Pro${tail}` };
  }
  if (status === 'past_due') return { kind: 'past_due', label: 'Past due' };
  if (status === 'cancelled' || status === 'expired') {
    return { kind: 'churned', label: 'Free · was Pro' };
  }
  return { kind: 'free', label: 'Free' };
}

// Render a single user-row inside the given section. Used by both the
// Power Users leaderboard and the All Users list — same card shape, just
// different containers.
function _renderUserRow(u) {
  const row = document.createElement('div');
  row.className = 'user-row';

  const billing = _billingStatus(u);
  const billingChip = `<span class="user-tag ${billing.kind}">${billing.label}</span>`;
  const overlayTags = (u.tags || [])
    .filter(t => !BILLING_TAG_SET.has(t))
    .slice(0, 3)
    .map(_renderTag).join('');

  row.innerHTML = `
    <div class="user-identity">
      <span class="user-email">${u.email}</span>
      <div class="user-tags">${billingChip}${overlayTags}</div>
    </div>
    <div class="user-numeric" data-label="Logins 30d">${u.logins_30d}</div>
    <div class="user-numeric muted" data-label="Bet taps">${u.bet_taps_30d}</div>
    <div class="user-numeric muted" data-label="Days active">${u.days_active_30d}</div>
    <div class="user-numeric faint" data-label="Last seen">${u.last_seen_at ? u.last_seen_at.slice(5, 10) : '—'}</div>
  `;
  return row;
}

// Replace the rows inside `<section id>`'s users-grid-header → user-row
// region with the rendered version of `users[]`. Preserves the header
// row above the rows.
function _replaceUserRows(sectionId, users) {
  const sec = document.getElementById(sectionId);
  if (!sec) return;
  sec.querySelectorAll('.user-row').forEach(n => n.remove());
  // Find the anchor to insert after — header row, or fall back to the
  // section element itself.
  const header = sec.querySelector('.users-grid-header');
  const anchor = header || sec;
  const frag = document.createDocumentFragment();
  users.forEach(u => frag.appendChild(_renderUserRow(u)));
  anchor.after(frag);
}

function bindUsersList(data) {
  if (!data || !Array.isArray(data.users)) return;

  // Counts on the All Users segment chips — total is "all real users".
  _setSegmentCount('#section-all-users .segment-chips', 'All', data.total);

  _replaceUserRows('section-all-users', data.users);

  // Footer: "showing N of M · load more". Only show "load more" affordance
  // if we got the full page (filtered > limit suggests more exist).
  const footer = document.querySelector('#section-all-users .users-list-footer');
  if (footer) {
    const showing = data.users.length;
    const more = data.filtered != null && data.filtered > showing;
    footer.textContent = `showing ${showing} of ${data.filtered ?? data.total ?? showing}${more ? ' · load more' : ''}`;
  }
}

// Power Users leaderboard — same shape as All Users but a different
// list (segment=power) and a different container. Also derives the
// Paid/Trial/Free split for the chip counts in this section.
function bindPowerUsersList(data) {
  if (!data || !Array.isArray(data.users)) return;
  _replaceUserRows('section-power-users', data.users);

  // Per-power-user breakdown for the chips. Tags reflect the user's
  // actual subscription state.
  let paid = 0, trial = 0, free = 0;
  data.users.forEach(u => {
    const tags = u.tags || [];
    if (tags.includes('paid_annual') || tags.includes('paid_monthly') || tags.includes('founding') || tags.includes('comped')) {
      paid += 1;
    } else if (tags.includes('trial')) {
      trial += 1;
    } else {
      free += 1;
    }
  });
  const POWER_CHIPS = '#section-power-users .segment-chips';
  _setSegmentCount(POWER_CHIPS, 'Paid', paid);
  _setSegmentCount(POWER_CHIPS, 'Trial', trial);
  _setSegmentCount(POWER_CHIPS, 'Free', free);
}

// Needs Attention — small list of users in concerning states.
function bindNeedsAttention(data) {
  // Summary comes from Stripe payload counts (truth source for billing
  // states). data.users gives us per-user detail for the rows below.
  const sp = window.__SP_METRICS?.stripe?.payload || {};
  const cancelTrials = sp.trials_with_cancel_scheduled || 0;
  const cancelPaid = sp.paid_with_cancel_scheduled || 0;
  const failedUsers = sp.failed_payment_users_30d || 0;
  const churned30d = sp.canceled_30d || 0;
  const total = cancelTrials + cancelPaid + failedUsers;
  if (total === 0 && churned30d === 0) {
    _bySectionTitle('needs attention', `No users in concerning states this week. Revenue collection is clean and no cancellations queued.`);
  } else {
    const bits = [];
    if (cancelTrials > 0) bits.push(`${cancelTrials} trial${cancelTrials === 1 ? '' : 's'} with cancel scheduled`);
    if (cancelPaid > 0) bits.push(`${cancelPaid} paid sub${cancelPaid === 1 ? '' : 's'} with cancel scheduled`);
    if (failedUsers > 0) bits.push(`${failedUsers} customer${failedUsers === 1 ? '' : 's'} with failed payments in 30d`);
    if (churned30d > 0) bits.push(`${churned30d} cancelled in the last 30 days`);
    _bySectionTitle('needs attention', `${bits.join(', ')}. Highest-leverage outreach is the cancel-scheduled cohort — the save window closes at cancel_effective_at.`);
  }

  const container = document.getElementById('needs-attention-rows');
  if (!container) return;
  const users = (data && Array.isArray(data.users)) ? data.users.slice(0, 4) : [];
  container.innerHTML = '';
  if (users.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'recent-row empty';
    empty.innerHTML = '<span class="meta">No users in concerning states this week.</span>';
    container.appendChild(empty);
    return;
  }
  const today = new Date();
  users.forEach(u => {
    const row = document.createElement('div');
    row.className = 'recent-row';
    // Compose a useful left-side timestamp + middle meta + right-side tag.
    let ts = '—';
    let badge = 'reach out';
    let badgeColor = 'var(--warn)';
    let badgeBorder = 'rgba(228,160,59,0.3)';
    if (u.cancel_effective_at) {
      const eff = new Date(u.cancel_effective_at);
      const days = Math.ceil((eff - today) / (1000 * 60 * 60 * 24));
      if (days >= 0) {
        ts = `${days}d left`;
        badge = days <= 2 ? 'urgent' : 'cancel scheduled';
        badgeColor = days <= 2 ? 'var(--danger)' : 'var(--warn)';
        badgeBorder = days <= 2 ? 'rgba(228,129,129,0.3)' : 'rgba(228,160,59,0.3)';
      } else {
        ts = `${Math.abs(days)}d ago`;
        badge = 'cancelled';
        badgeColor = 'var(--text-faint)';
        badgeBorder = 'var(--border)';
      }
    } else if ((u.tags || []).includes('past_due')) {
      ts = 'now';
      badge = 'payment failed';
      badgeColor = 'var(--danger)';
      badgeBorder = 'rgba(228,129,129,0.3)';
    }
    const subBits = [];
    if (u.subscription_status) subBits.push(u.subscription_status);
    if (u.logins_30d != null) subBits.push(`${u.logins_30d} logins/30d`);
    const sub = subBits.length ? ' · ' + subBits.join(' · ') : '';
    row.innerHTML = `
      <span class="ts">${ts}</span>
      <span class="meta">${u.email}${sub}</span>
      <span class="tag" style="color: ${badgeColor}; border-color: ${badgeBorder};">${badge}</span>
    `;
    container.appendChild(row);
  });
}

// Fetch Users tab data only when the user actually clicks into the tab —
// saves a query on initial load. Cache the response so re-clicks don't
// re-fetch.
// In-flight promise lets multiple eager triggers (page load + tab click +
// poll) coalesce onto one fetch. Cleared as soon as the fetch resolves so
// the next call re-fetches fresh — no time-based caching here, the dashboard
// trusts every call.
let _usersDataPromise = null;
function loadUsersTabData() {
  if (_usersDataPromise) return _usersDataPromise;
  const opts = { credentials: 'same-origin' };
  _usersDataPromise = Promise.all([
    fetch('/api/admin/users/activity?range=30d', opts).then(r => r.ok ? r.json() : null),
    fetch('/api/admin/users/list?segment=all&limit=50', opts).then(r => r.ok ? r.json() : null),
    fetch('/api/admin/users/list?segment=power&limit=20', opts).then(r => r.ok ? r.json() : null),
    fetch('/api/admin/users/list?segment=attention&limit=10', opts).then(r => r.ok ? r.json() : null),
  ]).then(([activity, allUsers, powerUsers, attention]) => {
    bindUsersActivity(activity);
    bindUsersList(allUsers);
    bindPowerUsersList(powerUsers);
    bindNeedsAttention(attention);
  }).finally(() => {
    _usersDataPromise = null;  // clear so next call re-fetches
  });
  return _usersDataPromise;
}

document.querySelector('.tab[data-tab="users"]')?.addEventListener('click', loadUsersTabData);
document.querySelectorAll('[data-deep-link="users"]').forEach(l => l.addEventListener('click', loadUsersTabData));

// ─────────────────────────────────────────────────────────────────────────
// Model tab data binding (Phase 3.6)
// /api/admin/model/perf returns {win_rate_by_sport_daily,
// hit_rate_by_edge_tier, calibration, edge_distribution, last_10_signals}
// ─────────────────────────────────────────────────────────────────────────

// Helper: returns true if a numeric series has at least `minCount`
// non-null, non-zero values. Used to guard chart updates so we don't
// blank out the mockup placeholder with sparse real-data responses
// (a chart with 1-2 valid points and 100+ nulls renders as
// essentially-invisible — better to keep the placeholder).
function _hasRealValues(arr, minCount = 5) {
  if (!Array.isArray(arr) || arr.length === 0) return false;
  let count = 0;
  for (const v of arr) {
    if (v != null && v !== 0) {
      count++;
      if (count >= minCount) return true;
    }
  }
  return false;
}

function bindModelPerf(data) {
  if (!data) return;

  // ── Model tab headline ──
  (() => {
    const headlineEl = document.querySelector('#panel-model .headline');
    if (!headlineEl) return;
    const sportSeries = data.win_rate_by_sport_daily || {};
    const sportNames = Object.keys(sportSeries);
    const phrases = sportNames.map(s => {
      const series = sportSeries[s] || [];
      for (let i = series.length - 1; i >= 0; i--) {
        if (series[i].win_rate != null) return `${s.toUpperCase()} at ${series[i].win_rate}% (n=${series[i].sample_n})`;
      }
      return null;
    }).filter(Boolean);
    if (phrases.length === 0) {
      headlineEl.textContent = 'Not enough resolved picks per sport for a 14d-rolling read yet. Data accumulates as games settle.';
    } else {
      const breakeven = phrases.length === 1 ? '. 52.4% is breakeven against -110 lines.' : '. Breakeven is 52.4%.';
      headlineEl.textContent = phrases.join(', ') + breakeven;
    }
  })();

  // Win rate vs market chart (NBA + MLB rolling 14d). Skip update if
  // there are not enough resolved picks per sport — keeps the mockup
  // line visible until real data accumulates. Need >= 14 days of
  // resolved picks per sport for a 14d rolling line to be honest.
  const winChart = Chart.getChart(document.getElementById('chart-winrate'));
  if (winChart && data.win_rate_by_sport_daily) {
    const sports = Object.keys(data.win_rate_by_sport_daily);
    if (sports.length > 0) {
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
          spanGaps: true,
        };
      });
      const anyReal = datasets.some(ds => _hasRealValues(ds.data, 14));
      if (anyReal) {
        winChart.data.labels = (data.win_rate_by_sport_daily[sports[0]] || []).map(d => d.date.slice(5));
        winChart.data.datasets = datasets;
        winChart.update('none');
      }
    }
  }

  // Hit rate by edge tier
  const meiChart = Chart.getChart(document.getElementById('chart-meihit'));
  if (meiChart && Array.isArray(data.hit_rate_by_edge_tier)) {
    const values = data.hit_rate_by_edge_tier.map(t => t.hit_rate);
    if (_hasRealValues(values)) {
      meiChart.data.labels = data.hit_rate_by_edge_tier.map(t => t.tier);
      meiChart.data.datasets[0].data = values.map(v => v || 0);
      meiChart.update('none');
    }
  }

  // Calibration plots: NBA + MLB. Already guarded against empty
  // series; preserve the existing skip behavior.
  ['nba', 'mlb'].forEach(sport => {
    const chart = Chart.getChart(document.getElementById('chart-cal-' + sport));
    if (!chart) return;
    const series = (data.calibration || {})[sport] || (data.calibration || {})[sport.toUpperCase()] || [];
    if (!series.length) return;
    if (!series.some(p => p.observed != null)) return;
    chart.data.labels = series.map(p => p.predicted);
    chart.data.datasets[0].data = series.map(p => ({ x: p.predicted, y: p.observed }));
    chart.update('none');
  });

  // Edge distribution histogram
  const meiDist = Chart.getChart(document.getElementById('chart-mei'));
  if (meiDist && Array.isArray(data.edge_distribution)) {
    const counts = data.edge_distribution.map(b => b.count);
    if (_hasRealValues(counts)) {
      meiDist.data.labels = data.edge_distribution.map(b => b.tier);
      meiDist.data.datasets[0].data = counts;
      meiDist.update('none');
    }
  }

  // -- Model tab section summaries --
  // Win rate vs market summary
  const winBySport = data.win_rate_by_sport_daily || {};
  const sportNames = Object.keys(winBySport);
  if (sportNames.length > 0) {
    const lastValues = sportNames.map(s => {
      const series = winBySport[s] || [];
      for (let i = series.length - 1; i >= 0; i--) {
        if (series[i].win_rate != null) return { sport: s.toUpperCase(), rate: series[i].win_rate, n: series[i].sample_n };
      }
      return null;
    }).filter(Boolean);
    if (lastValues.length > 0) {
      const phrase = lastValues.map(lv => `${lv.sport} ${lv.rate}% (n=${lv.n})`).join(', ');
      _bySectionTitle('win rate', `Latest 14d-rolling win rate: ${phrase}. 52.4% is breakeven against -110 lines.`);
    } else {
      _bySectionTitle('win rate', 'Not enough resolved picks per sport for a 14d rolling read yet.');
    }
  }

  // Hit rate by edge tier
  const tiers = Array.isArray(data.hit_rate_by_edge_tier) ? data.hit_rate_by_edge_tier : [];
  if (tiers.length > 0 && tiers.some(t => t.hit_rate != null)) {
    const top = tiers[tiers.length - 1];
    if (top && top.hit_rate != null) {
      _bySectionTitle('hit rate', `Top edge tier (${top.tier}) hits ${top.hit_rate}% on ${top.sample_n} picks. Higher edge tiers should out-hit lower — that's the threshold doing real work.`);
    }
  } else {
    _bySectionTitle('hit rate', 'Edge tier hit-rate computation needs resolved picks. Currently sparse.');
  }

  // Calibration plots — one summary covers both NBA and MLB
  const cal = data.calibration || {};
  const calSports = Object.keys(cal);
  if (calSports.length > 0) {
    const fragments = calSports.map(s => {
      const points = (cal[s] || []).filter(p => p.observed != null);
      if (points.length === 0) return null;
      const samples = points.reduce((a, p) => a + (p.sample_n || 0), 0);
      return `${s.toUpperCase()} (${points.length} buckets, n=${samples})`;
    }).filter(Boolean);
    if (fragments.length > 0) {
      _bySectionTitle('calibration', `Calibration coverage: ${fragments.join(' · ')}. Closer the points sit to the diagonal, the better the model's probability estimates.`);
    } else {
      _bySectionTitle('calibration', 'Not enough resolved picks with cover_prob to plot calibration yet.');
    }
  }

  // Edge distribution / MEI histogram
  const edgeDist = Array.isArray(data.edge_distribution) ? data.edge_distribution : [];
  const totalPicks = edgeDist.reduce((a, b) => a + (b.count || 0), 0);
  if (totalPicks > 0) {
    const above = edgeDist.filter(b => {
      const lo = parseFloat(b.tier);
      return !isNaN(lo) && lo >= 4;
    }).reduce((a, b) => a + (b.count || 0), 0);
    const sharpPct = Math.round(100 * above / totalPicks);
    _bySectionTitle('mei distribution', `${totalPicks} picks scored in the last 30 days. ${sharpPct}% cleared the 4% edge threshold.`);
  } else {
    _bySectionTitle('mei distribution', 'No scored picks in the last 30 days.');
  }

  // Note: Last 10 signals on the Model tab is rendered into
  // #recent-signals via bindLiveData using the events source's
  // recent_signals array. No duplicate render here.
}

let _modelDataPromise = null;
function loadModelTabData() {
  if (_modelDataPromise) return _modelDataPromise;
  _modelDataPromise = fetch('/api/admin/model/perf?range=90d', { credentials: 'same-origin' })
    .then(r => r.ok ? r.json() : null)
    .then(bindModelPerf)
    .finally(() => { _modelDataPromise = null; });
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

  // ── Infra tab headline ──
  (() => {
    const headlineEl = document.querySelector('#panel-infra .headline');
    if (!headlineEl) return;
    const errors = c.errors_24h ?? null;
    const p95 = c.p95_24h_ms ?? null;
    const requests = c.requests_24h ?? null;
    const deploys = Array.isArray(data.recent_deploys) ? data.recent_deploys : [];
    const lastDeploy = deploys.length > 0 ? deploys[0] : null;
    if (requests == null || requests === 0) {
      headlineEl.textContent = 'No requests measured in the current window. Either traffic is zero or RequestMetric instrumentation is paused.';
    } else {
      const errPhrase = errors === 0 ? 'No 5xx errors today' : `${errors} 5xx error${errors === 1 ? '' : 's'} in 24h`;
      const p95Phrase = p95 != null && p95 > 0 ? `p95 at ${p95}ms` : '';
      const deployPhrase = lastDeploy ? `Last deploy ${lastDeploy.sha}.` : '';
      headlineEl.textContent = [errPhrase, p95Phrase].filter(Boolean).join(', ') + '.' + (deployPhrase ? ' ' + deployPhrase : '');
    }
  })();

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

  // Latency chart (p50/p95/p99 hourly, 168 buckets = 7d). request_metrics
  // table was just created; needs at least 24 hours of data before the
  // chart looks meaningful. Below that, keep the mockup placeholder
  // visible — a 1-out-of-168-buckets chart renders as essentially blank.
  const latChart = Chart.getChart(document.getElementById('chart-latency'));
  if (latChart && Array.isArray(data.latency_series)) {
    const p95Values = data.latency_series.map(p => p.p95);
    if (_hasRealValues(p95Values, 24) && latChart.data.datasets.length >= 3) {
      latChart.data.labels = data.latency_series.map(p => p.hour.slice(5, 13));
      latChart.data.datasets[0].data = data.latency_series.map(p => p.p50);
      latChart.data.datasets[1].data = data.latency_series.map(p => p.p95);
      latChart.data.datasets[2].data = data.latency_series.map(p => p.p99);
      latChart.data.datasets.forEach(ds => { ds.spanGaps = true; });
      latChart.update('none');
    }
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

  // -- Infra tab section summaries --
  const p95 = c.p95_24h_ms;
  const errors = c.errors_24h;
  const requests = c.requests_24h;
  if (requests != null) {
    const healthBits = [];
    if (requests > 0) healthBits.push(`${requests.toLocaleString()} requests last 24h`);
    if (p95 != null && p95 > 0) healthBits.push(`p95 ${p95}ms`);
    if (errors != null) healthBits.push(`${errors} 5xx error${errors === 1 ? '' : 's'}`);
    const summary = healthBits.length > 0
      ? `${healthBits.join(', ')}. ` + (errors === 0 ? 'No server errors today.' : 'Investigate the 5xx counts.')
      : 'request_metrics table is sparse — fills in as traffic accumulates.';
    _bySectionTitle('server health', summary);
  }

  // Latency series summary
  const series = Array.isArray(data.latency_series) ? data.latency_series : [];
  const populatedHours = series.filter(p => p.p95 != null).length;
  if (populatedHours > 0) {
    _bySectionTitle('latency', `${populatedHours} of ${series.length} hours have data so far. Lines fill in as traffic accumulates.`);
  }

  // Recent deploys
  const deploys = Array.isArray(data.recent_deploys) ? data.recent_deploys : [];
  if (deploys.length > 0) {
    const latest = deploys[0];
    _bySectionTitle('recent deploys', `${deploys.length} commits in this window. Latest: ${latest.sha} by ${latest.author}.`);
  } else {
    _bySectionTitle('recent deploys', 'git log not callable from the running container.');
  }

  // Database health summary
  if (dh.database_size_mb != null) {
    const conns = (dh.connections_active || 0) + (dh.connections_idle || 0);
    _bySectionTitle('database', `${dh.database_size_mb} MB total, ${conns} active connections.`);
  }
}

function bindCronHealth(data) {
  if (!data || !Array.isArray(data.jobs)) return;
  const container = document.querySelector('#panel-infra .pipeline-row')?.parentNode;
  if (!container) return;

  // Data pipeline section summary — health rollup of the cron jobs.
  const total = data.jobs.length;
  const healthy = data.jobs.filter(j => j.health === 'ok').length;
  const warn = data.jobs.filter(j => j.health === 'warn').length;
  const fail = data.jobs.filter(j => j.health === 'error' || j.health === 'never').length;
  if (total === 0) {
    _bySectionTitle('data pipeline', 'No cron jobs registered.');
  } else if (fail === 0 && warn === 0) {
    _bySectionTitle('data pipeline', `All ${total} scheduled jobs landed within their windows.`);
  } else {
    const bits = [`${healthy} of ${total} healthy`];
    if (warn > 0) bits.push(`${warn} warn`);
    if (fail > 0) bits.push(`${fail} failing or never run`);
    _bySectionTitle('data pipeline', `${bits.join(', ')}. Investigate failing jobs first; warn buckets are 1-2 windows late but recoverable.`);
  }

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
  }).finally(() => { _infraDataPromise = null; });
  return _infraDataPromise;
}

document.querySelector('.tab[data-tab="infra"]')?.addEventListener('click', loadInfraTabData);

// Wire segment chip clicks ONLY for the All Users section. The Power
// Users chips below are visual-only filters of the leaderboard and must
// not refetch the All Users list (a previous selector-overlap bug did).
document.querySelectorAll('#section-all-users .segment-chips .segment-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const seg = (chip.dataset.segment || chip.textContent.trim().split(/\s+/)[0] || 'all').toLowerCase();
    fetch(`/api/admin/users/list?segment=${seg}&limit=50`, { credentials: 'same-origin' })
      .then(r => r.ok ? r.json() : null)
      .then(bindUsersList)
      .catch(() => {});
  });
});

// Power Users chips: filter the rendered leaderboard rows by tag
// match, in-place. No API call — we already have all power users in
// the rendered DOM. Avoids re-fetching just to re-filter.
document.querySelectorAll('#section-power-users .segment-chips .segment-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const label = chip.textContent.trim().split(/\s+/)[0].toLowerCase();
    const sec = document.getElementById('section-power-users');
    if (!sec) return;
    sec.querySelectorAll('.user-row').forEach(row => {
      const tags = row.querySelectorAll('.user-tag');
      const tagSet = new Set([...tags].map(t => t.textContent.trim().toLowerCase()));
      let show = true;
      if (label === 'paid')  show = tagSet.has('paid annual') || tagSet.has('paid monthly') || tagSet.has('founding') || tagSet.has('comped');
      else if (label === 'trial') show = [...tagSet].some(t => t.startsWith('trial'));
      else if (label === 'free')  show = ![...tagSet].some(t => t.startsWith('paid') || t === 'founding' || t === 'comped' || t.startsWith('trial'));
      // 'all' shows everything.
      row.style.display = show ? '' : 'none';
    });
  });
});

// Eager pre-fetch for Users-tab data so the Command-tab "user activity"
// section (and the Users tab itself) populate without waiting for a
// click. Placed at end-of-file so the let _usersDataPromise binding
// has already initialized — calling earlier hits TDZ.
loadUsersTabData();

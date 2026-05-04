// SharpPicks Command Center — admin dashboard.
// Phase 3 Step 3.2: tab toggling + deep-link wiring.
// Pure DOM toggle, no router, no URL hash. Default active tab is Command
// (set in admin.html via .panel.active and .tab.active classes).

(function () {
  function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => {
      const isActive = t.dataset.tab === tabName;
      t.classList.toggle('active', isActive);
      t.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
    document.querySelectorAll('.panel').forEach(p => {
      p.classList.toggle('active', p.id === 'panel-' + tabName);
    });
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  // Tab clicks
  document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Deep-link cards: any element with data-deep-link="<tabName>" jumps tabs.
  document.querySelectorAll('[data-deep-link]').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      switchTab(link.dataset.deepLink);
    });
  });

  // Expose for future steps (deep-link inside fetched/rendered content can
  // call this once that content lands).
  window.SharpPicksAdmin = { switchTab };
})();

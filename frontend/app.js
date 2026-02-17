(function () {
  const REPORT_URL = '../data/latest_report.json';

  const loadingEl = document.getElementById('loading');
  const errorEl = document.getElementById('error');
  const gridEl = document.getElementById('commodities-grid');
  const statusEl = document.getElementById('global-status');

  function showLoading() {
    loadingEl.hidden = false;
    errorEl.hidden = true;
    gridEl.hidden = true;
    statusEl.textContent = '';
    statusEl.className = 'global-status';
  }

  function showError(msg) {
    loadingEl.hidden = true;
    gridEl.hidden = true;
    errorEl.hidden = false;
    errorEl.textContent = msg;
    statusEl.textContent = '';
    statusEl.className = 'global-status';
  }

  function getStatusClass(status) {
    const m = { CRITICAL: 'critical', WARNING: 'warning', STABLE: 'stable' };
    return m[status] || 'no_data';
  }

  function renderGlobalStatus(commodities) {
    const statuses = commodities.map((c) => c.status);
    const hasCritical = statuses.includes('CRITICAL');
    const hasWarning = statuses.includes('WARNING');
    const allStable = statuses.every((s) => s === 'STABLE');

    let text, cls;
    if (commodities.length === 0) {
      text = 'No data';
      cls = 'empty';
    } else if (hasCritical) {
      text = 'Supply chain stress detected – one or more commodities at CRITICAL risk';
      cls = 'critical';
    } else if (hasWarning) {
      text = 'Elevated risk – one or more commodities at WARNING level';
      cls = 'warning';
    } else if (allStable) {
      text = 'Supply chain stable – all monitored commodities within normal variance';
      cls = 'stable';
    } else {
      text = 'Report generated';
      cls = 'empty';
    }

    statusEl.textContent = text;
    statusEl.className = 'global-status ' + cls;
  }

  function renderCards(commodities) {
    gridEl.innerHTML = commodities
      .map(
        (c) => `
      <div class="card">
        <h3>${escapeHtml(c.name)}</h3>
        <div class="meta">Sample: ${c.sample_size} price records</div>
        <div class="price">${formatPrice(c.mean_price, c.currency)}</div>
        <div class="risk">Risk score: ${formatRisk(c.risk_score)}</div>
        <span class="badge ${getStatusClass(c.status)}">${escapeHtml(c.status)}</span>
      </div>
    `
      )
      .join('');
  }

  function escapeHtml(s) {
    if (s == null) return 'N/A';
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function formatPrice(mean, currency) {
    if (mean == null) return 'N/A';
    const curr = currency && currency !== 'N/A' ? ' ' + currency : '';
    return mean.toFixed(2) + curr;
  }

  function formatRisk(risk) {
    if (risk == null) return 'N/A';
    return risk.toFixed(4);
  }

  function render(data) {
    loadingEl.hidden = true;
    errorEl.hidden = true;
    gridEl.hidden = false;

    const commodities = data.commodities || [];
    renderGlobalStatus(commodities);
    renderCards(commodities);
  }

  fetch(REPORT_URL)
    .then((r) => {
      if (!r.ok) throw new Error('Report not available');
      return r.json();
    })
    .then((data) => {
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid report format');
      }
      render(data);
    })
    .catch(() => {
      showError(
        'Report not yet available. The daily scan runs at 08:00 UTC. Enable GitHub Pages and run the workflow to populate data.'
      );
    });

  showLoading();
})();

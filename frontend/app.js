(function () {
  // Cache-bust GitHub Pages JSON to avoid stale dashboards.
  const REPORT_URL = '../data/latest_report.json?v=' + Date.now();
  const OPEN_PRICES_API = 'https://prices.openfoodfacts.org/api/v1/prices';

  const loadingEl = document.getElementById('loading');
  const errorEl = document.getElementById('error');
  const gridEl = document.getElementById('commodities-grid');
  const statusEl = document.getElementById('global-status');
  const keywordInput = document.getElementById('keyword-input');
  const keywordBtn = document.getElementById('keyword-btn');
  const keywordResult = document.getElementById('keyword-result');

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

  function computeRisk(prices) {
    if (!Array.isArray(prices) || prices.length < 2) return { risk_score: null, status: 'NO_DATA' };
    const mean = prices.reduce((a, b) => a + b, 0) / prices.length;
    if (!isFinite(mean) || mean <= 0) return { risk_score: null, status: 'NO_DATA' };
    const variance =
      prices.reduce((sum, p) => sum + Math.pow(p - mean, 2), 0) / (prices.length - 1);
    const stdev = Math.sqrt(variance);
    const cv = stdev / mean;
    let status = 'STABLE';
    if (cv > 0.5) status = 'CRITICAL';
    else if (cv > 0.3) status = 'WARNING';
    return { risk_score: Number(cv.toFixed(4)), status, mean_price: Number(mean.toFixed(2)) };
  }

  function groupBy(records, keyFn) {
    const m = new Map();
    for (const r of records) {
      const k = keyFn(r);
      if (!m.has(k)) m.set(k, []);
      m.get(k).push(r);
    }
    return m;
  }

  function computeRegionRisks(records, level) {
    const keyFn =
      level === 'country'
        ? (r) => r.country || 'Unknown'
        : (r) => `${r.city || 'Unknown'}, ${r.country || 'Unknown'}`;
    const groups = groupBy(records, keyFn);
    const rows = [];
    for (const [region, recs] of groups.entries()) {
      const prices = recs.map((x) => x.price).filter((p) => typeof p === 'number');
      if (prices.length < 5) continue;
      const r = computeRisk(prices);
      rows.push({
        region,
        mean_price: r.mean_price ?? null,
        risk_score: r.risk_score,
        status: r.status,
        sample_size: prices.length,
      });
    }
    rows.sort((a, b) => {
      const ar = a.risk_score == null ? -1 : a.risk_score;
      const br = b.risk_score == null ? -1 : b.risk_score;
      return br - ar;
    });
    return rows.slice(0, 3);
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

  function renderRegions(c) {
    const regions = c.regions || {};
    const byCountry = regions.by_country || [];
    const byCity = regions.by_city || [];
    const renderList = (rows) => {
      if (!rows.length) return '<div class="meta">No regional breakdown available</div>';
      return `
        <ul class="region-list">
          ${rows
            .map(
              (r) => `
            <li class="region-item">
              <div>${escapeHtml(r.region)}</div>
              <span>${escapeHtml(r.status)} · ${formatRisk(r.risk_score)} · n=${r.sample_size}</span>
            </li>`
            )
            .join('')}
        </ul>`;
    };
    return `
      <div class="regions">
        <h4>Top stressed regions</h4>
        ${renderList(byCountry)}
        <div style="height:0.5rem"></div>
        ${renderList(byCity)}
      </div>
    `;
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
        ${renderRegions(c)}
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

  async function investigateKeyword() {
    const keyword = (keywordInput.value || '').trim();
    if (!keyword) return;

    keywordBtn.disabled = true;
    keywordResult.hidden = false;
    keywordResult.innerHTML = `<div class="loading">Investigating “${escapeHtml(keyword)}”...</div>`;

    try {
      const url = new URL(OPEN_PRICES_API);
      url.searchParams.set('product_name__like', keyword);
      url.searchParams.set('size', '50');
      url.searchParams.set('sort', '-date');
      const resp = await fetch(url.toString());
      if (!resp.ok) throw new Error('API failed');
      const json = await resp.json();
      const items = json.items || [];
      const records = items
        .map((it) => ({
          price: typeof it.price === 'number' ? it.price : Number(it.price),
          currency: it.currency || '',
          country: (it.location && it.location.osm_address_country) || 'Unknown',
          city: (it.location && it.location.osm_address_city) || 'Unknown',
        }))
        .filter((r) => Number.isFinite(r.price));

      const prices = records.map((r) => r.price);
      const overall = computeRisk(prices);
      const currency = records.map((r) => r.currency).find((c) => c) || 'N/A';
      const by_country = computeRegionRisks(records, 'country');
      const by_city = computeRegionRisks(records, 'city');

      const card = {
        name: keyword,
        mean_price: overall.mean_price ?? null,
        risk_score: overall.risk_score,
        status: overall.status,
        currency,
        sample_size: prices.length,
        regions: { by_country, by_city },
      };

      keywordResult.innerHTML = `<div class="commodities-grid">${renderCardHtml(card)}</div>`;
    } catch (e) {
      keywordResult.innerHTML =
        '<div class="error">Unable to query Open Prices API from the browser. If this persists, use the MCP tool <code>investigate_commodity</code> in Cursor.</div>';
    } finally {
      keywordBtn.disabled = false;
    }
  }

  function renderCardHtml(c) {
    return `
      <div class="card">
        <h3>${escapeHtml(c.name)}</h3>
        <div class="meta">Sample: ${c.sample_size} price records</div>
        <div class="price">${formatPrice(c.mean_price, c.currency)}</div>
        <div class="risk">Risk score: ${formatRisk(c.risk_score)}</div>
        <span class="badge ${getStatusClass(c.status)}">${escapeHtml(c.status)}</span>
        ${renderRegions(c)}
      </div>
    `;
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

  keywordBtn?.addEventListener('click', investigateKeyword);
  keywordInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') investigateKeyword();
  });
})();

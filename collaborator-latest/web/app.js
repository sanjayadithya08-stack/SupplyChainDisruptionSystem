import { createGlobe, RISK_COLORS, STATUS_COLORS } from './globe.js';
import { createBars3D } from './bars3d.js';

// Same-origin by default; override with ?api=http://host:port when serving the page elsewhere.
const API = new URLSearchParams(location.search).get('api') || '';

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const money = v => {
  const n = Number(v) || 0;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
};
const num = v => (Number(v) || 0).toLocaleString();
const pill = (text, color) => `<span class="pill" style="--c:${color}">${esc(text)}</span>`;
const riskPill = l => pill(l, RISK_COLORS[l] || RISK_COLORS.UNKNOWN);
const statusPill = s => pill(s, STATUS_COLORS[s] || '#8898b8');
const titleCase = s => String(s || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

async function api(path, opts = {}) {
  const res = await fetch(API + path, { headers: { 'Content-Type': 'application/json' }, ...opts });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function toast(msg, ms = 2800) {
  const t = $('#toast'); t.textContent = msg; t.classList.remove('hidden');
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.add('hidden'), ms);
}

const state = { network: null, shipments: [], scan: null, sort: { key: 'estimated_arrival', asc: true }, loaded: {} };

// ── Globe ───────────────────────────────────────────────────────────────────
const tooltip = $('#tooltip');
const globe = createGlobe($('#globe'), {
  onSelect: renderDetail,
  onHover(ud, e) {
    if (!ud) { tooltip.classList.add('hidden'); return; }
    const d = ud.data;
    const html = ud.kind === 'shipment'
      ? `<div class="t">${esc(d.id)} · ${esc(d.sku)}</div><div class="s">${esc(d.origin)} → ${esc(d.destination)} · ${esc(d.status)}</div>`
      : ud.kind === 'hub' ? `<div class="t">${esc(d.name)}</div><div class="s">Port / hub · ${esc(d.region)}</div>`
      : ud.kind === 'event' ? `<div class="t">${esc(d.country)} · ${esc(d.event_type)}</div><div class="s">${esc(d.severity)} — ${esc(d.description)}</div>`
      : '';
    tooltip.innerHTML = html;
    tooltip.style.left = `${e.clientX + 14}px`; tooltip.style.top = `${e.clientY + 14}px`;
    tooltip.classList.remove('hidden');
  },
  onAutoRotateChange(on) { const cb = $('input[data-layer="rotate"]'); if (cb) cb.checked = on; },
});

$$('#layerToggles input').forEach(cb => cb.addEventListener('change', () => {
  if (cb.dataset.layer === 'rotate') globe.setAutoRotate(cb.checked);
  else globe.setLayer(cb.dataset.layer, cb.checked);
}));

function renderDetail(ud) {
  const box = $('#detail');
  if (!ud) { box.innerHTML = '<h3>Selection</h3><p class="muted">Click a shipment, hub or event on the globe to inspect it.</p>'; return; }
  const d = ud.data;
  if (ud.kind === 'shipment') {
    const risk = state.scan?.find(r => r.shipment.id === d.id);
    box.innerHTML = `
      <h3>Shipment</h3>
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px">
        <strong style="font-size:18px">${esc(d.id)}</strong>${statusPill(d.status)}
      </div>
      <dl class="detail-grid">
        <dt>SKU</dt><dd>${esc(d.sku)}</dd>
        <dt>Supplier</dt><dd>${esc(d.supplier_name)}</dd>
        <dt>Lane</dt><dd>${esc(d.origin)} → ${esc(d.destination)}</dd>
        <dt>Carrier</dt><dd>${esc(d.carrier)} · ${esc(d.route_id)}</dd>
        <dt>ETA</dt><dd>${esc(d.estimated_arrival)}</dd>
        <dt>Units</dt><dd>${num(d.units)}</dd>
        <dt>Value</dt><dd>${money(d.value_usd)}</dd>
        ${risk ? `<dt>Predicted risk</dt><dd>${riskPill(risk.prediction.label)}</dd>` : ''}
      </dl>
      <div class="progress"><i style="width:${Math.round((d.progress ?? 0) * 100)}%"></i></div>
      <span class="muted small">${Math.round((d.progress ?? 0) * 100)}% of voyage complete</span>`;
  } else if (ud.kind === 'hub') {
    const out = state.shipments.filter(s => s.origin === d.name), inn = state.shipments.filter(s => s.destination === d.name);
    box.innerHTML = `<h3>Hub</h3><strong style="font-size:18px">${esc(d.name)}</strong>
      <dl class="detail-grid" style="margin-top:10px">
        <dt>Region</dt><dd>${esc(d.region)}</dd>
        <dt>Outbound</dt><dd>${out.length} shipments · ${money(out.reduce((a, s) => a + s.value_usd, 0))}</dd>
        <dt>Inbound</dt><dd>${inn.length} shipments · ${money(inn.reduce((a, s) => a + s.value_usd, 0))}</dd>
      </dl>`;
  } else if (ud.kind === 'event') {
    box.innerHTML = `<h3>Geo event</h3>
      <div style="display:flex;justify-content:space-between;align-items:center"><strong style="font-size:18px">${esc(d.country)}</strong>${riskPill(d.severity)}</div>
      <p>${esc(d.event_type)} — ${esc(d.description)}</p>
      <p class="muted small">Affects: ${esc((d.affected_routes || []).join(', '))}</p>`;
  }
}

// ── Navigation ──────────────────────────────────────────────────────────────
const loaders = { command: loadCommand, shipments: renderShipments, threats: () => {}, analytics: loadAnalytics, intel: loadIntel, system: loadSystem };
function show(view) {
  $$('.tabs button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.view === view)));
  $$('.view').forEach(v => v.classList.toggle('active', v.dataset.view === view));
  document.body.dataset.view = view;
  globe.resize();
  if (!state.loaded[view] || view === 'shipments') { state.loaded[view] = true; loaders[view]?.(); }
  history.replaceState(null, '', `#${view}`);
}
$$('.tabs button').forEach(b => b.addEventListener('click', () => show(b.dataset.view)));
window.addEventListener('hashchange', () => {
  const v = location.hash.slice(1);
  if (loaders[v] && document.body.dataset.view !== v) show(v);
});

// Subtle 3D tilt on cards
document.addEventListener('pointermove', e => {
  const card = e.target.closest?.('.tilt, .kpi');
  $$('.tilt, .kpi').forEach(c => { if (c !== card) c.style.transform = ''; });
  if (!card || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const r = card.getBoundingClientRect();
  const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
  card.style.transform = `perspective(700px) rotateY(${x * 7}deg) rotateX(${-y * 7}deg) translateZ(4px)`;
});

// ── Health ──────────────────────────────────────────────────────────────────
async function loadHealth() {
  const el = $('#status');
  try {
    const h = await api('/monitor/health');
    el.className = `status ${h.status === 'healthy' ? 'ok' : 'warn'}`;
    $('.label', el).textContent = `${h.status === 'healthy' ? 'Online' : 'Degraded'} · v${h.version}`;
    $('#offline').classList.add('hidden');
    return h;
  } catch {
    el.className = 'status down'; $('.label', el).textContent = 'API offline';
    $('#offline').classList.remove('hidden');
    // retry quickly while offline so the banner clears soon after the API comes back
    clearTimeout(loadHealth._retry); loadHealth._retry = setTimeout(loadHealth, 5000);
    return null;
  }
}

// ── Command ─────────────────────────────────────────────────────────────────
function kpi(label, value, color) {
  return `<div class="kpi" style="--c:${color}"><div class="v">${value}</div><div class="l">${esc(label)}</div></div>`;
}

async function loadCommand() {
  try {
    const net = await api('/network');
    state.network = net; state.shipments = net.shipments;
    globe.setData(net);
    const active = net.shipments.filter(s => s.status !== 'Delivered');
    const delayed = active.filter(s => s.status === 'Delayed').length;
    const critRoutes = net.routes.filter(r => r.risk_level === 'CRITICAL' || r.risk_level === 'HIGH').length;
    $('#kpis').innerHTML =
      kpi('Active shipments', active.length, '#38e1ff') +
      kpi('Value in transit', money(active.reduce((a, s) => a + s.value_usd, 0)), '#2fe39a') +
      kpi('Delayed', delayed, delayed ? '#ff3d71' : '#2fe39a') +
      kpi('High-risk lanes', `${critRoutes}/${net.routes.length}`, '#ff8a3d');
    const hot = net.events.filter(e => ['HIGH', 'CRITICAL'].includes(e.severity))
      .sort((a, b) => (b.severity === 'CRITICAL') - (a.severity === 'CRITICAL'));
    $('#hotspots').innerHTML = hot.map((e, i) => `
      <li class="clickable" data-i="${i}">
        <div class="grow"><div class="t">${esc(e.country)} · ${esc(e.event_type)}</div><div class="s">${esc(e.description)}</div></div>
        ${riskPill(e.severity)}
      </li>`).join('') || '<li class="empty">No high-severity events.</li>';
    $$('#hotspots li[data-i]').forEach(li => li.addEventListener('click', () => {
      const e = hot[+li.dataset.i]; globe.flyTo(e.lat, e.lon, 2.3); renderDetail({ kind: 'event', data: e });
    }));
  } catch (err) {
    $('#kpis').innerHTML = `<div class="card">Could not load network: ${esc(err.message)}</div>`;
  }
}

// ── Shipments ───────────────────────────────────────────────────────────────
function renderShipments() {
  const q = $('#shipSearch').value.trim().toLowerCase(), st = $('#shipStatus').value;
  const { key, asc } = state.sort;
  const rows = state.shipments
    .filter(s => !st || s.status === st)
    .filter(s => !q || [s.id, s.sku, s.supplier_name, s.origin, s.destination, s.carrier].some(v => String(v).toLowerCase().includes(q)))
    .sort((a, b) => (a[key] > b[key] ? 1 : a[key] < b[key] ? -1 : 0) * (asc ? 1 : -1));
  $('#shipTable tbody').innerHTML = rows.map(s => `
    <tr data-id="${esc(s.id)}">
      <td><strong>${esc(s.id)}</strong><div class="sub">${esc(s.sku)}</div></td>
      <td>${esc(s.supplier_name)}<div class="sub">${esc(s.supplier_country)}</div></td>
      <td>${esc(s.origin)} → ${esc(s.destination)}<div class="sub">${esc(s.carrier)}</div></td>
      <td>${esc(s.estimated_arrival)}</td>
      <td class="num">${money(s.value_usd)}<div class="sub">${num(s.units)} u</div></td>
      <td>${statusPill(s.status)}</td>
    </tr>`).join('') || '<tr><td colspan="6" class="empty">No shipments match.</td></tr>';
  $$('#shipTable th').forEach(th => {
    th.classList.toggle('sorted', th.dataset.sort === key); th.classList.toggle('asc', th.dataset.sort === key && asc);
  });
}
$('#shipSearch').addEventListener('input', renderShipments);
$('#shipStatus').addEventListener('change', renderShipments);
$$('#shipTable th').forEach(th => th.addEventListener('click', () => {
  const k = th.dataset.sort;
  state.sort = { key: k, asc: state.sort.key === k ? !state.sort.asc : true };
  renderShipments();
}));
$('#shipTable tbody').addEventListener('click', e => {
  const tr = e.target.closest('tr[data-id]'); if (!tr) return;
  $$('#shipTable tr.sel').forEach(r => r.classList.remove('sel')); tr.classList.add('sel');
  globe.focusShipment(tr.dataset.id);
});

// ── Threat radar ────────────────────────────────────────────────────────────
const RANK = { CRITICAL: 3, HIGH: 2, MEDIUM: 1, LOW: 0, UNKNOWN: -1 };
function planHtml(plan) {
  if (!plan) return '<p class="muted small">Risk is low — no prevention plan required.</p>';
  const sec = (t, a) => a?.length ? `<h4>${t}</h4><ul>${a.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : '';
  return `<div class="plan">
    <div style="display:flex;gap:8px;flex-wrap:wrap">${pill(plan.priority, '#7c6cff')} ${pill(plan.estimated_cost_impact, '#ffc845')} ${pill(plan.generated_by || 'rule-engine', '#38e1ff')}</div>
    ${plan.llm_summary ? `<p>${esc(plan.llm_summary)}</p>` : ''}
    ${sec('Immediate', plan.immediate_actions)}${sec('Short term', plan.short_term_actions)}
    ${sec('Long term', plan.long_term_actions)}${sec('Inventory', plan.inventory_recommendations)}
  </div>`;
}

async function runScan() {
  const btn = $('#scanBtn'); btn.classList.add('loading'); btn.disabled = true;
  $('#threatList').innerHTML = '<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>';
  try {
    const data = await api('/shipments/threats');
    state.scan = data;
    const risk = Object.fromEntries(data.map(r => [r.shipment.id, r.prediction.label]));
    globe.setShipmentRisk(risk);
    const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    let exposure = 0;
    data.forEach(r => { counts[r.prediction.label] = (counts[r.prediction.label] || 0) + 1; if (RANK[r.prediction.label] >= 2) exposure += r.shipment.value_usd; });
    $('#radarSummary').innerHTML =
      kpi('Critical', counts.CRITICAL, RISK_COLORS.CRITICAL) + kpi('High', counts.HIGH, RISK_COLORS.HIGH) +
      kpi('Medium / low', counts.MEDIUM + counts.LOW, RISK_COLORS.LOW) + kpi('Value exposed', money(exposure), '#7c6cff');
    const sorted = [...data].sort((a, b) => RANK[b.prediction.label] - RANK[a.prediction.label] || b.shipment.value_usd - a.shipment.value_usd);
    $('#threatList').innerHTML = sorted.map(r => {
      const s = r.shipment, l = r.prediction.label, c = RISK_COLORS[l] || RISK_COLORS.UNKNOWN;
      return `<details class="threat" style="--c:${c}" ${RANK[l] >= 3 ? 'open' : ''}>
        <summary>
          <div class="grow"><strong>${esc(s.id)}</strong> · ${esc(s.supplier_name)}
            <div class="muted small">${esc(s.origin)} → ${esc(s.destination)} · ${money(s.value_usd)} · ${r.threats.length} signal${r.threats.length === 1 ? '' : 's'}</div></div>
          ${riskPill(l)}
          <button class="btn" data-fly="${esc(s.id)}" title="Show on globe">Locate</button>
        </summary>
        <div class="body">
          ${r.threats.map(t => `<div class="sig" style="--c:${RISK_COLORS[t.severity] || c}">[${esc(t.source)}] ${esc(t.desc)}</div>`).join('') || '<p class="muted small">No regional signals.</p>'}
          ${planHtml(r.plan)}
        </div>
      </details>`;
    }).join('');
    $('#notifyBtn').disabled = !(counts.CRITICAL + counts.HIGH);
    $('#notifyBtn').title = 'Send prevention plans to supplier and receiver contacts';
    toast(`Scan complete — ${counts.CRITICAL} critical, ${counts.HIGH} high-risk shipments`);
  } catch (err) {
    $('#threatList').innerHTML = `<p class="empty">Scan failed: ${esc(err.message)}</p>`;
  } finally { btn.classList.remove('loading'); btn.disabled = false; }
}
$('#scanBtn').addEventListener('click', runScan);
$('#threatList').addEventListener('click', e => {
  const b = e.target.closest('[data-fly]'); if (!b) return;
  e.preventDefault(); globe.focusShipment(b.dataset.fly);
});
$('#notifyBtn').addEventListener('click', async () => {
  const n = state.scan?.filter(r => RANK[r.prediction.label] >= 2).length || 0;
  if (!confirm(`Send prevention plans for ${n} high-risk shipment(s) to their supplier and receiver contacts?`)) return;
  const btn = $('#notifyBtn'); btn.classList.add('loading');
  try {
    const r = await api('/shipments/threats/notify', { method: 'POST' });
    toast(`Dispatched ${r.alerts_sent} alert(s)`);
  } catch (err) { toast(`Dispatch failed: ${err.message}`); }
  finally { btn.classList.remove('loading'); }
});

// ── Analytics ───────────────────────────────────────────────────────────────
const TYPE_COLORS = { normal: '#2fe39a', port_strike: '#ffc845', weather: '#4f8bff', war: '#ff3d71', cyber: '#a66bff', supplier: '#ff8a3d', logistics: '#38e1ff', customs: '#ffd76b' };
const REGION_COLORS = ['#38e1ff', '#7c6cff', '#ff3d71', '#ffc845', '#2fe39a', '#ff8a3d', '#4f8bff', '#e86bff', '#9be15d', '#ff6b9a'];
let bars3d = null;

function trendSvg(byMonth) {
  const entries = Object.entries(byMonth).sort(([a], [b]) => a.localeCompare(b));
  if (!entries.length) return '<p class="empty">No data.</p>';
  const W = 560, H = 160, P = 24;
  const max = Math.max(...entries.map(([, v]) => v), 1);
  const x = i => P + (i / Math.max(entries.length - 1, 1)) * (W - P * 2);
  const y = v => H - P - (v / max) * (H - P * 2);
  const line = entries.map(([, v], i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const area = `${line} L${x(entries.length - 1)},${H - P} L${x(0)},${H - P} Z`;
  const ticks = entries.filter((_, i) => i % Math.ceil(entries.length / 6) === 0)
    .map(([m]) => `<text x="${x(entries.findIndex(e => e[0] === m))}" y="${H - 6}" fill="#8898b8" font-size="10" text-anchor="middle">${esc(m)}</text>`).join('');
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Revenue at risk per month">
    <defs><linearGradient id="tg" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#38e1ff" stop-opacity=".45"/><stop offset="1" stop-color="#38e1ff" stop-opacity="0"/></linearGradient></defs>
    <path d="${area}" fill="url(#tg)"/><path d="${line}" fill="none" stroke="#38e1ff" stroke-width="2" vector-effect="non-scaling-stroke"/>
    ${entries.map(([m, v], i) => `<circle cx="${x(i)}" cy="${y(v)}" r="2.5" fill="#38e1ff"><title>${esc(m)}: ${money(v)}</title></circle>`).join('')}
    ${ticks}</svg>`;
}

function ring(pct, color, size = 84, label = '') {
  const r = 34, C = 2 * Math.PI * r, p = Math.max(0, Math.min(100, pct));
  return `<svg viewBox="0 0 84 84" width="${size}" height="${size}" role="img" aria-label="${esc(label)} ${p}%">
    <circle cx="42" cy="42" r="${r}" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="8"/>
    <circle cx="42" cy="42" r="${r}" fill="none" stroke="${color}" stroke-width="8" stroke-linecap="round"
      stroke-dasharray="${(C * p / 100).toFixed(1)} ${C.toFixed(1)}" transform="rotate(-90 42 42)"/>
    <text x="42" y="47" text-anchor="middle" fill="#e7efff" font-size="15" font-weight="700">${Math.round(p)}%</text></svg>`;
}

async function loadAnalytics() {
  try {
    const histP = api('/company/history').catch(() => []);
    $('#accuracy').innerHTML = '<div class="skeleton"></div><div class="skeleton"></div>';
    const s = await api('/company/stats');
    $('#aKpis').innerHTML =
      kpi('Events', s.total_events, '#38e1ff') + kpi('Revenue at risk', money(s.total_revenue_at_risk), '#ff3d71') +
      kpi('Avg delay', `${s.avg_delay_days}d`, '#ffc845') + kpi('Units hit', num(s.total_units_affected), '#7c6cff');

    const regions = Object.entries(s.by_region).map(([k, v], i) => ({ label: k.replace(/-/g, ' '), value: v, color: REGION_COLORS[i % REGION_COLORS.length] }));
    bars3d?.dispose();
    bars3d = createBars3D($('#bars3d'), regions, { format: money });

    const total = s.total_events || 1;
    $('#typeBars').innerHTML = Object.entries(s.by_disruption_type).map(([k, v]) => `
      <div class="hbar"><span>${esc(titleCase(k))}</span><div class="track"><i style="width:${(v / total * 100).toFixed(1)}%;--c:${TYPE_COLORS[k] || '#8898b8'}"></i></div><span class="n">${v}</span></div>`).join('');

    $('#trend').innerHTML = trendSvg(s.by_month || {});
    $('#worst').innerHTML = s.worst_events.map(e => `
      <li><div class="grow"><div class="t">${esc(e.supplier_name)}</div><div class="s">${esc(e.date)} · ${esc(titleCase(e.disruption_type))} · ${esc(e.event_id)}</div></div>
      <div style="text-align:right"><div class="t">${money(e.revenue_at_risk_usd)}</div>${riskPill(e.label)}</div></li>`).join('');

    const hist = await histP;
    if (hist.length) {
      const ok = hist.filter(r => r.correct).length, acc = ok / hist.length * 100;
      const by = l => hist.filter(r => r.actual === l);
      $('#accuracy').innerHTML = `<div class="ring-stat">${ring(acc, '#2fe39a', 96, 'Accuracy')}
        <div><div class="big">${ok}/${hist.length}</div><div class="muted small">historical events classified correctly</div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">${['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(l => {
          const g = by(l); return g.length ? pill(`${l} ${Math.round(g.filter(r => r.correct).length / g.length * 100)}%`, RISK_COLORS[l]) : '';
        }).join('')}</div></div></div>
        <p class="muted small" style="margin-top:10px">Evaluated on the full dataset, including training rows, so this overstates real-world accuracy.</p>`;
    } else $('#accuracy').innerHTML = '<p class="empty">Model not trained yet.</p>';
  } catch (err) {
    $('#aKpis').innerHTML = `<p class="empty">Analytics unavailable: ${esc(err.message)}</p>`;
  }
}

// ── Intelligence ────────────────────────────────────────────────────────────
async function loadIntel() {
  try {
    const news = await api('/news');
    $('#news').innerHTML = news.map(n => {
      const url = /^https?:\/\//.test(n.url || '') ? n.url : null;
      const tag = url ? 'a' : 'div';
      return `<${tag} class="item" ${url ? `href="${esc(url)}" target="_blank" rel="noopener noreferrer"` : ''} style="--c:${RISK_COLORS[n.severity_hint] || '#8898b8'}">
        <div style="display:flex;justify-content:space-between;gap:10px"><strong>${esc(n.headline)}</strong>${riskPill(n.severity_hint)}</div>
        <div class="meta"><span>${esc(n.source)}</span><span>${esc(titleCase(n.category))}</span><span>${esc(n.region)}</span>
        <span>${esc(new Date(n.published_at).toLocaleString())}</span></div></${tag}>`;
    }).join('') || '<p class="empty">No news available.</p>';
  } catch (err) { $('#news').innerHTML = `<p class="empty">Feed unavailable: ${esc(err.message)}</p>`; }
}

$('#analyzeForm').addEventListener('submit', async e => {
  e.preventDefault();
  const text = $('#analyzeText').value.trim(); if (!text) return;
  const btn = $('button', e.target); btn.classList.add('loading'); btn.disabled = true;
  try {
    const r = await api(`/analyze?text=${encodeURIComponent(text)}`);
    const p = r.prediction;
    $('#analyzeOut').innerHTML = `<div class="result">
      <div class="head">${riskPill(p.label)} <span>${Math.round(p.confidence * 100)}% confidence</span>
        ${pill(titleCase(p.disruption_type), '#38e1ff')} ${pill(`~${p.estimated_duration_days} days`, '#7c6cff')}</div>
      <div class="muted small" style="margin-bottom:8px">Regions: ${esc(p.affected_regions.join(', '))}</div>
      ${planHtml(r.plan)}
      ${r.plan.supplier_alternatives?.length ? `<h4 class="muted small" style="text-transform:uppercase;letter-spacing:.08em">Alternate suppliers</h4>
        <div class="chips">${r.plan.supplier_alternatives.map(a => pill(`${a.name} · ${a.country}`, '#2fe39a')).join('')}</div>` : ''}
    </div>`;
  } catch (err) { $('#analyzeOut').innerHTML = `<p class="empty">Analysis failed: ${esc(err.message)}</p>`; }
  finally { btn.classList.remove('loading'); btn.disabled = false; }
});

// ── System ──────────────────────────────────────────────────────────────────
async function loadSystem() {
  const h = await loadHealth();
  if (h) {
    const m = h.system_metrics || {};
    const g = (label, v, c) => `<div class="gauge">${ring(v ?? 0, c, 84, label)}<div class="l">${esc(label)}</div></div>`;
    const color = v => v > 85 ? '#ff3d71' : v > 65 ? '#ffc845' : '#2fe39a';
    $('#gauges').innerHTML =
      g('CPU', m.cpu_percent, color(m.cpu_percent)) + g('Memory', m.memory_percent, color(m.memory_percent)) +
      g('Disk', m.disk_percent, color(m.disk_percent)) +
      `<div class="gauge"><div style="font-size:26px;font-weight:700;margin:22px 0 18px">${(h.uptime_seconds / 60).toFixed(1)}m</div><div class="l">Uptime</div></div>`;
    $('#artefacts').innerHTML =
      Object.entries(h.artefacts).map(([k, ok]) => pill(`${ok ? '✓' : '✕'} ${k}`, ok ? '#2fe39a' : '#ff3d71')).join('') +
      Object.entries(h.channels || {}).map(([k, ok]) => pill(`${k.replace('_', ' ')}: ${ok ? 'on' : 'off'}`, ok ? '#38e1ff' : '#8898b8')).join('');
  } else {
    $('#gauges').innerHTML = '<p class="empty">API offline.</p>';
  }
  try {
    const alerts = await api('/alerts');
    const lc = { EMERGENCY: '#ff3d71', CRITICAL: '#ff3d71', WARNING: '#ffc845', INFO: '#38e1ff' };
    $('#alerts').innerHTML = alerts.slice(0, 12).map(a => `
      <li><div class="grow"><div class="t" style="white-space:pre-line">${esc(a.message.split('\n').slice(0, 3).join('\n'))}</div>
      <div class="s">${esc(new Date(a.timestamp + (a.timestamp.endsWith('Z') ? '' : 'Z')).toLocaleString())} · via ${esc(a.channel)}</div></div>${pill(a.level, lc[a.level] || '#8898b8')}</li>`).join('')
      || '<li class="empty">No alerts logged yet.</li>';
  } catch { $('#alerts').innerHTML = '<li class="empty">Alerts unavailable.</li>'; }
}
$('#refreshSys').addEventListener('click', loadSystem);
$('#alertForm').addEventListener('submit', async e => {
  e.preventDefault();
  const message = $('#alertMsg').value.trim(); if (!message) return;
  try {
    await api('/alerts/send', { method: 'POST', body: JSON.stringify({ level: $('#alertLevel').value, message }) });
    $('#alertMsg').value = ''; toast('Broadcast queued');
    setTimeout(loadSystem, 600);
  } catch (err) { toast(`Broadcast failed: ${err.message}`); }
});

// ── Boot ────────────────────────────────────────────────────────────────────
(async function boot() {
  await loadHealth();
  await loadCommand();
  state.loaded.command = true;
  const initial = location.hash.slice(1);
  if (initial && loaders[initial]) show(initial); else document.body.dataset.view = 'command';
  await Promise.race([globe.landReady, new Promise(r => setTimeout(r, 4000))]);
  $('#loader').classList.add('done');
  setTimeout(() => $('#loader').remove(), 700);
  setInterval(loadHealth, 30000);
})();

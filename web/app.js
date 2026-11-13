import { createGlobe, RISK_COLORS, STATUS_COLORS } from './globe.js';
import { createBars3D } from './bars3d.js';

// Same-origin by default. Old local UI ports are forwarded to the current API
// so a previously opened tab cannot post the new per-shipment payload to an
// older backend that only accepts the legacy single-mode request.
const requestedApi = new URLSearchParams(location.search).get('api');
const API = requestedApi || (['8001', '8002', '8003'].includes(location.port) ? 'http://localhost:8004' : '');

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
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || body.error || body.message || JSON.stringify(body);
      if (Array.isArray(detail)) detail = detail.map(x => x.msg || JSON.stringify(x)).join('; ');
    } catch { /* Keep the HTTP status text when the response isn't JSON. */ }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json();
}

function toast(msg, ms = 2800) {
  const t = $('#toast'); t.textContent = msg; t.classList.remove('hidden');
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.add('hidden'), ms);
}

const state = { network: null, shipments: [], scan: null, responseHistory: [], selectedDetail: null, sort: { key: 'estimated_arrival', asc: true }, loaded: {} };

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
  state.selectedDetail = ud;
  if (!ud) { box.innerHTML = '<h3>Selection</h3><p class="muted">Click a shipment, hub or event on the globe to inspect it.</p>'; return; }
  const d = ud.data;
  if (ud.kind === 'shipment') {
    const risk = state.scan?.find(r => r.shipment.id === d.id);
    const responseEvents = state.responseHistory
      .filter(r => r.shipment_id === d.id)
      .map(r => ({
        date: r.timestamp,
        event: `Automated response · ${titleCase(r.cause)}`,
        detail: `${titleCase(r.mode)} → ${titleCase(r.horizon)} · ${(r.actions || []).slice(0, 2).join(' · ')}`,
        source: 'Response log',
      }));
    const receiver = d.receiver || {};
    const supplierContacts = (d.supplier_contacts || []).map(c => `
      <li><div class="grow"><div class="t">${esc(c.contact_name)} · ${esc(c.role || 'Supplier contact')}</div>
        <div class="s">${esc(c.email)}${c.phone ? ` · ${esc(c.phone)}` : ''}</div></div>${pill(c.verified ? 'VERIFIED' : 'DEMO / UNVERIFIED', c.verified ? '#2fe39a' : '#ffc845')}</li>`).join('') || '<li class="empty">No supplier contact saved.</li>';
    const trackingEvents = (d.tracking_events || []).map(ev => ({
      date: ev.date,
      event: ev.event,
      detail: `${d.current_location || d.origin} · simulated shipment update`,
      source: 'DEMO',
    }));
    const timeline = [...trackingEvents, ...responseEvents]
      .sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 10);
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
        <dt>Tracking ref</dt><dd>${esc(d.tracking_reference || 'Not provided')}</dd>
        <dt>Tracking type</dt><dd>${esc(d.tracking_source || 'Demo simulation')}</dd>
        <dt>Tracking status</dt><dd>${esc(d.tracking_status || d.status)}</dd>
        <dt>Last location</dt><dd>${esc(d.current_location || d.origin)}</dd>
        <dt>Updated</dt><dd>${esc(d.tracking_updated_at || 'Demo snapshot')}</dd>
        <dt>ETA</dt><dd>${esc(d.estimated_arrival)}</dd>
        <dt>Units</dt><dd>${num(d.units)}</dd>
        <dt>Value</dt><dd>${money(d.value_usd)}</dd>
        ${risk ? `<dt>Predicted risk</dt><dd>${riskPill(risk.prediction.label)}</dd>` : ''}
      </dl>
      <h4 style="margin:16px 0 8px">Supplier contacts</h4>
      <ul class="list">${supplierContacts}</ul>
      <h4 style="margin:16px 0 8px">Receiving company</h4>
      <ul class="list"><li><div class="grow"><div class="t">${esc(receiver.name || d.receiver_id || 'No receiver saved')}</div>
        <div class="s">${esc([receiver.city, receiver.country].filter(Boolean).join(', '))} · ${esc(receiver.tier || 'No tier')}</div>
        <div class="s">${esc(receiver.contact_email || 'No email saved')}${receiver.contact_phone ? ` · ${esc(receiver.contact_phone)}` : ''}</div></div>${pill(receiver.contact_verified ? 'VERIFIED' : 'DEMO / UNVERIFIED', receiver.contact_verified ? '#2fe39a' : '#ffc845')}</li></ul>
      <p class="muted small">${esc(d.contact_data_note || '')}</p>
      <div class="progress"><i style="width:${Math.round((d.progress ?? 0) * 100)}%"></i></div>
      <span class="muted small">${Math.round((d.progress ?? 0) * 100)}% of voyage complete · demo estimate</span>
      <h4 style="margin:16px 0 8px">Shipment activity timeline</h4>
      <ul class="list">${timeline.map(ev => `<li><div class="grow"><strong>${esc(ev.event)}</strong><div class="muted small">${esc(ev.detail)}</div><div class="muted small">${esc(ev.date)}</div></div>${pill(ev.source, ev.source === 'DEMO' ? '#ffc845' : '#38e1ff')}</li>`).join('') || '<li class="empty">No tracking events or responses recorded.</li>'}</ul>`;
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

async function loadOutcomeSummary() {
  try {
    // Dispatch writes this ledger immediately; bypass browser caching so the
    // System view cannot keep showing an older GET response.
    const history = await api(`/actions/history?_=${Date.now()}`);
    state.responseHistory = history;
    if (state.selectedDetail?.kind === 'shipment') renderDetail(state.selectedDetail);
    const counts = { in_progress: 0, completed: 0, rejected: 0 };
    history.forEach(r => { const key = r.outcome || 'in_progress'; if (key in counts) counts[key]++; });
    const recent = history.slice(0, 3).map(r => `<li><div class="grow"><div class="t">${esc(r.shipment_id)} · ${esc(titleCase(r.cause))}</div><div class="s">${esc(titleCase(r.outcome || 'in_progress'))} · ${esc(r.notification_channel || 'not sent')}</div></div>${pill(titleCase(r.risk), r.risk === 'CRITICAL' ? '#ff3d71' : '#ff8a3d')}</li>`).join('');
    $('#outcomeSummary').innerHTML = `<div class="response-result"><strong>${counts.in_progress} in progress</strong> · ${counts.completed} completed · ${counts.rejected} rejected</div>${recent ? `<ul class="list" style="margin-top:8px">${recent}</ul>` : '<p class="muted small">No response outcomes recorded yet.</p>'}`;
  } catch { $('#outcomeSummary').innerHTML = '<p class="muted small">Response history unavailable.</p>'; }
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
    await loadOutcomeSummary();
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
      <td>${esc(s.tracking_status || 'Demo tracking')}<div class="sub">${esc(s.current_location || s.origin)} · DEMO</div></td>
      <td class="num">${money(s.value_usd)}<div class="sub">${num(s.units)} u</div></td>
      <td>${statusPill(s.status)}</td>
    </tr>`).join('') || '<tr><td colspan="7" class="empty">No shipments match.</td></tr>';
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

function responseHtml(response) {
  if (!response || !response.actions?.length) return `<div class="response-result"><strong>Monitoring only</strong><p class="muted small">${esc(response?.decision_reason || 'No response actions are needed for this risk level.')}</p></div>`;
  const carrierLine = response.carrier_execution && response.carrier_execution.status !== 'not_applicable'
    ? `<p class="muted small">Carrier action: ${esc(response.carrier_execution.message)} · ${esc(response.carrier_execution.status)}</p>` : '';
  return `<div class="response-result">
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center"><strong>Automated response</strong>${pill(titleCase(response.horizon), '#38e1ff')} ${pill(response.status, '#2fe39a')}</div>
    <p class="muted small">${esc(response.decision_reason || '')}</p>
    <ul>${response.actions.map(a => `<li>${esc(a)}</li>`).join('')}</ul>
    <p class="muted small">Supplier/client notification: ${esc(response.notification_channel || 'not needed')}</p>
    ${carrierLine}
  </div>`;
}

function shipmentPlanChoice(shipment, risk) {
  if (RANK[risk] < 2) return `<div class="response-result"><strong>Not eligible for dispatch</strong><p class="muted small">${esc(risk)} risk — only HIGH and CRITICAL shipments can be dispatched.</p></div>`;
  const name = `responseMode-${shipment.id}`;
  const options = [
    ['immediate', 'Immediate', 'Act now'],
    ['short_term', 'Short term', 'Contain near-term impact'],
    ['long_term', 'Long term', 'Reduce recurring risk'],
    ['ai', 'AI solution', 'Let the risk model decide'],
  ];
  return `<fieldset class="response-picker shipment-response"><legend>Choose a response for ${esc(shipment.id)}</legend>
    ${options.map(([value, label, help]) => `<label><input type="radio" name="${esc(name)}" value="${value}"><span><strong>${label}</strong><small>${help}</small></span></label>`).join('')}
  </fieldset>`;
}

function updateDispatchButton() {
  const pending = (state.scan || []).filter(r => RANK[r.prediction.label] >= 2 && !r.response?.actions?.length);
  const hasSelection = pending.some(r => $(`input[name="responseMode-${r.shipment.id}"]:checked`, $('#threatList')));
  $('#notifyBtn').disabled = !hasSelection;
  $('#notifyBtn').title = !pending.length ? 'No undispatched HIGH or CRITICAL shipments remain' : hasSelection ? 'Dispatch selected shipment response(s)' : 'Choose a response for at least one HIGH or CRITICAL shipment';
}

function renderThreatResults(data, automated = false) {
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
        ${(automated && (r.response?.actions?.length || RANK[l] < 2)) ? responseHtml(r.response) : planHtml(r.plan)}
        ${RANK[l] >= 2 && !(automated && r.response?.actions?.length) ? shipmentPlanChoice(s, l) : ''}
      </div>
    </details>`;
  }).join('');
  return counts;
}

async function runScan() {
  const btn = $('#scanBtn'); btn.classList.add('loading'); btn.disabled = true;
  $('#notifyBtn').disabled = true;
  $('#threatList').innerHTML = '<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>';
  try {
    const data = await api('/shipments/threats');
    const counts = renderThreatResults(data);
    const dispatchable = data.some(r => RANK[r.prediction.label] >= 2);
    updateDispatchButton();
    toast(dispatchable ? `Scan complete — ${counts.CRITICAL} critical, ${counts.HIGH} high, ${counts.MEDIUM} medium` : 'Scan complete — no response actions required');
  } catch (err) {
    $('#threatList').innerHTML = `<p class="empty">Scan failed: ${esc(err.message)}</p>`;
    state.scan = null;
  } finally { btn.classList.remove('loading'); btn.disabled = false; }
}
async function dispatchResponse() {
  if (!state.scan || $('#notifyBtn').disabled) return;
  const btn = $('#notifyBtn'); btn.classList.add('loading'); btn.disabled = true;
  try {
    const responses = {};
    state.scan.filter(r => RANK[r.prediction.label] >= 2 && !r.response?.actions?.length).forEach(r => {
      const selected = $(`input[name="responseMode-${r.shipment.id}"]:checked`, $('#threatList'));
      if (selected) responses[r.shipment.id] = selected.value;
    });
    const priorResponses = new Map(state.scan.filter(r => r.response?.actions?.length).map(r => [r.shipment.id, r.response]));
    const report = await api('/shipments/threats/respond', { method: 'POST', body: JSON.stringify({ responses }) });
    report.results.forEach(r => {
      if (!responses[r.shipment.id] && priorResponses.has(r.shipment.id)) r.response = priorResponses.get(r.shipment.id);
    });
    renderThreatResults(report.results, true);
    toast(`Individual responses complete — ${report.summary.responded} plans recorded, ${report.summary.notifications_sent} notifications sent`);
    await loadSystem();
    loadOutcomeSummary();
  } catch (err) { toast(`Dispatch failed: ${err.message}`); }
  finally { btn.classList.remove('loading'); updateDispatchButton(); }
}
$('#scanBtn').addEventListener('click', runScan);
$('#notifyBtn').addEventListener('click', dispatchResponse);
$('#threatList').addEventListener('change', updateDispatchButton);
$('#threatList').addEventListener('click', e => {
  const b = e.target.closest('[data-fly]'); if (!b) return;
  e.preventDefault(); globe.focusShipment(b.dataset.fly);
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
    const externalEventsP = api('/analytics/external-disruptions').catch(() => null);
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

    const externalEvents = await externalEventsP;
    if (externalEvents) {
      $('#externalEventKpis').innerHTML =
        kpi('Measured impact records', num(externalEvents.record_count), '#38e1ff') +
        kpi('Distinct disruption events', num(externalEvents.unique_event_count), '#ff3d71') +
        kpi('Cause types', num(externalEvents.event_type_count), '#ffc845') +
        kpi('Evidence period', `${esc(externalEvents.date_from || '—')}–${esc(externalEvents.date_to || '—')}`, '#7c6cff');

      const renderEventBars = (entries, color) => {
        const values = Object.entries(entries || {});
        const max = Math.max(1, ...values.map(([, value]) => value));
        return values.map(([name, value]) => `<div class="hbar"><span>${esc(titleCase(name.replace(/-/g, ' ').replace(/^portwatch /i, '')))}</span><div class="track"><i style="width:${(value / max * 100).toFixed(1)}%;--c:${color}"></i></div><span class="n">${num(value)}</span></div>`).join('');
      };
      $('#externalEventTypes').innerHTML = renderEventBars(externalEvents.by_event_type, '#38e1ff');
      $('#externalEventSources').innerHTML = renderEventBars(externalEvents.by_measurement_series, '#7c6cff');
      $('#externalEventTop').innerHTML = (externalEvents.largest_declines || []).map(e =>
        `<li><div class="grow"><div class="t">${esc(e.event_title)} · ${esc(titleCase(e.event_type.replace(/-/g, ' ')))}</div><div class="s">${esc(e.event_date)} · ${esc(e.affected_entity)} · ${esc(e.measurement_unit)}</div><div class="s">${num(e.change_pct)}% activity change · ${esc(e.confidence)} confidence</div></div><a class="btn" href="${esc((e.source_references || e.source_event_url).split(';')[0])}" target="_blank" rel="noopener">Source</a></li>`).join('') || '<li class="empty">No measured disruption impacts.</li>';
    } else {
      $('#externalEventKpis').innerHTML = '<p class="empty">Measured disruption data unavailable.</p>';
    }
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
      Object.entries(h.channels || {}).filter(([k]) => k !== 'carrier_mode').map(([k, ok]) => pill(`${k.replace('_', ' ')}: ${ok ? 'on' : 'off'}`, ok ? '#38e1ff' : '#8898b8')).join('');
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
  try {
    const history = await api(`/actions/history?_=${Date.now()}`);
    $('#responseHistory').innerHTML = history.map(r => `
      <li><div class="grow"><div class="t">${esc(r.shipment_id)} · ${esc(r.risk)} · ${esc(titleCase(r.cause))}</div>
      <div class="s">${esc(titleCase(r.mode))} → ${esc(titleCase(r.horizon))} · ${esc(new Date(r.timestamp).toLocaleString())}</div>
      <div class="s">${esc((r.actions || []).slice(0, 2).join(' · '))} · notify: ${esc(r.notification_channel)}</div>
      <div class="s">Carrier: ${esc(r.carrier_execution?.message || 'No reroute action')}</div>
      ${r.response_id ? `<div class="outcome-edit"><select data-outcome="${esc(r.response_id)}" aria-label="Update response outcome">
        <option value="in_progress" ${(r.outcome || 'in_progress') === 'in_progress' ? 'selected' : ''}>In progress</option>
        <option value="completed" ${r.outcome === 'completed' ? 'selected' : ''}>Completed</option>
        <option value="rejected" ${r.outcome === 'rejected' ? 'selected' : ''}>Rejected</option>
      </select><input type="text" data-outcome-note="${esc(r.response_id)}" maxlength="500" placeholder="Outcome note (optional)" value="${esc(r.outcome_note || '')}">
      <button class="btn" data-save-outcome="${esc(r.response_id)}">Save</button></div>` : ''}</div>${pill(titleCase(r.outcome || r.status), r.outcome === 'completed' ? '#2fe39a' : r.outcome === 'rejected' ? '#ff3d71' : '#ffc845')}</li>`).join('')
      || '<li class="empty">No automated responses recorded yet.</li>';
    const latest = history[0]?.timestamp;
    $('#responseHistoryUpdated').textContent = latest
      ? `Updated ${new Date(latest).toLocaleTimeString()}`
      : 'No responses yet';
  } catch {
    $('#responseHistory').innerHTML = '<li class="empty">Response history unavailable.</li>';
    $('#responseHistoryUpdated').textContent = 'Could not refresh';
  }
  const guidance = [];
  if (!h?.channels?.email && !h?.channels?.slack) guidance.push('Alerts are saved to the local log only. Configure SMTP_USER + SMTP_PASSWORD or SLACK_WEBHOOK_URL in .env to deliver them.');
  if (!h?.channels?.carrier) guidance.push('Carrier reroutes are recommendations only. Configure CARRIER_WEBHOOK_URL (and optional CARRIER_API_TOKEN) to request and confirm reroutes.');
  if (h?.channels?.carrier && h?.channels?.carrier_mode === 'demo') guidance.push('Mock carrier is active for demonstration only; it confirms a safer route from the local demo route list and contacts no real carrier.');
  else if (h?.channels?.carrier) guidance.push('Carrier webhook is configured; route changes are recorded only after the carrier returns a confirmed response.');
  if (!guidance.length) guidance.push('Email/Slack delivery is configured.');
  $('#integrationGuidance').innerHTML = guidance.map(x => `<p>${esc(x)}</p>`).join('');
}
$('#refreshSys').addEventListener('click', loadSystem);
setInterval(() => {
  if (document.body.dataset.view === 'system') loadSystem();
}, 10000);
$('#responseHistory').addEventListener('click', async e => {
  const button = e.target.closest('[data-save-outcome]'); if (!button) return;
  const responseId = button.dataset.saveOutcome;
  const select = $(`[data-outcome="${responseId}"]`, $('#responseHistory'));
  const note = $(`[data-outcome-note="${responseId}"]`, $('#responseHistory'));
  button.disabled = true;
  try {
    await api(`/actions/history/${encodeURIComponent(responseId)}`, { method: 'PATCH', body: JSON.stringify({ outcome: select.value, note: note.value }) });
    toast('Response outcome saved'); await loadSystem(); await loadOutcomeSummary();
  } catch (err) { toast(`Outcome update failed: ${err.message}`); }
  finally { button.disabled = false; }
});
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

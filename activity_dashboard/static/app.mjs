/* Daymark: framework-free rendering, calendar math, and local API integration. */
export const TIMEZONE = 'Asia/Ho_Chi_Minh';
export const DEFAULT_CATEGORIES = [
  { id: 'coding', label: 'Coding', color: '#236353' },
  { id: 'github', label: 'GitHub', color: '#4c6f55' },
  { id: 'chatgpt', label: 'ChatGPT', color: '#6b9a74' },
  { id: 'orca', label: 'Orca', color: '#a87946' },
  { id: 'reading', label: 'Reading', color: '#a8af72' },
  { id: 'other', label: 'Other', color: '#869891' },
];
const DAY_MS = 86400000;
const dateFormatter = new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', day: 'numeric', month: 'long' });
const timeFormatter = new Intl.DateTimeFormat('en-GB', { timeZone: TIMEZONE, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const e = escapeHTML;
const color = value => /^#[a-f\d]{3,8}$/i.test(value || '') ? value : '#236353';
const dateObject = day => new Date(`${day}T00:00:00Z`);
export const addDays = (day, count) => new Date(dateObject(day).getTime() + count * DAY_MS).toISOString().slice(0, 10);
export function todayInZone(now = new Date()) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TIMEZONE, year: 'numeric', month: '2-digit', day: '2-digit' }).format(now);
}
export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return '—';
  if (seconds <= 0) return '0m';
  if (seconds < 60) return '<1m';
  const minutes = Math.floor(seconds / 60);
  return minutes < 60 ? `${minutes}m` : `${Math.floor(minutes / 60)}h${minutes % 60 ? ` ${minutes % 60}m` : ''}`;
}
function largeDuration(seconds) {
  return e(formatDuration(seconds)).replace(/(h|m)/g, '<small>$1</small>');
}
export function filteredSeconds(day, selectedCategories) {
  if (!day || day.totalSeconds == null || day.status === 'missing' || day.status === 'future') return null;
  return [...selectedCategories].reduce((sum, category) => sum + Math.max(0, Number(day.categories?.[category]) || 0), 0);
}
export function periodBounds(selectedDate, period) {
  const parsed = dateObject(selectedDate);
  const year = selectedDate.slice(0, 4);
  if (period === 'day') return [selectedDate, selectedDate];
  if (period === 'week') {
    const monday = addDays(selectedDate, -((parsed.getUTCDay() + 6) % 7));
    return [monday, addDays(monday, 6)];
  }
  if (period === 'month') return [`${selectedDate.slice(0, 7)}-01`, new Date(Date.UTC(parsed.getUTCFullYear(), parsed.getUTCMonth() + 1, 0)).toISOString().slice(0, 10)];
  return [`${year}-01-01`, `${year}-12-31`];
}
export function periodSummary(days, selectedDate, period, selectedCategories, today) {
  const [start, end] = periodBounds(selectedDate, period);
  const byDate = new Map(days.map(day => [day.date, day]));
  let totalSeconds = 0, observedDays = 0, expectedDays = 0, incomplete = false;
  for (let day = start; day <= end; day = addDays(day, 1)) {
    if (day > today) continue;
    expectedDays++;
    const record = byDate.get(day);
    const seconds = filteredSeconds(record, selectedCategories);
    if (seconds == null) { incomplete = true; continue; }
    observedDays++;
    totalSeconds += seconds;
    if (record.status !== 'complete') incomplete = true;
  }
  return { totalSeconds: observedDays ? totalSeconds : null, observedDays, expectedDays, incomplete, start, end };
}
export function heatLevel(seconds) {
  if (seconds == null) return 'missing';
  if (seconds === 0) return 'level-0';
  if (seconds < 3600) return 'level-1';
  if (seconds < 10800) return 'level-2';
  if (seconds < 21600) return 'level-3';
  return 'level-4';
}
export function dayDescription(day, selectedCategories) {
  if (!day || day.status === 'missing' || day.totalSeconds == null && day.status !== 'future') return 'No data — activity is unknown';
  if (day.status === 'future') return 'Future day';
  return `${formatDuration(filteredSeconds(day, selectedCategories))} observed activity${day.status === 'partial' ? ' · partial coverage' : ' · complete coverage'}`;
}
export function renderHeatmap(data, selectedCategories) {
  const year = data.year;
  const first = `${year}-01-01`, last = `${year}-12-31`;
  const offset = (dateObject(first).getUTCDay() + 6) % 7;
  const count = Math.round((dateObject(last) - dateObject(first)) / DAY_MS) + 1;
  const weeks = Math.ceil((offset + count) / 7);
  const days = new Map(data.days.map(day => [day.date, day]));
  const labels = ['Mon', '', 'Wed', '', 'Fri', '', 'Sun'];
  const monthLabels = Array.from({ length: 12 }, (_, index) => {
    const date = new Date(Date.UTC(Number(year), index, 1));
    const col = Math.floor((offset + Math.round((date - dateObject(first)) / DAY_MS)) / 7) + 1;
    return `<span style="grid-column:${col}">${date.toLocaleDateString('en-GB', { timeZone: 'UTC', month: 'short' })}</span>`;
  }).join('');
  const cells = Array.from({ length: weeks * 7 }, (_, index) => {
    if (index < offset || index >= count + offset) return '<span class="heat-cell pad" aria-hidden="true"></span>';
    const day = addDays(first, index - offset);
    const record = days.get(day) || { date: day, status: day > data.today ? 'future' : 'missing', totalSeconds: null };
    const desc = `${day}: ${dayDescription(record, selectedCategories)}`;
    const selected = day === data.selectedDate;
    const state = record.status === 'future' ? 'future' : `${heatLevel(filteredSeconds(record, selectedCategories))} ${record.status === 'partial' ? 'partial' : ''}`;
    return `<button type="button" class="heat-cell ${state}${selected ? ' selected' : ''}" data-date="${day}" title="${e(desc)}" aria-label="${e(desc)}" aria-pressed="${selected}"${record.status === 'future' ? ' disabled' : ''}></button>`;
  }).join('');
  return `<div class="heatmap-labels" aria-hidden="true"><span></span>${labels.map(label => `<span>${label}</span>`).join('')}</div><div class="heatmap-body" style="--weeks:${weeks}"><div class="heatmap-months" aria-hidden="true">${monthLabels}</div><div class="heatmap-days" role="group" aria-label="Daily activity for ${year}">${cells}</div></div>`;
}
export function renderSummary(data, selectedCategories) {
  const names = { day: 'Selected day', week: 'This week', month: 'This month', year: 'This year' };
  const days = [...data.days, ...(data.weekDays || [])];
  return Object.entries(names).map(([period, name]) => {
    const summary = periodSummary(days, data.selectedDate, period, selectedCategories, data.today);
    let note;
    if (!summary.expectedDays) note = 'Future period · no activity yet';
    else if (!summary.observedDays) note = 'No data · activity unknown';
    else if (period === 'day') note = summary.incomplete ? 'Observed time · partial coverage' : 'Observed time · complete coverage';
    else note = `Observed · ${summary.observedDays}/${summary.expectedDays} days with data`;
    const dateNote = period === 'day' ? dateFormatter.format(dateObject(data.selectedDate)) : period === 'week' ? `${dateFormatter.format(dateObject(summary.start))} – ${dateFormatter.format(dateObject(summary.end))}` : period === 'month' ? dateObject(data.selectedDate).toLocaleDateString('en-GB', { month: 'long', year: 'numeric', timeZone: 'UTC' }) : String(data.year);
    return `<article class="summary-card"><h3 class="summary-label">${name}</h3><p class="summary-value">${largeDuration(summary.totalSeconds)}</p><p class="summary-note">${e(note)}<br>${e(dateNote)}</p></article>`;
  }).join('');
}
const emptySymbol = '<span class="empty-symbol" aria-hidden="true">' + '<i></i>'.repeat(9) + '</span>';
export function renderEmptyState(kind) {
  const states = {
    missing: ['This day is still a blank page.', 'No verified activity data is available. Start ActivityWatch and check the collectors below. Unknown time is never counted as zero.'],
    future: ['A day yet to come.', 'Future days stay empty. Your journal fills in as activity is observed.'],
    zero: ['A quiet observed day.', 'No active foreground time was recorded in the observed intervals. Gaps outside those intervals remain unknown.'],
    filtered: ['Nothing in this selection.', 'There is no observed activity in the selected categories. Choose another category to explore this day.'],
  };
  const [title, message] = states[kind] || states.missing;
  return `<div class="empty-state" data-empty-state="${kind}">${emptySymbol}<h3>${title}</h3><p>${message}</p></div>`;
}
function wallSeconds(iso) {
  const value = new Date(iso);
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone: TIMEZONE, hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).formatToParts(value);
  const read = type => Number(parts.find(part => part.type === type)?.value || 0);
  return read('hour') * 3600 + read('minute') * 60 + read('second');
}
export function renderDayDetails(data, selectedCategories) {
  const day = data.selected || data.days.find(record => record.date === data.selectedDate) || { date: data.selectedDate, status: 'missing', totalSeconds: null, categories: {} };
  const categories = data.categories || DEFAULT_CATEGORIES;
  const total = filteredSeconds(day, selectedCategories);
  const hasData = total !== null;
  const statuses = { partial: 'Partial coverage', complete: 'Complete coverage', missing: 'No data', future: 'Future day' };
  const note = !hasData ? day.status === 'future' ? 'Activity will appear after this day begins.' : 'Activity is unknown. No zero has been assumed.' : day.status === 'partial' ? 'Observed active time only. Unrecorded parts of the day remain unknown.' : 'Active foreground time in the selected categories. Idle time is excluded.';
  const categoryRows = categories.map(category => {
    const seconds = hasData ? Number(day.categories?.[category.id]) || 0 : null;
    const included = selectedCategories.has(category.id);
    const width = included && total > 0 ? Math.min(100, seconds / total * 100) : 0;
    return `<div class="category-row${included ? '' : ' excluded'}" style="--category-color:${color(category.color)}"><span class="category-dot"></span><span>${e(category.label)}${included ? '' : ' · hidden'}</span><span class="category-duration">${e(formatDuration(seconds))}</span><div class="category-bar"><span style="width:${width}%"></span></div></div>`;
  }).join('');
  const coverage = `<dl class="coverage-row"><div><dt>Observed coverage</dt><dd>${e(formatDuration(day.observedSeconds ?? null))}</dd></div><div><dt>Idle excluded</dt><dd>${e(formatDuration(hasData ? day.idleSeconds ?? 0 : null))}</dd></div><div><dt>Unknown time</dt><dd>${e(formatDuration(day.status === 'future' ? null : day.unknownSeconds ?? null))}</dd></div></dl>`;
  const segments = (day.segments || []).filter(segment => selectedCategories.has(segment.category));
  const lookup = Object.fromEntries(categories.map(category => [category.id, category]));
  const timeline = segments.map(segment => {
    const offset = wallSeconds(segment.start) / 864;
    const width = Math.min(100 - offset, segment.seconds / 864);
    return `<span class="track-segment" style="left:${offset}%;width:${width}%;--category-color:${color(lookup[segment.category]?.color)}" title="${e(lookup[segment.category]?.label || segment.category)}: ${e(timeFormatter.format(new Date(segment.start)))}–${e(timeFormatter.format(new Date(segment.end)))}"></span>`;
  }).join('');
  const log = segments.map(segment => `<li><span class="log-time">${e(timeFormatter.format(new Date(segment.start)))} – ${e(timeFormatter.format(new Date(segment.end)))}</span><span class="log-category" style="--category-color:${color(lookup[segment.category]?.color)}"><i class="category-dot" aria-hidden="true"></i>${e(lookup[segment.category]?.label || segment.category)}</span><span class="log-duration">${e(formatDuration(segment.seconds))}</span></li>`).join('');
  const emptyKind = day.status === 'future' ? 'future' : !hasData ? 'missing' : day.totalSeconds === 0 ? 'zero' : 'filtered';
  const timelineContent = segments.length ? `<div class="day-track" role="img" aria-label="Active intervals across the selected day, from midnight to midnight">${timeline}</div><div class="track-hours" aria-hidden="true"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>24:00</span></div><div class="log-heading"><span>ACTIVE INTERVALS</span><span>${segments.length} interval${segments.length === 1 ? '' : 's'}</span></div><ol class="activity-log">${log}</ol>` : renderEmptyState(emptyKind);
  return `<div class="day-layout"><article class="panel day-panel"><div class="day-panel-title"><h3>Time by category</h3><span class="coverage-badge ${e(day.status)}">${statuses[day.status] || 'No data'}</span></div><p class="day-total">${largeDuration(total)}</p><p class="day-subtitle">${note}</p>${categoryRows}${coverage}</article><article class="panel day-panel"><div class="day-panel-title"><h3>The shape of your day</h3><span class="coverage-badge">UTC+7</span></div><p class="timeline-intro">One foreground activity at a time. Overlapping collectors never add extra time.</p>${timelineContent}</article></div>`;
}
export function renderCollectionStatus(status = {}) {
  const labels = { window: 'Foreground window', afk: 'Idle detection', browser: 'Browser detail', editor: 'Editor detail' };
  const watchers = status.watchers || [];
  const safeStatus = value => ['connected', 'available', 'ready', 'active', 'recent', 'missing', 'unavailable', 'unsupported', 'unconfigured', 'error', 'stale', 'demo'].includes(value) ? value : 'unconfigured';
  const rows = watchers.length ? watchers.map(watcher => `<div class="collector-row"><span>${e(labels[watcher.kind] || watcher.kind)}</span><span class="collector-state ${safeStatus(watcher.status)}">${e(watcher.status)}</span><p>${e(watcher.message || '')}</p></div>`).join('') : status.backend === 'demo' ? '<div class="collector-row"><span>Synthetic collectors</span><span class="collector-state demo">Demo</span><p>Invented window, browser, and idle events demonstrate the interface. These are not live collectors or your activity.</p></div>' : '<div class="collector-row"><span>ActivityWatch collectors</span><span class="collector-state unavailable">Not connected</span><p>Window and idle collectors are needed to verify active foreground time. Browser detail is needed to identify websites reliably.</p></div>';
  const orca = status.orcaBackground || { status: 'unsupported', message: 'No reliable background run source is configured. Orca foreground time is a separate category.' };
  return `${rows}<div class="collector-row orca-row"><span>Orca background runs</span><span class="collector-state unsupported">${e(orca.status || 'unsupported')}</span><p>${e(orca.message)} Background runtime is never added to human foreground time.</p></div>${status.warnings?.length ? `<ul class="warnings">${status.warnings.map(warning => `<li>${e(warning)}</li>`).join('')}</ul>` : ''}`;
}

// Keep pure functions importable in Node without a browser or third-party test runtime.
if (typeof document !== 'undefined') initializeDashboard();
function initializeDashboard() {
  const byId = id => document.getElementById(id);
  const today = todayInZone();
  const state = { source: 'live', year: Number(today.slice(0, 4)), date: today, device: '', selectedCategories: new Set(DEFAULT_CATEGORIES.map(category => category.id)), data: null, request: 0, controller: null };
  byId('year').value = String(state.year);
  byId('selected-date').value = state.date;
  byId('source').value = 'live';

  function renderFilters() {
    const categories = state.data?.categories || DEFAULT_CATEGORIES;
    byId('filters').innerHTML = categories.map(category => `<label class="filter-chip" style="--category-color:${color(category.color)}"><input type="checkbox" value="${e(category.id)}"${state.selectedCategories.has(category.id) ? ' checked' : ''}><span class="category-dot" aria-hidden="true"></span>${e(category.label)}<span class="filter-check" aria-hidden="true">✓</span></label>`).join('');
  }
  function renderViews() {
    const data = state.data;
    if (!data) return;
    byId('summary').innerHTML = renderSummary(data, state.selectedCategories);
    byId('heatmap').innerHTML = renderHeatmap(data, state.selectedCategories);
    byId('day-details').innerHTML = renderDayDetails(data, state.selectedCategories);
    byId('year-title').textContent = `${data.year}, one day at a time`;
    byId('day-title').textContent = dateObject(data.selectedDate).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' });
    byId('selected-date').value = data.selectedDate;
    byId('next-day').disabled = data.selectedDate >= data.today;
    byId('year').value = String(data.year);
  }
  function renderStatus() {
    const data = state.data, status = data.status || {};
    const backend = status.backend || 'unavailable';
    const names = { connected: 'ActivityWatch is connected', unavailable: 'ActivityWatch is not running', unconfigured: 'Collection needs setup', error: 'Could not read activity', demo: 'Previewing synthetic activity' };
    const banner = byId('connection-banner');
    banner.className = `connection-banner ${['unavailable', 'error', 'unconfigured'].includes(backend) ? 'unavailable' : ''}`;
    banner.innerHTML = `<span class="status-dot"></span><div><strong>${names[backend] || 'ActivityWatch status'}</strong><p>${e(status.message || 'Data stays on this Mac.')}</p></div>`;
    byId('demo-banner').hidden = data.source !== 'demo';
    byId('collection-status').innerHTML = renderCollectionStatus(status);
    const devices = status.devices || [];
    byId('device').innerHTML = devices.length ? `${status.selectedDevice ? '' : '<option value="" selected disabled>Choose a device</option>'}${devices.map(device => `<option value="${e(device.id)}"${device.id === status.selectedDevice ? ' selected' : ''}>${e(device.label)}</option>`).join('')}` : '<option value="">No device data available</option>';
    byId('device').disabled = !devices.length;
    state.device = status.selectedDevice || '';
  }
  function emptyData(message) {
    const first = `${state.year}-01-01`, last = `${state.year}-12-31`, days = [];
    for (let day = first; day <= last; day = addDays(day, 1)) days.push({ date: day, status: day > today ? 'future' : 'missing', totalSeconds: null, categories: {} });
    return { year: state.year, selectedDate: state.date, today, days, categories: DEFAULT_CATEGORIES, source: state.source, status: { backend: 'error', message, watchers: [], devices: [] } };
  }
  async function load() {
    const request = ++state.request;
    state.controller?.abort();
    state.controller = new AbortController();
    state.data = null;
    byId('refresh').disabled = true;
    byId('announcement').textContent = 'Loading local activity…';
    byId('main').setAttribute('aria-busy', 'true');
    // A change of source/device must never leave another source's numbers visible.
    byId('summary').innerHTML = '<div class="skeleton-card">Loading activity…</div>';
    byId('heatmap').innerHTML = '';
    byId('day-details').innerHTML = '';
    byId('connection-banner').className = 'connection-banner';
    byId('connection-banner').innerHTML = '<span class="status-dot"></span><div><strong>Loading selected source</strong><p>Reading the local dashboard…</p></div>';
    byId('collection-status').innerHTML = '<p class="muted">Checking collector status…</p>';
    byId('demo-banner').hidden = state.source !== 'demo';
    const query = new URLSearchParams({ year: String(state.year), date: state.date, source: state.source });
    if (state.device) query.set('device', state.device);
    try {
      const response = await fetch(`/api/dashboard?${query}`, { signal: state.controller.signal, cache: 'no-store' });
      if (!response.ok) throw new Error(`The local dashboard returned HTTP ${response.status}. Check its terminal and try Refresh.`);
      const data = await response.json();
      if (!Array.isArray(data.days) || !Array.isArray(data.categories)) throw new Error('The local dashboard returned an unexpected response. Check its terminal.');
      if (request !== state.request) return;
      state.data = data;
      state.date = data.selectedDate;
      state.year = Number(data.year);
    } catch (error) {
      if (error.name === 'AbortError' || request !== state.request) return;
      state.data = emptyData(error.message || 'Could not reach the local dashboard. Start server.py and refresh.');
    } finally {
      if (request === state.request) {
        renderFilters(); renderStatus(); renderViews();
        byId('refresh').disabled = false;
        byId('main').removeAttribute('aria-busy');
        byId('announcement').textContent = `${state.source === 'demo' ? 'Synthetic demo' : 'Local activity'} updated. ${dayDescription(state.data.selected || state.data.days.find(day => day.date === state.date), state.selectedCategories)}.`;
      }
    }
  }
  function selectDate(date) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return;
    const year = Number(date.slice(0, 4));
    if (year < 2000 || year > 2100) return;
    state.date = date; state.year = year; load();
  }
  byId('source').addEventListener('change', event => { state.source = event.target.value; state.device = ''; load(); });
  byId('device').addEventListener('change', event => { state.device = event.target.value; load(); });
  byId('year').addEventListener('change', event => {
    const year = Number(event.target.value);
    if (!Number.isInteger(year) || year < 2000 || year > 2100) { event.target.value = state.year; return; }
    selectDate(year === Number(today.slice(0, 4)) ? today : `${year}-01-01`);
  });
  byId('refresh').addEventListener('click', load);
  byId('filters').addEventListener('change', event => {
    if (event.target.type !== 'checkbox') return;
    if (event.target.checked) state.selectedCategories.add(event.target.value);
    else state.selectedCategories.delete(event.target.value);
    renderViews();
    byId('announcement').textContent = 'Category filter updated.';
  });
  byId('select-all').addEventListener('click', () => { state.selectedCategories = new Set((state.data?.categories || DEFAULT_CATEGORIES).map(category => category.id)); renderFilters(); renderViews(); });
  byId('heatmap').addEventListener('click', event => { const cell = event.target.closest('[data-date]'); if (cell) selectDate(cell.dataset.date); });
  byId('selected-date').addEventListener('change', event => selectDate(event.target.value));
  byId('previous-day').addEventListener('click', () => selectDate(addDays(state.date, -1)));
  byId('next-day').addEventListener('click', () => selectDate(addDays(state.date, 1)));
  byId('today').addEventListener('click', () => selectDate(todayInZone()));
  renderFilters();
  load();
}

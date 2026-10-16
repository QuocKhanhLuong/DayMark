import test from 'node:test';
import assert from 'node:assert/strict';
import { TIMEZONE, DEFAULT_CATEGORIES, todayInZone, addDays, periodBounds, periodSummary, filteredSeconds, renderSummary, renderDayDetails, renderHeatmap, renderCollectionStatus, dayDescription, formatDuration, escapeHTML } from '../activity_dashboard/static/app.mjs';

const selected = new Set(DEFAULT_CATEGORIES.map(category => category.id));
const day = (date, totalSeconds, status = 'partial', categories = { coding: totalSeconds }) => ({ date, totalSeconds, status, categories, observedSeconds: totalSeconds, idleSeconds: 0, unknownSeconds: 86400 - (totalSeconds || 0), segments: [] });
const data = (record, extras = {}) => ({ year: Number(record.date.slice(0, 4)), today: '2026-10-16', selectedDate: record.date, selected: record, days: [record], categories: DEFAULT_CATEGORIES, ...extras });

test('unknown durations remain unknown; observed zero is explicit', () => {
  assert.equal(formatDuration(null), '—');
  assert.equal(formatDuration(undefined), '—');
  assert.equal(formatDuration(0), '0m');
  assert.equal(formatDuration(59), '<1m');
  assert.equal(formatDuration(3660), '1h 1m');
});

test('daily boundaries use Vietnam time independently of browser timezone', () => {
  assert.equal(TIMEZONE, 'Asia/Ho_Chi_Minh');
  assert.equal(todayInZone(new Date('2026-10-15T16:59:59Z')), '2026-10-15');
  assert.equal(todayInZone(new Date('2026-10-15T17:00:00Z')), '2026-10-16');
  assert.equal(addDays('2024-02-28', 1), '2024-02-29');
  assert.deepEqual(periodBounds('2026-01-01', 'week'), ['2025-12-29', '2026-01-04']);
});

test('cross-year weekly totals include supplied weekDays without double counting', () => {
  const days = [day('2025-12-29', 600), day('2026-01-01', 1200), day('2026-01-01', 1200)];
  const summary = periodSummary(days, '2026-01-01', 'week', selected, '2026-01-01');
  assert.equal(summary.totalSeconds, 1800);
  assert.equal(summary.observedDays, 2);
  assert.equal(summary.expectedDays, 4);
  assert.equal(summary.incomplete, true);
  const html = renderSummary(data(day('2026-01-01', 1200), { today: '2026-01-01', weekDays: [day('2025-12-29', 600)] }), selected);
  assert.match(html, /30<small>m<\/small>/);
});

test('filters never turn missing or future data into observed zero', () => {
  assert.equal(filteredSeconds(day('2026-10-16', null, 'missing'), selected), null);
  assert.equal(filteredSeconds(day('2026-10-17', null, 'future'), new Set()), null);
  assert.equal(filteredSeconds(day('2026-10-16', 600), new Set(['github'])), 0);
});

test('no-data rendering contains unknown text and no fabricated category zeroes', () => {
  const fixture = data(day('2026-10-16', null, 'missing'));
  const detail = renderDayDetails(fixture, selected);
  assert.match(detail, /data-empty-state="missing"/);
  assert.match(detail, /Activity is unknown/);
  assert.doesNotMatch(detail, />0m</);
  assert.doesNotMatch(detail, /<small>0/);
  assert.match(renderSummary(fixture, selected), /No data · activity unknown/);
  assert.doesNotMatch(renderSummary(fixture, selected), /0<small>[hm]/);
  assert.match(renderHeatmap(fixture, selected), /2026-10-16: No data — activity is unknown/);
});

test('observed idle-only day shows zero active and separate idle duration', () => {
  const record = { ...day('2026-10-16', 0), observedSeconds: 1200, idleSeconds: 1200 };
  const html = renderDayDetails(data(record), selected);
  assert.match(html, /data-empty-state="zero"/);
  assert.match(html, /0<small>m<\/small>/);
  assert.match(html, /Idle excluded<\/dt><dd>20m/);
  assert.match(html, /Partial coverage/);
});

test('heatmap labels distinguish future, zero, partial and missing', () => {
  const fixture = data(day('2026-10-16', 0), { days: [day('2026-10-15', null, 'missing'), day('2026-10-16', 0), day('2026-10-17', null, 'future')] });
  const html = renderHeatmap(fixture, selected);
  assert.match(html, /2026-10-15: No data/);
  assert.match(html, /2026-10-16: 0m observed activity · partial coverage/);
  assert.match(html, /2026-10-17: Future day/);
  assert.equal((html.match(/data-date=/g) || []).length, 365);
  assert.equal((renderHeatmap({ ...fixture, year: 2024 }, selected).match(/data-date=/g) || []).length, 366);
});

test('future detail is not shown as missing or as zero time', () => {
  const html = renderDayDetails(data(day('2026-10-17', null, 'future')), selected);
  assert.match(html, /data-empty-state="future"/);
  assert.doesNotMatch(html, />0m</);
  assert.equal(dayDescription(day('2026-10-17', null, 'future'), selected), 'Future day');
});

test('browser data strings are escaped and Orca background is separate', () => {
  const html = renderCollectionStatus({ watchers: [{ kind: '<script>', status: '" onclick="x', message: '<img src=x>' }], orcaBackground: { status: 'unsupported', message: 'No source' } });
  assert.doesNotMatch(html, /<script>|<img/);
  assert.match(html, /Orca background runs/);
  assert.match(html, /Background runtime is never added to human foreground time/);
  assert.equal(escapeHTML('<img>'), '&lt;img&gt;');
});

test('timeline includes only filtered foreground intervals and uses UTC+7 labels', () => {
  const record = { ...day('2026-10-16', 1200, 'partial', { coding: 600, reading: 600 }), segments: [{ start: '2026-10-16T01:00:00Z', end: '2026-10-16T01:10:00Z', category: 'coding', seconds: 600 }, { start: '2026-10-16T02:00:00Z', end: '2026-10-16T02:10:00Z', category: 'reading', seconds: 600 }] };
  const html = renderDayDetails(data(record), new Set(['coding']));
  assert.match(html, /08:00 – 08:10/);
  assert.doesNotMatch(html, /09:00 – 09:10/);
  assert.match(html, /1 interval</);
});

test('switching demo to live cannot restore synthetic totals while a request is pending', async () => {
  const previousDocument = globalThis.document;
  const previousFetch = globalThis.fetch;
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, { innerHTML: '', value: '', hidden: false, disabled: false, handlers: {}, addEventListener(type, handler) { this.handlers[type] = handler; }, setAttribute() {}, removeAttribute() {} });
    return elements.get(id);
  };
  const pending = [];
  const flush = () => new Promise(resolve => setImmediate(resolve));
  globalThis.document = { getElementById: element };
  globalThis.fetch = () => new Promise(resolve => pending.push(payload => resolve({ ok: true, json: async () => payload })));
  try {
    await import('../activity_dashboard/static/app.mjs?interaction-regression');
    pending.shift()(data(day('2026-10-16', null, 'missing'), { source: 'live', status: { backend: 'connected', devices: [{ id: 'first', label: 'First Mac' }, { id: 'second', label: 'Second Mac' }], selectedDevice: null } }));
    await flush();
    assert.match(element('device').innerHTML, /value="" selected disabled>Choose a device/);
    element('source').handlers.change({ target: { value: 'demo' } });
    pending.shift()(data(day('2026-10-16', 7200), { source: 'demo', status: { backend: 'demo' } }));
    await flush();
    assert.match(element('summary').innerHTML, /2<small>h/);
    assert.equal(element('demo-banner').hidden, false);
    element('source').handlers.change({ target: { value: 'live' } });
    element('filters').handlers.change({ target: { type: 'checkbox', value: 'coding', checked: false } });
    element('select-all').handlers.click();
    assert.equal(element('demo-banner').hidden, true);
    assert.match(element('summary').innerHTML, /Loading activity/);
    assert.doesNotMatch(element('summary').innerHTML, /2<small>h/);
    assert.equal(element('heatmap').innerHTML, '');
    pending.shift()(data(day('2026-10-16', null, 'missing'), { source: 'live', status: { backend: 'unavailable' } }));
    await flush();
    assert.match(element('summary').innerHTML, /No data · activity unknown/);
    assert.doesNotMatch(element('summary').innerHTML, /2<small>h/);
  } finally {
    if (previousDocument === undefined) delete globalThis.document;
    else globalThis.document = previousDocument;
    globalThis.fetch = previousFetch;
  }
});

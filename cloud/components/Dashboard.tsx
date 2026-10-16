"use client";

import { useRef, useState, type CSSProperties, type KeyboardEvent } from "react";
import {
  CATEGORIES, CATEGORY_LABELS, daysOfYear, formatDuration, periodSummary, totalSeconds,
  type DashboardData, type Day,
} from "../lib/model";
import SignOut from "./SignOut";

type Category = (typeof CATEGORIES)[number];
type Summary = ReturnType<typeof periodSummary>;
const COLORS: Record<Category, string> = {
  coding: "#28634e", github: "#758b42", chatgpt: "#478d8c",
  orca: "#82709c", reading: "#b47b45", other: "#8c9389",
};
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "numeric", month: "long", year: "numeric", timeZone: "UTC",
});
const syncFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  hour12: false, timeZone: "Asia/Ho_Chi_Minh",
});

function calendarDate(value: string) { return new Date(`${value}T12:00:00Z`); }
function shiftDate(value: string, amount: number) {
  const date = calendarDate(value);
  date.setUTCDate(date.getUTCDate() + amount);
  return date.toISOString().slice(0, 10);
}
function prettyDate(value: string) { return dateFormatter.format(calendarDate(value)); }
function syncTime(value: string | null | undefined) {
  return value ? `${syncFormatter.format(new Date(value))} · UTC+7` : "Not synced yet";
}
function duration(value: number | null) { return value === null ? "No data" : formatDuration(value); }
function missingDay(date: string): Day { return { date, status: "missing", seconds: null }; }
function initialDate(data: DashboardData) {
  return Number(data.today.slice(0, 4)) === data.year ? data.today : `${data.year}-12-31`;
}
function level(value: number | null) {
  return value === null ? "missing" : `level-${value === 0 ? 0 : value < 3600 ? 1 : value < 10800 ? 2 : value < 21600 ? 3 : 4}`;
}
function summaryNote(summary: Summary) {
  if (!summary.knownDays) return "No observed days in this period";
  return `${summary.knownDays} observed · ${summary.missingDays} missing · ${summary.partialDays} partial`;
}

function SummaryCard({ label, value, note }: { label: string; value: number | null; note: string }) {
  return <article className="summary-card">
    <p className="summary-label">{label}</p>
    <p className={`summary-value${value === null ? " no-value" : ""}`}>{duration(value)}</p>
    <p className="summary-note">{note}</p>
  </article>;
}

export default function Dashboard({ initial }: { initial: DashboardData }) {
  const [data, setData] = useState(initial);
  const [selected, setSelected] = useState(() => initialDate(initial));
  const [categories, setCategories] = useState<Category[]>(() => [...CATEGORIES]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [announcement, setAnnouncement] = useState("");
  const requestId = useRef(0);
  const cellRefs = useRef(new Map<string, HTMLButtonElement>());
  const byDate = new Map(data.days.map(day => [day.date, day]));
  const yearDates = daysOfYear(data.year);
  const offset = (calendarDate(yearDates[0]).getUTCDay() + 6) % 7;
  const weeks = Math.ceil((offset + yearDates.length) / 7);
  const cellDates = Array.from({ length: weeks * 7 }, (_, i) => yearDates[i - offset] ?? null);
  const selectedDay = byDate.get(selected) ?? missingDay(selected);
  const selectedTotal = totalSeconds(selectedDay, categories);
  const allDayTotal = totalSeconds(selectedDay, [...CATEGORIES]);
  const weekFrom = shiftDate(selected, -((calendarDate(selected).getUTCDay() + 6) % 7));
  const weekTo = shiftDate(weekFrom, 6);
  const monthFrom = `${selected.slice(0, 7)}-01`;
  const monthEnd = new Date(Date.UTC(Number(selected.slice(0, 4)), Number(selected.slice(5, 7)), 0, 12)).toISOString().slice(0, 10);
  const clipToday = (value: string) => value > data.today ? data.today : value;
  const week = periodSummary(data.days, weekFrom, clipToday(weekTo), categories);
  const month = periodSummary(data.days, monthFrom, clipToday(monthEnd), categories);
  const year = periodSummary(data.days, `${data.year}-01-01`, clipToday(`${data.year}-12-31`), categories);
  const currentYear = Number(data.today.slice(0, 4));
  const yearOptions = Array.from({ length: Math.max(currentYear, data.year) - 1999 }, (_, i) => Math.max(currentYear, data.year) - i);
  const allSelected = categories.length === CATEGORIES.length;
  const noneSelected = categories.length === 0;
  const hasYearData = year.knownDays > 0;
  const isMissing = selectedDay.status === "missing" || selectedDay.seconds === null;

  async function loadYear(yearNumber: number, nextSelected?: string) {
    const id = ++requestId.current;
    setLoading(true);
    setError("");
    setAnnouncement(`Loading ${yearNumber}…`);
    try {
      const response = await fetch(`/api/days?year=${yearNumber}`, {
        credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" }, signal: AbortSignal.timeout(20_000),
      });
      if (response.status === 401 || response.status === 403) {
        throw new Error("Your session is no longer available. Sign in again to view your activity.");
      }
      if (!response.ok) throw new Error("Could not refresh your activity. Your previous view is still shown.");
      const next: DashboardData = await response.json();
      if (next.schemaVersion !== 1 || next.timeZone !== "Asia/Ho_Chi_Minh" || next.year !== yearNumber || !Array.isArray(next.days)) {
        throw new Error("The activity response could not be read. Your previous view is still shown.");
      }
      if (id !== requestId.current) return;
      setData(next);
      setSelected(nextSelected ?? (yearNumber === data.year ? selected : initialDate(next)));
      setAnnouncement(`${yearNumber} activity refreshed. Last sync: ${syncTime(next.lastSyncAt)}.`);
    } catch (cause) {
      if (id !== requestId.current) return;
      setError(cause instanceof Error ? cause.message : "Could not refresh your activity.");
      setAnnouncement("");
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }

  function chooseDate(date: string) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || date < "2000-01-01" || date > data.today) return;
    const yearNumber = Number(date.slice(0, 4));
    if (yearNumber !== data.year) { void loadYear(yearNumber, date); return; }
    setSelected(date);
  }

  function toggleCategory(category: Category) {
    setCategories(previous => previous.includes(category) ? previous.filter(item => item !== category) : [...previous, category]);
  }

  function navigateHeatmap(event: KeyboardEvent<HTMLButtonElement>, date: string) {
    const movement: Record<string, number> = { ArrowUp: -1, ArrowDown: 1, ArrowLeft: -7, ArrowRight: 7 };
    if (!(event.key in movement)) return;
    event.preventDefault();
    const target = shiftDate(date, movement[event.key]);
    if (target < yearDates[0] || target > yearDates[yearDates.length - 1] || target > data.today) return;
    setSelected(target);
    cellRefs.current.get(target)?.focus();
  }

  return <div className="page-shell">
    <a className="skip-link" href="#main">Skip to activity</a>
    <header className="topbar">
      <a className="brand" href="/" aria-label="Daymark home"><span className="brand-mark" aria-hidden="true"><i /><i /><i /><i /></span>daymark<span className="brand-caption">ACTIVITY JOURNAL</span></a>
      <div className="header-actions"><span className="private-badge"><span className="lock-icon" aria-hidden="true" />Private dashboard</span><SignOut /></div>
    </header>
    <main id="main">
      <section className="intro" aria-labelledby="page-title">
        <div><p className="eyebrow">A RECORD OF YOUR EVERYDAY</p><h1 id="page-title">Small steps.<br /><em>A bigger picture.</em></h1><p className="intro-description">Your coding, conversations, and reading — one day at a time.</p></div>
        <div className="intro-note"><span className="note-line" /><p>Focus time, thoughtfully counted.</p><span>Foreground activity · idle excluded<br />Asia/Ho_Chi_Minh · UTC+7</span></div>
      </section>

      <section className="sync-panel" aria-labelledby="sync-title">
        <div className="sync-copy"><span className={`status-dot${data.lastSyncAt ? "" : " waiting"}`} aria-hidden="true" /><div><h2 id="sync-title">{data.lastSyncAt ? "Daily totals received" : "Ready for your first sync"}</h2><p>{data.lastSyncAt ? <>Last received <time dateTime={data.lastSyncAt}>{syncTime(data.lastSyncAt)}</time></> : "No activity has been uploaded yet. Start collection and sync from your Mac."}</p></div></div>
        <button className="refresh-button" type="button" disabled={loading} onClick={() => void loadYear(data.year)}><span aria-hidden="true">↻</span>{loading ? "Refreshing…" : "Refresh"}</button>
      </section>
      {error ? <div className="error-banner" role="alert">{error}<a href="/">Reload dashboard</a></div> : null}
      <div className="sr-only" role="status" aria-live="polite">{announcement}</div>

      <section className="category-filter" aria-labelledby="filter-title">
        <div className="filter-heading"><h2 id="filter-title">What counts in your view</h2><button className="text-button" type="button" onClick={() => setCategories(allSelected ? [] : [...CATEGORIES])}>{allSelected ? "Clear selection" : "Select all"}</button></div>
        <div className="filter-options">{CATEGORIES.map(category => <button key={category} className={`filter-chip${categories.includes(category) ? " is-selected" : ""}`} type="button" aria-pressed={categories.includes(category)} onClick={() => toggleCategory(category)}><span className="category-dot" style={{ "--category-color": COLORS[category] } as CSSProperties} aria-hidden="true" />{CATEGORY_LABELS[category]}<span className="filter-check" aria-hidden="true">✓</span></button>)}</div>
        {noneSelected ? <p className="filter-note" role="status">No categories selected. Select a category to show its time; missing days remain unknown.</p> : null}
      </section>

      <section className="summary-grid" aria-label="Observed activity totals" aria-busy={loading}>
        <SummaryCard label="Selected day" value={selectedTotal} note={`${prettyDate(selected)}${isMissing ? " · No data" : selectedDay.status === "partial" ? " · Partial coverage" : " · Complete coverage"}`} />
        <SummaryCard label="Selected week" value={week.seconds} note={summaryNote(week)} />
        <SummaryCard label="Selected month" value={month.seconds} note={summaryNote(month)} />
        <SummaryCard label={`${data.year} so far`} value={year.seconds} note={summaryNote(year)} />
      </section>

      <section className="panel year-panel" aria-labelledby="year-title" aria-busy={loading}>
        <div className="panel-heading"><div><p className="eyebrow">THE LONG VIEW</p><h2 id="year-title">Your year in focus</h2></div><div className="year-control"><label htmlFor="year-select">Year</label><select id="year-select" value={data.year} disabled={loading} onChange={event => void loadYear(Number(event.target.value))}>{yearOptions.map(value => <option key={value} value={value}>{value}</option>)}</select></div></div>
        {!hasYearData ? <div className="year-empty"><strong>A blank page is a beginning.</strong><span>No activity has been synced for {data.year}. Hatched squares mean unknown time, not zero.</span></div> : null}
        <div className="heatmap-scroll" role="group" aria-label={`${data.year} daily activity. Use arrow keys to move between days.`}>
          <div className="heatmap" style={{ "--weeks": weeks } as CSSProperties}>
            <div className="heatmap-labels" aria-hidden="true"><span /><span>Mon</span><span /><span>Wed</span><span /><span>Fri</span><span /><span /></div>
            <div className="heatmap-body"><div className="heatmap-months" aria-hidden="true">{MONTHS.map((name, monthIndex) => { const first = `${data.year}-${String(monthIndex + 1).padStart(2, "0")}-01`; const column = Math.floor((offset + yearDates.indexOf(first)) / 7) + 1; return <span key={name} style={{ gridColumn: column }}>{name}</span>; })}</div>
              <div className="heatmap-days">{cellDates.map((date, index) => {
                if (!date) return <span key={`pad-${index}`} className="heat-cell pad" aria-hidden="true" />;
                const day = byDate.get(date) ?? missingDay(date);
                const value = totalSeconds(day, categories);
                const future = date > data.today;
                const partial = day.status === "partial" && value !== null;
                const label = `${prettyDate(date)}: ${future ? "future day" : `${duration(value)}${partial ? ", partial coverage" : ""}${value !== null && noneSelected ? ", no categories selected" : ""}`}`;
                return <button key={date} type="button" className={`heat-cell ${future ? "future" : level(value)}${partial ? " partial" : ""}${selected === date ? " selected" : ""}`} title={label} aria-label={label} aria-pressed={selected === date} disabled={future || loading} tabIndex={selected === date ? 0 : -1} ref={node => { if (node) cellRefs.current.set(date, node); else cellRefs.current.delete(date); }} onClick={() => chooseDate(date)} onKeyDown={event => navigateHeatmap(event, date)} />;
              })}</div>
            </div>
          </div>
        </div>
        <div className="heatmap-footer"><p>Every square is a day. Select one for a closer look.</p><div className="legend" aria-label="Heatmap legend"><span><i className="swatch missing" />No data</span><span><i className="swatch future" />Future</span><span><i className="swatch level-0" />0</span><span className="scale" title="Under 1 hour, 1–3 hours, 3–6 hours, 6 hours or more"><i className="swatch level-1" /><i className="swatch level-2" /><i className="swatch level-3" /><i className="swatch level-4" /></span><span>6h+</span><span><i className="swatch level-2 partial" />Partial</span></div></div>
      </section>

      <section className="day-section" aria-labelledby="day-title">
        <div className="day-heading"><div><p className="eyebrow">A CLOSER LOOK</p><h2 id="day-title">{prettyDate(selected)}</h2></div><div className="date-controls"><button type="button" aria-label="Previous day" disabled={loading || selected === "2000-01-01"} onClick={() => chooseDate(shiftDate(selected, -1))}>←</button><label className="sr-only" htmlFor="selected-date">Selected day</label><input id="selected-date" type="date" min="2000-01-01" max={data.today} value={selected} disabled={loading} onChange={event => chooseDate(event.target.value)} /><button type="button" aria-label="Next day" disabled={loading || selected >= data.today} onClick={() => chooseDate(shiftDate(selected, 1))}>→</button><button className="today-button" type="button" disabled={loading || selected === data.today} onClick={() => chooseDate(data.today)}>Today</button></div></div>
        <div className="day-layout">
          <article className="panel day-panel"><div className="day-panel-title"><h3>Time by category</h3><span className={`coverage-badge ${isMissing ? "missing-badge" : selectedDay.status}`}>{isMissing ? "No data" : selectedDay.status === "partial" ? "Partial coverage" : "Complete coverage"}</span></div><p className={`day-total${selectedTotal === null ? " no-value" : ""}`}>{duration(selectedTotal)}</p><p className="day-subtitle">{isMissing ? "No reliable activity total is available for this day." : noneSelected ? "Choose categories above to include their time." : "Observed foreground time in your selected categories."}</p>
            {isMissing ? <div className="empty-state"><span className="empty-symbol" aria-hidden="true">{Array.from({ length: 9 }, (_, i) => <i key={i} />)}</span><h3>This day is still a blank.</h3><p>Collection may have been off, or this day has not been synced. It does not mean you spent zero time.</p></div> : <div className="category-breakdown">{CATEGORIES.map(category => { const seconds = selectedDay.seconds?.[category] ?? 0; const included = categories.includes(category); const width = allDayTotal ? (seconds / allDayTotal) * 100 : 0; return <div key={category} className={`category-row${included ? "" : " excluded"}`} style={{ "--category-color": COLORS[category] } as CSSProperties}><span className="category-dot" aria-hidden="true" /><span>{CATEGORY_LABELS[category]}{included ? "" : <span className="excluded-note"> · excluded</span>}</span><span className="category-duration">{duration(seconds)}</span><div className="category-bar" aria-hidden="true"><span style={{ width: `${width}%` }} /></div></div>; })}</div>}
          </article>
          <article className="panel context-panel"><p className="eyebrow">PUTTING THE DAY IN CONTEXT</p><h3>Count the time. Keep the gaps.</h3><p className="context-intro">Totals include observed activity. Unrecorded time is never filled in, and partial days can grow after the next sync.</p><dl className="context-list"><div><dt>Week · Monday–Sunday</dt><dd>{prettyDate(weekFrom)} – {prettyDate(weekTo)}</dd><dd className="context-total">{duration(week.seconds)}</dd></div><div><dt>Month · {MONTHS[Number(selected.slice(5, 7)) - 1]} {selected.slice(0, 4)}</dt><dd>{summaryNote(month)}</dd><dd className="context-total">{duration(month.seconds)}</dd></div><div><dt>This day last synced</dt><dd>{selectedDay.syncedAt ? syncTime(selectedDay.syncedAt) : isMissing ? "Not available" : "Per-day sync time unavailable"}</dd></div></dl><div className="privacy-note"><span className="lock-icon" aria-hidden="true" /><p>Only daily category totals leave your Mac. Window titles, URLs, and detailed activity stay local.</p></div></article>
        </div>
      </section>

      <section className="collection-note" aria-labelledby="counting-title"><div><p className="eyebrow">BEHIND THE NUMBERS</p><h2 id="counting-title">Your time, counted once.</h2></div><div><p>ActivityWatch records on your Mac. Daymark excludes idle time and resolves overlapping watchers before syncing daily totals.</p><p>Orca here means human foreground time. Background run duration is not available.</p></div></section>
      <footer><span>daymark<span className="footer-dot">·</span>A private record of your everyday.</span><span>Day boundaries: Asia/Ho_Chi_Minh · UTC+7</span></footer>
    </main>
  </div>;
}

export { Dashboard };

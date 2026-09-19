/**
 * Deterministic extraction of chartable series from agent message text.
 *
 * Upstream hands the model tool output as prose and the model echoes it back,
 * so the only source is text. Everything here is pure parsing: no model calls,
 * no network, no cost. The hard rule is that a chart is drawn only when the
 * data was read completely — a partially parsed series is refused, because a
 * plausible-looking chart built from half the rows is worse than no chart.
 *
 * Measured on a real run (`~/.tradingagents/runs/ed41b5d9/events.jsonl`), the
 * two shapes that appear are an OHLCV CSV block and `date: value` indicator
 * dumps where non-trading days read `N/A: Not a trading day (weekend or holiday)`.
 */

export interface OhlcBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface LinePoint {
  time: string;
  /** Absent means "no reading that day"; the line is drawn with a gap, never bridged. */
  value?: number;
}

export interface IndicatorSeries {
  label: string;
  points: LinePoint[];
  valueCount: number;
}

export interface ParsedChartData {
  bars: OhlcBar[];
  indicators: IndicatorSeries[];
}

/** Minimum rows before a CSV block is considered a chart instead of a stray table. */
const MIN_BARS = 10;
/** Minimum numeric readings before an indicator block is worth drawing. */
const MIN_POINTS = 8;

const DATE = String.raw`\d{4}-\d{2}-\d{2}`;
const OHLC_HEADER = /^\s*Date\s*,\s*Open\s*,\s*High\s*,\s*Low\s*,\s*Close\b/i;
const BAR_ROW = new RegExp(
  String.raw`^(${DATE})\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,`,
);
// The label usually arrives as a markdown heading (`## close_200_sma values
// from ...`), so allow the markers a model might wrap it in. Missing this
// prefix is why the indicator dumps initially parsed as nothing at all.
const SERIES_HEADER = new RegExp(
  String.raw`^\s*(?:[#>*_-]+\s*)?([A-Za-z][A-Za-z0-9_]*)\s+values from\s+(${DATE})\s+to\s+(${DATE})\s*:?`,
);
const SERIES_POINT = new RegExp(String.raw`(${DATE})\s*:\s*([-\d.]+)`);
const SERIES_GAP = new RegExp(String.raw`(${DATE})\s*:\s*N/?A`, 'i');

/**
 * Markdown tables are the other shape upstream produces (a "verified snapshot"
 * message carries three of them). Only tables with a date column are series;
 * the snapshot tables of single readings have no date column and are skipped,
 * because a chart of one point means nothing.
 */
const TABLE_ROW = /^\s*\|(.+)\|\s*$/;
const TABLE_SEPARATOR = /^\s*\|[\s:|-]+\|\s*$/;
const MARKDOWN_HEADING = /^\s*#{1,6}\s+(.+?)\s*$/;
const OHLC_COLUMNS = ['open', 'high', 'low', 'close'];
/** Column names that say nothing about what is being plotted. */
const GENERIC_COLUMNS = new Set(['value', 'close', 'price', 'adj close', 'adjusted close']);
const MAX_LABEL = 54;

function seriesLabel(heading: string | null, column: string): string {
  // "| Date | Value |" under "## FRED: Consumer Price Index ..." is a CPI chart
  // labelled "Value" without this. Prefer the heading when the column name is
  // generic; a real column name (close_200_sma, rsi) is already specific.
  const preferred = heading && GENERIC_COLUMNS.has(column.trim().toLowerCase()) ? heading : column;
  const cleaned = preferred
    .replace(/^#{1,6}\s*/, '')
    // "… (last 30 rows)" plus the point count reads as "(last 30 rows) (30)".
    .replace(/\s*\(last\s+\d+\s+rows?\)\s*$/i, '')
    .trim();
  return cleaned.length > MAX_LABEL ? `${cleaned.slice(0, MAX_LABEL - 1)}…` : cleaned;
}

/** True when a line still looks like part of the CSV block, valid or not. */
function looksLikeBarRow(line: string): boolean {
  return new RegExp(String.raw`^\s*${DATE}\s*,`).test(line);
}

function parseBars(lines: string[]): OhlcBar[] {
  for (let i = 0; i < lines.length; i += 1) {
    if (!OHLC_HEADER.test(lines[i])) continue;

    const bars: OhlcBar[] = [];
    let sawBadRow = false;

    for (let j = i + 1; j < lines.length; j += 1) {
      const line = lines[j];
      const match = BAR_ROW.exec(line);
      if (!match) {
        // A row-shaped line that failed to parse means the block is malformed,
        // not finished. Refuse rather than chart a truncated series.
        if (looksLikeBarRow(line)) sawBadRow = true;
        break;
      }
      const [, time, open, high, low, close] = match;
      const values = [open, high, low, close].map(Number);
      if (values.some((v) => !Number.isFinite(v))) {
        sawBadRow = true;
        break;
      }
      bars.push({ time, open: values[0], high: values[1], low: values[2], close: values[3] });
    }

    if (sawBadRow) return [];
    if (bars.length >= MIN_BARS) {
      // Ascending, de-duplicated: the chart library requires it and a repeated
      // day is a data fault worth collapsing rather than passing through.
      const byTime = new Map(bars.map((bar) => [bar.time, bar]));
      return [...byTime.values()].sort((a, b) => a.time.localeCompare(b.time));
    }
  }
  return [];
}

function parseIndicators(lines: string[]): IndicatorSeries[] {
  const series: IndicatorSeries[] = [];

  for (let i = 0; i < lines.length; i += 1) {
    const header = SERIES_HEADER.exec(lines[i]);
    if (!header) continue;

    const label = header[1];
    const points: LinePoint[] = [];
    let valueCount = 0;

    // The values continue on the header line itself, then on following lines.
    // Points and gaps are matched in separate passes rather than as one
    // alternation: combined, the capture-group indices shift between the two
    // branches and gap dates were being read as `undefined`.
    const candidates = [lines[i].slice(header[0].length), ...lines.slice(i + 1)];

    for (const candidate of candidates) {
      const values = [...candidate.matchAll(new RegExp(SERIES_POINT.source, 'g'))];
      const gaps = [...candidate.matchAll(new RegExp(SERIES_GAP.source, 'g'))];
      if (values.length === 0 && gaps.length === 0) {
        if (points.length > 0) break;
        continue;
      }
      for (const [, date, raw] of values) {
        const value = Number(raw);
        if (!Number.isFinite(value)) continue;
        valueCount += 1;
        points.push({ time: date, value });
      }
      for (const [, date] of gaps) {
        points.push({ time: date });
      }
    }

    if (valueCount >= MIN_POINTS) {
      const byTime = new Map(points.map((point) => [point.time, point]));
      series.push({
        label,
        valueCount,
        points: [...byTime.values()].sort((a, b) => a.time.localeCompare(b.time)),
      });
    }
  }

  // Two lines is already a crowded story; keep the most complete ones.
  return series.sort((a, b) => b.valueCount - a.valueCount).slice(0, 3);
}

function splitTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim());
}

interface TableParse {
  bars: OhlcBar[];
  indicators: IndicatorSeries[];
}

function parseMarkdownTables(lines: string[]): TableParse {
  const result: TableParse = { bars: [], indicators: [] };
  let heading: string | null = null;

  for (let i = 0; i < lines.length - 1; i += 1) {
    const foundHeading = MARKDOWN_HEADING.exec(lines[i]);
    if (foundHeading) heading = foundHeading[1];
    if (!TABLE_ROW.test(lines[i]) || !TABLE_SEPARATOR.test(lines[i + 1])) continue;

    const header = splitTableRow(lines[i]);
    const dateIndex = header.findIndex((cell) => /^date$/i.test(cell));
    // No date column -> a table of single readings, not a series.
    if (dateIndex < 0) continue;

    const rows: string[][] = [];
    let malformed = false;
    for (let j = i + 2; j < lines.length; j += 1) {
      if (!TABLE_ROW.test(lines[j])) break;
      const cells = splitTableRow(lines[j]);
      if (!new RegExp(`^${DATE}$`).test(cells[dateIndex] ?? '')) {
        // Table-shaped but the date is unreadable: refuse the whole table
        // rather than publish a series with a hole the reader cannot see.
        malformed = true;
        break;
      }
      rows.push(cells);
    }
    if (malformed || rows.length < MIN_BARS) continue;

    const numericColumns = header
      .map((cell, index) => ({ cell: cell.toLowerCase(), index }))
      .filter(
        ({ index }) =>
          index !== dateIndex &&
          rows.every((cells) => Number.isFinite(Number(cells[index])) && (cells[index] ?? '') !== ''),
      );
    if (numericColumns.length === 0) continue;

    const columnFor = (name: string) => numericColumns.find((column) => column.cell === name);
    const ohlcColumns = OHLC_COLUMNS.map(columnFor);

    if (ohlcColumns.every(Boolean)) {
      const [open, high, low, close] = ohlcColumns.map((column) => column!.index);
      const bars = rows.map((cells) => ({
        time: cells[dateIndex],
        open: Number(cells[open]),
        high: Number(cells[high]),
        low: Number(cells[low]),
        close: Number(cells[close]),
      }));
      const byTime = new Map(bars.map((bar) => [bar.time, bar]));
      result.bars = [...byTime.values()].sort((a, b) => a.time.localeCompare(b.time));
      continue;
    }

    // A plain `Date | Close` table is a line series.
    for (const column of numericColumns.slice(0, 2)) {
      // Dedupe by date, as the CSV path does. The chart library throws on a
      // repeated time, and a throw here blanks the whole record, so a table
      // that names the same day twice must not reach it.
      const points = new Map<string, LinePoint>();
      for (const cells of rows) {
        points.set(cells[dateIndex], { time: cells[dateIndex], value: Number(cells[column.index]) });
      }
      result.indicators.push({
        label: seriesLabel(heading, header[column.index] || 'value'),
        valueCount: points.size,
        points: [...points.values()].sort((a, b) => a.time.localeCompare(b.time)),
      });
    }
  }

  return result;
}

/**
 * Extract chartable series, or `null` when the text holds nothing usable.
 *
 * Returning `null` is a real outcome, not an error: most agent messages are
 * prose with no series in them at all.
 */
export function parseChartData(text: string | undefined | null): ParsedChartData | null {
  if (!text) return null;
  const lines = text.split(/\r?\n/);
  const tables = parseMarkdownTables(lines);
  const bars = parseBars(lines);
  const indicators = [...parseIndicators(lines), ...tables.indicators].slice(0, 3);
  const finalBars = bars.length > 0 ? bars : tables.bars;
  if (finalBars.length === 0 && indicators.length === 0) return null;
  return { bars: finalBars, indicators };
}

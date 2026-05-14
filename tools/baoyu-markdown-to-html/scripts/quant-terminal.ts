import type { CliOptions } from "./vendor/baoyu-md/src/types.ts";
import { renderMarkdownDocument } from "./vendor/baoyu-md/src/index.ts";

interface QuantMeta {
  ticker: string;
  date: string;
  model: string;
  verdict: string;
  confidence?: number;
}
interface TocItem {
  id: string;
  title: string;
  level: number;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
function stripTags(value: string): string {
  return value.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
}
function slugify(value: string): string {
  const slug = stripTags(value)
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s_-]/gu, "")
    .replace(/[\s_-]+/g, "-")
    .replace(/^-|-$/g, "");
  return slug || "section";
}
function uniqueSlug(base: string, seen: Map<string, number>): string {
  const count = seen.get(base) ?? 0;
  seen.set(base, count + 1);
  return count ? `${base}-${count + 1}` : base;
}
function classifySection(title: string): string {
  const text = title.toLowerCase();
  if (/fundamental|valuation|financial|基本面|估值|财务/.test(text)) return "fundamentals";
  if (/sentiment|social|reddit|stocktwits|情绪|社交/.test(text)) return "sentiment";
  if (/news|macro|headline|新闻|宏观/.test(text)) return "news";
  if (/technical|indicator|macd|rsi|技术|指标/.test(text)) return "technical";
  if (/\bbull\b|bullish|看多|多头/.test(text)) return "bull";
  if (/\bbear\b|bearish|看空|空头/.test(text)) return "bear";
  if (/research manager|manager|synthesis|研究主管|综合/.test(text)) return "manager";
  if (/trader|trade plan|investment plan|交易员|交易计划/.test(text)) return "trader";
  if (/risk|risky|neutral|safe|conservative|aggressive|风险/.test(text)) return "risk";
  if (/portfolio|final|decision|verdict|最终|决策|结论/.test(text)) return "final";
  return "default";
}

function enhanceSections(contentHtml: string): { html: string; toc: TocItem[] } {
  const headingPattern = /<h([23])([^>]*)>([\s\S]*?)<\/h\1>/gi;
  const matches = [...contentHtml.matchAll(headingPattern)];
  const h2Matches = matches.filter((m) => m[1] === "2");

  if (!h2Matches.length) {
    return {
      html: `<section class="qt-section">${contentHtml}</section>`,
      toc: [],
    };
  }

  const seen = new Map<string, number>();
  const toc: TocItem[] = [];
  const parts: string[] = [];
  let cursor = 0;

  if ((h2Matches[0]?.index ?? 0) > 0) {
    parts.push(
      `<section class="qt-section qt-section-intro">${contentHtml.slice(0, h2Matches[0]!.index)}</section>`,
    );
    cursor = h2Matches[0]!.index!;
  }

  for (let i = 0; i < h2Matches.length; i += 1) {
    const match = h2Matches[i]!;
    const next = h2Matches[i + 1];
    const start = match.index!;
    const end = next?.index ?? contentHtml.length;
    if (start < cursor) continue;

    const attrs = match[2] ?? "";
    const inner = match[3] ?? "";
    const title = stripTags(inner);
    const id = uniqueSlug(slugify(title), seen);
    const kind = classifySection(title);
    toc.push({ id, title, level: 2 });

    const newH2 = `<h2${attrs} id="${id}">${inner}</h2>`;
    let sectionInner = contentHtml.slice(start, end).replace(match[0], newH2);

    const h3Pattern = /<h3([^>]*)>([\s\S]*?)<\/h3>/gi;
    sectionInner = sectionInner.replace(h3Pattern, (_full, h3attrs, h3inner) => {
      const h3Title = stripTags(h3inner);
      const h3Id = uniqueSlug(slugify(h3Title), seen);
      toc.push({ id: h3Id, title: h3Title, level: 3 });
      const hasId = /id\s*=/.test(h3attrs);
      const newAttrs = hasId ? h3attrs : `${h3attrs} id="${h3Id}"`;
      return `<h3${newAttrs}>${h3inner}</h3>`;
    });

    parts.push(
      `<section class="qt-section" data-kind="${kind}">${sectionInner}</section>`,
    );
    cursor = end;
  }

  return { html: parts.join("\n"), toc };
}

function firstMatch(markdown: string, patterns: RegExp[]): string {
  for (const pattern of patterns) {
    const match = markdown.match(pattern);
    if (match?.[1]) return match[1].trim();
  }
  return "";
}
function extractMeta(markdown: string, title: string, overrides?: Partial<QuantMeta>): QuantMeta {
  const ticker =
    overrides?.ticker ||
    firstMatch(markdown, [
      /(?:ticker|symbol|股票代码|代码)\s*[:：]\s*`?([A-Z][A-Z0-9.\-]{0,9})`?/i,
      /\b(?:NYSE|NASDAQ|HKEX|SSE|SZSE)\s*[:：]\s*([A-Z0-9.\-]{1,10})\b/i,
    ]) ||
    firstMatch(title, [/\b([A-Z][A-Z0-9.\-]{1,9})\b/]) ||
    "—";
  const date =
    overrides?.date ||
    firstMatch(markdown, [
      /(?:analysis date|date|分析日期|日期)\s*[:：]\s*(\d{4}-\d{2}-\d{2})/i,
      /\b(\d{4}-\d{2}-\d{2})\b/,
    ]) ||
    "—";
  const model =
    overrides?.model ||
    firstMatch(markdown, [
      /(?:model|llm|quick|deep|模型)\s*[:：]\s*`?([A-Za-z0-9_.:/\- ]{2,80})`?/i,
    ]) ||
    "—";
  const finalSection =
    markdown.match(/(?:final|portfolio|decision|verdict|最终|决策)[\s\S]{0,2500}/i)?.[0] ??
    markdown;
  const verdict =
    firstMatch(finalSection, [/\b(BUY|SELL|HOLD)\b/i]).toUpperCase() ||
    firstMatch(finalSection, [/(买入|卖出|持有)/])
      .replace(/买入/, "BUY")
      .replace(/卖出/, "SELL")
      .replace(/持有/, "HOLD") ||
    "—";
  const confidenceRaw = firstMatch(finalSection, [
    /(?:confidence|置信度|信心)\s*[:：]?\s*(\d{1,3})\s*%/i,
    /(\d{1,3})\s*%\s*(?:confidence|置信度|信心)/i,
  ]);
  const confidence = confidenceRaw
    ? Math.max(0, Math.min(100, Number(confidenceRaw)))
    : undefined;
  return { ticker, date, model, verdict, confidence };
}
function extractReasons(markdown: string): string[] {
  const finalSection =
    markdown.match(/(?:final|portfolio|decision|verdict|最终|决策)[\s\S]{0,3000}/i)?.[0] ?? "";
  if (!finalSection) return [];
  const bullets = [...finalSection.matchAll(/^\s*[-*]\s+(.{12,220})\s*$/gm)]
    .map((match) => match[1]?.trim() ?? "")
    .filter(Boolean);
  if (bullets.length) return bullets.slice(0, 3);
  const sentences = finalSection
    .replace(/[#*_`>]/g, "")
    .split(/(?<=[.!?。！？])\s+/)
    .map((sentence) => sentence.trim())
    .filter(
      (sentence) => sentence.length >= 24 && !/\b(BUY|SELL|HOLD)\b$/i.test(sentence),
    );
  return sentences.slice(0, 2);
}
function verdictClass(verdict: string): string {
  if (verdict === "BUY") return "buy";
  if (verdict === "SELL") return "sell";
  if (verdict === "HOLD") return "hold";
  return "unknown";
}
function buildToc(toc: TocItem[]): string {
  if (!toc.length) return '<p class="qt-empty">No sections.</p>';
  return toc
    .map(
      (item, i) =>
        `<a href="#${item.id}" class="qt-toc-l${item.level}" data-toc-level="${item.level}"><span class="qt-toc-num">${item.level === 2 ? String(i + 1).padStart(2, "0") : ""}</span><span class="qt-toc-text">${escapeHtml(item.title)}</span></a>`,
    )
    .join("\n");
}

function buildQuantCss(): string {
  return `
:root {
  --bg: #0A0B0F;
  --surface: #101218;
  --surface-2: #16181F;
  --border: #1F2229;
  --hairline: #1A1D24;
  --text: #E6E8EC;
  --text-2: #9BA1AD;
  --text-3: #5C6270;
  --accent: #E8E8E8;
  --bull: #00C887;
  --bear: #FF5C5C;
  --neutral: #E0A93B;
  --link: #6FA8FF;
  --scroll-track: #0A0B0F;
  --scroll-thumb: #2A2F3A;
  --scroll-thumb-hover: #3C4352;
  --sans: "Geist", "Inter", -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SF Mono", monospace;
  --ease: cubic-bezier(0.22, 1, 0.36, 1);
  --radius: 8px;
  --topbar-h: 52px;
}
[data-theme="light"] {
  --bg: #FAFAFA;
  --surface: #FFFFFF;
  --surface-2: #F5F5F7;
  --border: #E8E8EA;
  --hairline: #EFEFF2;
  --text: #18181B;
  --text-2: #52525B;
  --text-3: #A1A1AA;
  --accent: #18181B;
  --bull: #008F5D;
  --bear: #DC2626;
  --neutral: #B45309;
  --link: #2563EB;
  --scroll-track: #F4F4F5;
  --scroll-thumb: #C7CBD1;
  --scroll-thumb-hover: #A7ADB7;
}
*, *::before, *::after { box-sizing: border-box; }
html {
  scroll-behavior: smooth;
  scroll-padding-top: calc(var(--topbar-h) + 16px);
  scrollbar-color: var(--scroll-thumb) var(--scroll-track);
  scrollbar-width: thin;
}
html::-webkit-scrollbar,
body::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}
html::-webkit-scrollbar-track,
body::-webkit-scrollbar-track {
  background: var(--scroll-track);
}
html::-webkit-scrollbar-thumb,
body::-webkit-scrollbar-thumb {
  background: var(--scroll-thumb);
  border: 2px solid var(--scroll-track);
  border-radius: 999px;
}
html::-webkit-scrollbar-thumb:hover,
body::-webkit-scrollbar-thumb:hover {
  background: var(--scroll-thumb-hover);
}
html::-webkit-scrollbar-corner,
body::-webkit-scrollbar-corner {
  background: var(--scroll-track);
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.65;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "ss01", "cv11", "tnum";
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
:lang(zh), :lang(zh-CN), :lang(zh-TW) { line-height: 1.8; }

/* ============ Topbar ============ */
.qt-topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  height: var(--topbar-h);
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 0 max(16px, calc((100vw - 1440px) / 2 + 16px));
  background: color-mix(in srgb, var(--bg) 80%, transparent);
  backdrop-filter: blur(16px) saturate(1.4);
  -webkit-backdrop-filter: blur(16px) saturate(1.4);
  border-bottom: 1px solid var(--hairline);
  font-size: 13px;
  color: var(--text-2);
}
.qt-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--sans);
  font-weight: 600;
  font-size: 14px;
  color: var(--text);
  letter-spacing: -0.01em;
}
.qt-brand-mark {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  background: linear-gradient(135deg, var(--text) 0%, var(--text-2) 100%);
  flex-shrink: 0;
}
[data-theme="light"] .qt-brand-mark { background: linear-gradient(135deg, #18181B 0%, #52525B 100%); }
.qt-topbar-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-left: auto;
  font-family: var(--mono);
  font-size: 12px;
  color: var(--text-3);
  letter-spacing: 0.02em;
}
.qt-topbar-meta .qt-val { color: var(--text-2); }
.qt-topbar-meta .qt-sep { color: var(--hairline); }
.qt-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-2);
  border-radius: 6px;
  cursor: pointer;
  transition: color 160ms var(--ease), background 160ms var(--ease);
}
.qt-icon-btn:hover { color: var(--text); background: var(--surface-2); }
.qt-icon-btn svg { width: 16px; height: 16px; }
.qt-menu-toggle { display: none; }
.qt-scroll-actions {
  position: fixed;
  right: 18px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 35;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.qt-scroll-btn {
  width: 34px;
  height: 34px;
  border: 1px solid var(--hairline);
  border-radius: 7px;
  background: color-mix(in srgb, var(--bg) 82%, transparent);
  color: var(--text-2);
  backdrop-filter: blur(14px) saturate(1.25);
  -webkit-backdrop-filter: blur(14px) saturate(1.25);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.24);
  opacity: 0.74;
}
.qt-scroll-btn:hover {
  color: var(--text);
  background: var(--surface-2);
  border-color: var(--border);
  opacity: 1;
}
.qt-scroll-btn svg {
  width: 17px;
  height: 17px;
}

/* ============ Layout ============ */
.qt-shell {
  max-width: 1440px;
  margin: 0 auto;
  padding: 20px 16px 56px;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 40px;
}
.qt-sidebar {
  position: sticky;
  top: calc(var(--topbar-h) + 24px);
  align-self: start;
  max-height: calc(100vh - var(--topbar-h) - 48px);
  overflow-y: auto;
  padding-right: 8px;
  /* Invisible scrollbar with subtle reveal on hover */
  scrollbar-width: none;
  -ms-overflow-style: none;
  mask-image: linear-gradient(180deg, transparent 0, #000 12px, #000 calc(100% - 24px), transparent);
  -webkit-mask-image: linear-gradient(180deg, transparent 0, #000 12px, #000 calc(100% - 24px), transparent);
}
.qt-sidebar::-webkit-scrollbar { width: 0; height: 0; display: none; }
.qt-sidebar-title {
  margin: 0 0 16px;
  padding-left: 12px;
  color: var(--text-3);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-weight: 500;
}
.qt-sidebar a {
  position: relative;
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 6px 10px 6px 12px;
  color: var(--text-2);
  text-decoration: none;
  font-size: 13px;
  line-height: 1.45;
  border-left: 1px solid var(--hairline);
  transition: color 160ms var(--ease), border-color 160ms var(--ease);
}
.qt-sidebar a.qt-toc-l3 {
  padding-left: 28px;
  font-size: 12px;
  color: var(--text-3);
}
.qt-toc-num {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-3);
  letter-spacing: 0.04em;
  flex-shrink: 0;
  min-width: 16px;
}
.qt-sidebar a.qt-toc-l3 .qt-toc-num { display: none; }
.qt-toc-text { flex: 1; }
.qt-sidebar a:hover {
  color: var(--text);
  border-left-color: var(--text-3);
}
.qt-sidebar a.active {
  color: var(--text);
  border-left-color: var(--accent);
}
.qt-sidebar a.active .qt-toc-num { color: var(--text-2); }

/* ============ Main + Hero ============ */
.qt-main { min-width: 0; }
.qt-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 18px;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--text-3);
  letter-spacing: 0.14em;
  text-transform: uppercase;
}
.qt-eyebrow::before {
  content: "";
  width: 18px;
  height: 1px;
  background: var(--text-3);
}
.qt-title {
  margin: 0 0 14px;
  font-family: var(--sans);
  font-size: clamp(28px, 3.6vw, 44px);
  line-height: 1.1;
  letter-spacing: -0.025em;
  font-weight: 600;
  color: var(--text);
  max-width: 22ch;
}
.qt-subtitle {
  margin: 0;
  color: var(--text-2);
  font-size: 16px;
  line-height: 1.55;
  max-width: 58ch;
}
.qt-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(340px, 0.75fr);
  gap: 40px;
  padding: 0 0 28px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--hairline);
  align-items: start;
}
.qt-hero-left { min-width: 0; }
.qt-verdict {
  position: sticky;
  top: calc(var(--topbar-h) + 32px);
}
.qt-verdict-label {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-3);
  margin-bottom: 12px;
}
.qt-badge {
  display: flex;
  align-items: baseline;
  gap: 12px;
  font-family: var(--sans);
  font-size: 50px;
  line-height: 1;
  letter-spacing: -0.04em;
  font-weight: 600;
  margin-bottom: 14px;
}
.qt-badge.buy { color: var(--bull); }
.qt-badge.sell { color: var(--bear); }
.qt-badge.hold { color: var(--neutral); }
.qt-badge.unknown { color: var(--text-2); font-size: 32px; }
.qt-badge-conf {
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-3);
  letter-spacing: 0.02em;
}
.qt-conf-track {
  position: relative;
  width: 100%;
  height: 2px;
  background: var(--hairline);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 24px;
}
.qt-conf-fill {
  height: 100%;
  background: currentColor;
  transition: width 600ms var(--ease);
}
.qt-conf-fill.buy { color: var(--bull); }
.qt-conf-fill.sell { color: var(--bear); }
.qt-conf-fill.hold { color: var(--neutral); }
.qt-reasons {
  list-style: none;
  padding: 0;
  margin: 0 0 16px;
}
.qt-reasons li {
  position: relative;
  padding: 7px 0 7px 18px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-2);
  border-bottom: 1px solid var(--hairline);
}
.qt-reasons li:last-child { border-bottom: 0; }
.qt-reasons li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 15px;
  width: 8px;
  height: 1px;
  background: var(--text-3);
}
.qt-meta {
  display: grid;
  grid-template-columns: minmax(56px, 0.7fr) minmax(92px, 0.9fr) minmax(132px, 1.4fr);
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid var(--hairline);
}
.qt-meta-row {
  display: grid;
  gap: 4px;
  padding: 0;
  font-family: var(--mono);
  font-size: 12px;
}
.qt-meta-key { color: var(--text-3); letter-spacing: 0.04em; text-transform: uppercase; font-size: 10px; }
.qt-meta-val { color: var(--text); text-align: left; word-break: normal; overflow-wrap: anywhere; }

/* ============ Content sections ============ */
.qt-content { font-size: 15px; }
.qt-section {
  padding: 44px 0;
  border-bottom: 1px solid var(--hairline);
}
.qt-section:last-child { border-bottom: 0; }
.qt-section.qt-section-intro { padding-top: 0; }

.qt-section h2 {
  margin: 0 0 24px;
  font-family: var(--sans);
  font-size: 26px;
  line-height: 1.2;
  letter-spacing: -0.02em;
  font-weight: 600;
  color: var(--text);
}

/* Subtle kind indicator: a tiny colored marker before h2, not a left-border on entire card */
.qt-section h2::before {
  content: "";
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-3);
  margin-right: 14px;
  vertical-align: middle;
  transform: translateY(-3px);
}
.qt-section[data-kind="bull"] h2::before { background: var(--bull); }
.qt-section[data-kind="bear"] h2::before { background: var(--bear); }
.qt-section[data-kind="risk"] h2::before, .qt-section[data-kind="news"] h2::before { background: var(--neutral); }
.qt-section[data-kind="final"] h2::before { background: var(--bull); box-shadow: 0 0 0 3px color-mix(in srgb, var(--bull) 25%, transparent); }
.qt-section[data-kind="trader"] h2::before { background: var(--text); }

.qt-content :is(h1, h2, h3, h4, h5, h6) {
  font-family: var(--sans);
  font-weight: 600;
  color: var(--text);
}
.qt-content h3 {
  margin: 36px 0 14px;
  font-size: 18px;
  line-height: 1.3;
  letter-spacing: -0.01em;
}
.qt-content h4 {
  margin: 24px 0 10px;
  font-size: 15px;
  line-height: 1.4;
  color: var(--text);
}
.qt-content p {
  margin: 14px 0;
  color: var(--text-2);
  line-height: 1.75;
  max-width: 72ch;
}
.qt-content ul, .qt-content ol {
  color: var(--text-2);
  padding-left: 22px;
  margin: 14px 0;
}
.qt-content li {
  margin: 8px 0;
  line-height: 1.7;
  padding-left: 4px;
}
.qt-content ul li::marker { color: var(--text-3); }
.qt-content strong { color: var(--text); font-weight: 600; }
.qt-content em { color: var(--text); font-style: italic; }
.qt-content a {
  color: var(--link);
  text-decoration: none;
  border-bottom: 1px solid color-mix(in srgb, var(--link) 30%, transparent);
  transition: border-color 160ms var(--ease);
}
.qt-content a:hover { border-bottom-color: var(--link); }

/* ============ Tables ============ */
.qt-table-wrap {
  margin: 20px 0;
  overflow-x: auto;
  scrollbar-width: thin;
}
.qt-table-wrap::-webkit-scrollbar { height: 6px; }
.qt-table-wrap::-webkit-scrollbar-thumb { background: var(--border); border-radius: 6px; }
.qt-content table {
  width: 100%;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;
  font-size: 14px;
}
.qt-content thead th {
  position: sticky;
  top: var(--topbar-h);
  background: var(--bg);
  color: var(--text-3);
  font-weight: 500;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 10px 16px 10px 0;
  text-align: left;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.qt-content thead th:last-child { padding-right: 0; }
.qt-content tbody td {
  padding: 14px 16px 14px 0;
  border-bottom: 1px solid var(--hairline);
  color: var(--text-2);
  vertical-align: top;
}
.qt-content tbody td:last-child { padding-right: 0; }
.qt-content tbody tr:last-child td { border-bottom: 0; }
.qt-content tbody td:first-child { color: var(--text); font-weight: 500; }
.qt-content td:not(:first-child), .qt-content th:not(:first-child) {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.qt-content tbody tr { transition: background 120ms var(--ease); }
.qt-content tbody tr:hover { background: var(--surface-2); }

/* ============ Blockquote / Code ============ */
.qt-content blockquote {
  margin: 20px 0;
  padding: 4px 0 4px 20px;
  border-left: 2px solid var(--border);
  color: var(--text-2);
  font-style: normal;
}
.qt-content blockquote p { margin: 6px 0; max-width: none; }
.qt-content code {
  background: var(--surface-2);
  color: var(--text);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.88em;
  font-family: var(--mono);
}
.qt-content pre {
  position: relative;
  overflow-x: auto;
  padding: 18px 20px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  background: var(--surface);
  margin: 20px 0;
  font-size: 13px;
  line-height: 1.6;
}
.qt-content pre code {
  padding: 0;
  background: transparent;
  border: 0;
}
.qt-content img {
  max-width: 100%;
  border-radius: var(--radius);
  border: 1px solid var(--hairline);
  margin: 16px 0;
  display: block;
}
.qt-content hr {
  border: 0;
  border-top: 1px solid var(--hairline);
  margin: 32px 0;
}

/* ============ Inline status pills (BUY/SELL/HOLD only) ============ */
.qt-status {
  display: inline-block;
  padding: 0 6px;
  font-family: var(--mono);
  font-size: 0.82em;
  font-weight: 600;
  letter-spacing: 0.04em;
  border-radius: 3px;
  vertical-align: 0.05em;
}
.qt-status.buy { color: var(--bull); background: color-mix(in srgb, var(--bull) 10%, transparent); }
.qt-status.sell { color: var(--bear); background: color-mix(in srgb, var(--bear) 10%, transparent); }
.qt-status.hold { color: var(--neutral); background: color-mix(in srgb, var(--neutral) 10%, transparent); }

/* ============ Risk grid ============ */
.qt-section[data-kind="risk"] > ul,
.qt-section[data-kind="risk"] ul:not(ul ul) {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1px;
  padding: 0;
  list-style: none;
  background: var(--hairline);
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  overflow: hidden;
  margin: 20px 0;
}
.qt-section[data-kind="risk"] > ul > li,
.qt-section[data-kind="risk"] ul:not(ul ul) > li {
  margin: 0;
  padding: 18px 20px;
  background: var(--bg);
  list-style: none;
  line-height: 1.65;
}
.qt-section[data-kind="risk"] > ul > li::marker { content: ""; }

/* ============ Empty / utility ============ */
.qt-empty { color: var(--text-3); font-size: 13px; padding: 0 12px; }

/* ============ Mobile ============ */
@media (max-width: 900px) {
  .qt-shell { grid-template-columns: 1fr; padding: 20px 16px 40px; gap: 24px; }
  .qt-sidebar {
    display: none;
    position: fixed;
    z-index: 25;
    top: calc(var(--topbar-h) + 8px);
    left: 16px;
    right: 16px;
    max-height: 70vh;
    padding: 16px;
    background: var(--surface);
    border: 1px solid var(--hairline);
    border-radius: var(--radius);
    box-shadow: 0 12px 40px rgba(0,0,0,0.32);
    mask-image: none;
    -webkit-mask-image: none;
  }
  .qt-sidebar.open { display: block; }
  .qt-menu-toggle { display: inline-flex; }
  .qt-hero { grid-template-columns: 1fr; gap: 32px; padding-bottom: 32px; }
  .qt-verdict { position: static; }
  .qt-meta { grid-template-columns: 1fr; gap: 8px; }
  .qt-meta-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }
  .qt-meta-val { text-align: right; }
  .qt-badge { font-size: 44px; }
  .qt-topbar { gap: 12px; }
  .qt-topbar-meta { gap: 10px; font-size: 11px; }
  .qt-topbar-meta .qt-field-optional { display: none; }
  .qt-section { padding: 40px 0; }
  .qt-section h2 { font-size: 22px; }
  .qt-scroll-actions { right: 12px; }
  .qt-scroll-btn { width: 32px; height: 32px; }
}

/* ============ Reduced motion ============ */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    transition-duration: 0.001ms !important;
    scroll-behavior: auto !important;
  }
}

/* ============ Print ============ */
@media print {
  @page { margin: 18mm; }
  .qt-topbar, .qt-sidebar, .qt-icon-btn, .qt-scroll-actions { display: none !important; }
  body {
    background: #fff;
    color: #111;
    font-family: Georgia, "Times New Roman", "PingFang SC", "Microsoft YaHei", serif;
    font-size: 11pt;
    line-height: 1.55;
  }
  .qt-shell { display: block; max-width: none; padding: 0; }
  .qt-hero { display: block; border-bottom: 1px solid #ccc; padding-bottom: 16pt; }
  .qt-section { padding: 16pt 0; border-bottom: 1px solid #ddd; break-inside: avoid; }
  .qt-section h2::before { display: none; }
  .qt-content a { color: #111; border-bottom: 1px solid #999; }
}
`;
}

function buildQuantScript(): string {
  return `
(function () {
  const root = document.documentElement;
  const saved = localStorage.getItem("qt-theme") || "dark";
  root.setAttribute("data-theme", saved);

  const sunIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>';
  const moonIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';

  const syncToggle = () => {
    document.querySelectorAll("[data-theme-toggle]").forEach((b) => {
      b.innerHTML = root.getAttribute("data-theme") === "light" ? moonIcon : sunIcon;
      b.setAttribute("aria-label", root.getAttribute("data-theme") === "light" ? "Switch to dark theme" : "Switch to light theme");
    });
  };
  syncToggle();
  const applyTheme = (next) => {
    root.setAttribute("data-theme", next);
    localStorage.setItem("qt-theme", next);
    syncToggle();
  };
  document.querySelectorAll("[data-theme-toggle]").forEach((b) => {
    b.addEventListener("click", () => {
      const next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
      if (typeof document.startViewTransition === "function") document.startViewTransition(() => applyTheme(next));
      else applyTheme(next);
    });
  });

  const menu = document.querySelector("[data-toc]");
  document.querySelectorAll("[data-menu-toggle]").forEach((b) => {
    b.addEventListener("click", () => menu && menu.classList.toggle("open"));
  });
  document.querySelectorAll("[data-toc] a").forEach((a) => {
    a.addEventListener("click", (event) => {
      event.preventDefault();
      const href = a.getAttribute("href") || "";
      const target = href.startsWith("#") ? document.getElementById(href.slice(1)) : null;
      if (target) target.scrollIntoView({ block: "start", behavior: "auto" });
      menu && menu.classList.remove("open");
    });
  });

  document.querySelectorAll("[data-scroll-target]").forEach((b) => {
    b.addEventListener("click", () => {
      const target = b.getAttribute("data-scroll-target");
      const maxScroll = Math.max(
        document.body.scrollHeight,
        document.body.offsetHeight,
        document.documentElement.clientHeight,
        document.documentElement.scrollHeight,
        document.documentElement.offsetHeight,
      ) - window.innerHeight;
      const top = target === "bottom" ? Math.max(0, maxScroll) : 0;
      document.documentElement.scrollTop = top;
      document.body.scrollTop = top;
      window.scrollTo({ top, left: 0, behavior: "auto" });
    });
  });

  // Wrap tables for horizontal scroll
  document.querySelectorAll(".qt-content table").forEach((table) => {
    if (table.parentElement && table.parentElement.classList.contains("qt-table-wrap")) return;
    const wrap = document.createElement("div");
    wrap.className = "qt-table-wrap";
    table.parentNode && table.parentNode.insertBefore(wrap, table);
    wrap.appendChild(table);
  });

  // Subtle inline pills for trading verdicts only
  const verdictPattern = /\\b(BUY|SELL|HOLD)\\b/g;
  const content = document.querySelector(".qt-content");
  if (content) {
    const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;
        if (/^(SCRIPT|STYLE|CODE|PRE|A|H1|H2|H3|H4|H5|H6)$/i.test(parent.tagName)) return NodeFilter.FILTER_REJECT;
        if (parent.closest(".qt-status, .qt-badge")) return NodeFilter.FILTER_REJECT;
        verdictPattern.lastIndex = 0;
        return verdictPattern.test(node.nodeValue || "") ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      const fragment = document.createDocumentFragment();
      const text = node.nodeValue || "";
      let lastIndex = 0;
      text.replace(verdictPattern, (match, _g, offset) => {
        fragment.appendChild(document.createTextNode(text.slice(lastIndex, offset)));
        const span = document.createElement("span");
        span.className = "qt-status " + match.toLowerCase();
        span.textContent = match;
        fragment.appendChild(span);
        lastIndex = offset + match.length;
        return match;
      });
      fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
      node.parentNode && node.parentNode.replaceChild(fragment, node);
    });
  }

  // Active TOC link
  const links = Array.from(document.querySelectorAll("[data-toc] a"));
  const sections = links
    .map((link) => document.getElementById((link.getAttribute("href") || "").slice(1)))
    .filter(Boolean);
  if ("IntersectionObserver" in window && sections.length) {
    let activeId = null;
    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((e) => e.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      const newId = visible.target.id;
      if (newId === activeId) return;
      activeId = newId;
      links.forEach((link) => {
        link.classList.toggle("active", link.getAttribute("href") === "#" + newId);
      });
    }, { rootMargin: "-80px 0px -65% 0px", threshold: [0.1, 0.5] });
    sections.forEach((s) => observer.observe(s));
  }
}());
`;
}

export async function renderQuantTerminalDocument(
  markdown: string,
  title: string,
  options?: Partial<Omit<CliOptions, "inputPath">>,
  overrides?: Partial<QuantMeta>,
): Promise<string> {
  const rendered = await renderMarkdownDocument(markdown, {
    codeTheme: options?.codeTheme,
    countStatus: false,
    citeStatus: options?.citeStatus ?? false,
    defaultTitle: title,
    fontFamily: options?.fontFamily,
    fontSize: options?.fontSize,
    isMacCodeBlock: false,
    isShowLineNumber: options?.isShowLineNumber ?? false,
    keepTitle: true,
    legend: options?.legend,
    primaryColor: options?.primaryColor,
    theme: "simple",
  });
  const enhanced = enhanceSections(rendered.contentHtml);
  const meta = extractMeta(markdown, title, overrides);
  const reasons = extractReasons(markdown);
  const vClass = verdictClass(meta.verdict);
  const hasConf = meta.confidence !== undefined;

  const confidenceBlock = hasConf
    ? `<div class="qt-conf-track"><div class="qt-conf-fill ${vClass}" style="width:${meta.confidence}%"></div></div>`
    : "";

  const reasonsHtml = reasons.length
    ? `<ul class="qt-reasons">${reasons.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>`
    : "";

  const metaHtml = `
    <div class="qt-meta">
      <div class="qt-meta-row"><span class="qt-meta-key">Ticker</span><span class="qt-meta-val">${escapeHtml(meta.ticker)}</span></div>
      <div class="qt-meta-row"><span class="qt-meta-key">Date</span><span class="qt-meta-val">${escapeHtml(meta.date)}</span></div>
      <div class="qt-meta-row"><span class="qt-meta-key">Model</span><span class="qt-meta-val">${escapeHtml(meta.model)}</span></div>
    </div>`;

  return `<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>${buildQuantCss()}</style>
</head>
<body>
  <header class="qt-topbar">
    <button class="qt-icon-btn qt-menu-toggle" data-menu-toggle type="button" aria-label="Toggle contents">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
    </button>
    <div class="qt-brand">
      <div class="qt-brand-mark" aria-hidden="true"></div>
      <span>Trading Research</span>
    </div>
    <div class="qt-topbar-meta">
      <span><span class="qt-val">${escapeHtml(meta.ticker)}</span></span>
      <span class="qt-sep">·</span>
      <span class="qt-field-optional">${escapeHtml(meta.date)}</span>
    </div>
    <button class="qt-icon-btn" data-theme-toggle type="button" aria-label="Toggle theme"></button>
  </header>
  <div class="qt-shell">
    <aside class="qt-sidebar" data-toc>
      <p class="qt-sidebar-title">Contents</p>
      ${buildToc(enhanced.toc)}
    </aside>
    <main class="qt-main">
      <section class="qt-hero">
        <div class="qt-hero-left">
          <div class="qt-eyebrow">Multi-agent research · ${escapeHtml(meta.date)}</div>
          <h1 class="qt-title">${escapeHtml(title)}</h1>
          <p class="qt-subtitle">A consolidated trading research synthesis combining fundamentals, sentiment, technical, and risk perspectives.</p>
        </div>
        <aside class="qt-verdict">
          <div class="qt-verdict-label">Final Verdict</div>
          <div class="qt-badge ${vClass}">
            <span>${escapeHtml(meta.verdict)}</span>
            ${hasConf ? `<span class="qt-badge-conf">${meta.confidence}%</span>` : ""}
          </div>
          ${confidenceBlock}
          ${reasonsHtml}
          ${metaHtml}
        </aside>
      </section>
      <article class="qt-content">
        ${enhanced.html}
      </article>
    </main>
  </div>
  <div class="qt-scroll-actions" aria-label="Page scroll controls">
    <button class="qt-icon-btn qt-scroll-btn" data-scroll-target="top" type="button" aria-label="Scroll to top" title="Top">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></svg>
    </button>
    <button class="qt-icon-btn qt-scroll-btn" data-scroll-target="bottom" type="button" aria-label="Scroll to bottom" title="Bottom">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="m19 12-7 7-7-7"/></svg>
    </button>
  </div>
  <script>${buildQuantScript()}</script>
</body>
</html>`;
}

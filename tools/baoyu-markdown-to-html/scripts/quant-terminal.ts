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

const SECTION_MARKERS: Record<string, string> = {
  fundamentals: "FN",
  sentiment: "SN",
  news: "NW",
  technical: "TA",
  bull: "UP",
  bear: "DN",
  manager: "RM",
  trader: "TR",
  risk: "RK",
  final: "FD",
  default: "SC",
};

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
function sectionLabel(kind: string): string {
  const labels: Record<string, string> = {
    fundamentals: "Fundamentals",
    sentiment: "Sentiment",
    news: "News",
    technical: "Technical",
    bull: "Bull Case",
    bear: "Bear Case",
    manager: "Research Manager",
    trader: "Trader Plan",
    risk: "Risk Management",
    final: "Final Decision",
    default: "Section",
  };
  return labels[kind] ?? labels.default;
}
function sectionMarker(kind: string): string {
  return SECTION_MARKERS[kind] ?? SECTION_MARKERS.default;
}

function enhanceSections(contentHtml: string): { html: string; toc: TocItem[] } {
  // Capture h2 (top-level sections) and optionally h3 (subsections for TOC hierarchy)
  const headingPattern = /<h([23])([^>]*)>([\s\S]*?)<\/h\1>/gi;
  const matches = [...contentHtml.matchAll(headingPattern)];
  const h2Matches = matches.filter((m) => m[1] === "2");

  if (!h2Matches.length) {
    return {
      html: `<section class="qt-section qt-section-default">${contentHtml}</section>`,
      toc: [],
    };
  }

  const seen = new Map<string, number>();
  const toc: TocItem[] = [];
  const parts: string[] = [];
  let cursor = 0;

  // Intro before first h2
  if ((h2Matches[0]?.index ?? 0) > 0) {
    parts.push(
      `<section class="qt-section qt-section-intro">${contentHtml.slice(0, h2Matches[0]!.index)}</section>`,
    );
    cursor = h2Matches[0]!.index!;
  }

  // Process each h2 section, also collecting h3s within for TOC
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

    // Build section HTML with kicker only (avoid redundancy if title closely matches kind)
    const kickerLabel = sectionLabel(kind);
    const titleLower = title.toLowerCase();
    const kickerLower = kickerLabel.toLowerCase();
    const showKicker = !(
      titleLower === kickerLower ||
      titleLower.includes(kickerLower) ||
      kickerLower.includes(titleLower)
    );

    const newH2 = showKicker
      ? `<div class="qt-section-kicker"><span class="qt-section-icon">${sectionMarker(kind)}</span>${kickerLabel}</div><h2${attrs} id="${id}">${inner}</h2>`
      : `<h2${attrs} id="${id}"><span class="qt-section-icon-inline">${sectionMarker(kind)}</span>${inner}</h2>`;

    let sectionInner = contentHtml.slice(start, end).replace(match[0], newH2);

    // Collect h3s inside for hierarchical TOC
    const h3Pattern = /<h3([^>]*)>([\s\S]*?)<\/h3>/gi;
    sectionInner = sectionInner.replace(h3Pattern, (full, h3attrs, h3inner) => {
      const h3Title = stripTags(h3inner);
      const h3Id = uniqueSlug(slugify(h3Title), seen);
      toc.push({ id: h3Id, title: h3Title, level: 3 });
      // If h3 has no id already, inject one
      const hasId = /id\s*=/.test(h3attrs);
      const newAttrs = hasId ? h3attrs : `${h3attrs} id="${h3Id}"`;
      return `<h3${newAttrs}>${h3inner}</h3>`;
    });

    parts.push(
      `<section class="qt-section qt-section-${kind}" data-section-kind="${kind}">${sectionInner}</section>`,
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
    "Unknown";
  const date =
    overrides?.date ||
    firstMatch(markdown, [
      /(?:analysis date|date|分析日期|日期)\s*[:：]\s*(\d{4}-\d{2}-\d{2})/i,
      /\b(\d{4}-\d{2}-\d{2})\b/,
    ]) ||
    "Unknown";
  const model =
    overrides?.model ||
    firstMatch(markdown, [
      /(?:model|llm|quick|deep|模型)\s*[:：]\s*`?([A-Za-z0-9_.:/\- ]{2,80})`?/i,
    ]) ||
    "Unknown";
  const finalSection =
    markdown.match(/(?:final|portfolio|decision|verdict|最终|决策)[\s\S]{0,2500}/i)?.[0] ??
    markdown;
  const verdict =
    firstMatch(finalSection, [/\b(BUY|SELL|HOLD)\b/i]).toUpperCase() ||
    firstMatch(finalSection, [/(买入|卖出|持有)/]).replace(/买入/, "BUY").replace(/卖出/, "SELL").replace(/持有/, "HOLD") ||
    "Unknown";
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
  if (bullets.length) return bullets.slice(0, 4);
  const sentences = finalSection
    .replace(/[#*_`>]/g, "")
    .split(/(?<=[.!?。！？])\s+/)
    .map((sentence) => sentence.trim())
    .filter(
      (sentence) =>
        sentence.length >= 24 && !/\b(BUY|SELL|HOLD)\b$/i.test(sentence),
    );
  return sentences.slice(0, 3);
}
function verdictClass(verdict: string): string {
  if (verdict === "BUY") return "buy";
  if (verdict === "SELL") return "sell";
  if (verdict === "HOLD") return "hold";
  return "unknown";
}
function buildToc(toc: TocItem[]): string {
  if (!toc.length) return '<p class="qt-empty-toc">No sections found.</p>';
  return toc
    .map(
      (item) =>
        `<a href="#${item.id}" class="qt-toc-l${item.level}" data-toc-level="${item.level}">${escapeHtml(item.title)}</a>`,
    )
    .join("\n");
}

function buildQuantCss(): string {
  return `
:root {
  --bg: #07090F;
  --card: #131825;
  --nested: #1C2333;
  --border: #2A3142;
  --text: #E8ECF4;
  --text-2: #B4C2D4;
  --muted: #7B8696;
  --bull: #00D68F;
  --bear: #FF4757;
  --neutral: #FFB547;
  --ai: #4DA3FF;
  --ml: #B794F6;
  --grad: linear-gradient(135deg, #4DA3FF 0%, #B794F6 100%);
  --code-bg: #0B0F16;
  --line-soft: rgba(232,236,244,0.08);
  --panel-shadow: 0 1px 3px rgba(0,0,0,0.32), 0 12px 32px -16px rgba(0,0,0,0.5);
  --sans: "Geist", "Inter", -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui, sans-serif;
  --mono: "JetBrains Mono", "IBM Plex Mono", monospace;
  --hairline: color-mix(in srgb, var(--border) 85%, transparent);
  --elev-1: rgba(255,255,255,0.025);
  --elev-2: rgba(255,255,255,0.05);
  --elev-3: rgba(255,255,255,0.08);
  --ease-out-expo: cubic-bezier(0.22, 1, 0.36, 1);
}
[data-theme="light"] {
  --bg: #FCFCFD;
  --card: #FFFFFF;
  --nested: #F4F6FA;
  --border: #E5E7EB;
  --text: #0F172A;
  --text-2: #475569;
  --muted: #64748B;
  --code-bg: #EEF1F6;
  --line-soft: rgba(15,23,42,0.08);
  --panel-shadow: 0 1px 3px rgba(15,23,42,0.06), 0 12px 32px -20px rgba(15,23,42,0.18);
  --hairline: color-mix(in srgb, var(--border) 90%, transparent);
  --elev-1: rgba(15,23,42,0.02);
  --elev-2: rgba(15,23,42,0.04);
  --elev-3: rgba(15,23,42,0.06);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 64px; }
body {
  margin: 0;
  background:
    radial-gradient(circle at 8% -12%, rgba(77,163,255,0.08), transparent 28rem),
    radial-gradient(circle at 92% 4%, rgba(183,148,246,0.05), transparent 30rem),
    var(--bg);
  color: var(--text);
  font-family: var(--sans);
  line-height: 1.7;
  font-variant-numeric: tabular-nums slashed-zero;
  font-feature-settings: "ss01", "cv11", "tnum", "zero";
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
:lang(zh), :lang(zh-CN), :lang(zh-TW) { line-height: 1.85; }
.qt-mono, code, pre, .qt-topbar .qt-mono, .qt-badge, .qt-num,
.qt-confidence-label, .qt-section-kicker, .qt-section-icon, .qt-section-icon-inline,
.qt-status, .qt-token { font-family: var(--mono); }
.qt-progress-bar {
  position: fixed;
  top: 0; left: 0;
  height: 2px;
  width: 0%;
  background: var(--grad);
  z-index: 100;
  pointer-events: none;
  transition: width 80ms linear;
}
.qt-topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  height: 48px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 max(18px, calc((100vw - 1200px) / 2 + 24px));
  background: color-mix(in srgb, var(--card) 88%, transparent);
  backdrop-filter: blur(18px) saturate(1.4);
  -webkit-backdrop-filter: blur(18px) saturate(1.4);
  border-bottom: 1px solid var(--hairline);
  color: var(--text-2);
  font-size: 13px;
  overflow-x: auto;
}
.qt-led {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--bull);
  box-shadow: 0 0 0 0 rgba(0,214,143,0.5);
  animation: qtPulse 2.4s infinite;
  flex-shrink: 0;
}
@keyframes qtPulse {
  70% { box-shadow: 0 0 0 7px rgba(0,214,143,0); }
  100% { box-shadow: 0 0 0 0 rgba(0,214,143,0); }
}
.qt-theme-toggle, .qt-menu-toggle {
  border: 1px solid var(--hairline);
  background: var(--nested);
  color: var(--text);
  border-radius: 8px;
  min-height: 30px;
  padding: 0 12px;
  font-size: 12px;
  cursor: pointer;
  font-family: var(--mono);
  transition: border-color 200ms var(--ease-out-expo), background 200ms var(--ease-out-expo);
}
.qt-theme-toggle:hover, .qt-menu-toggle:hover {
  border-color: var(--ai);
  background: color-mix(in srgb, var(--nested) 80%, var(--ai) 20%);
}
.qt-theme-toggle { margin-left: auto; }
.qt-sep { color: var(--muted); }
.qt-live { color: var(--text); font-weight: 600; letter-spacing: 0.06em; font-family: var(--mono); }
.qt-field { white-space: nowrap; font-family: var(--mono); }
.qt-field strong { color: var(--text); }
.qt-field-label { color: var(--muted); }
.qt-menu-toggle { display: none; width: 42px; padding: 0; justify-content: center; }
.qt-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 24px 40px;
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 28px;
}
.qt-sidebar {
  position: sticky;
  top: 72px;
  align-self: start;
  max-height: calc(100vh - 96px);
  overflow-y: auto;
  scrollbar-width: thin;
  padding: 14px 12px 12px;
  border: 1px solid var(--hairline);
  border-radius: 12px;
  background: color-mix(in srgb, var(--card) 92%, transparent);
  box-shadow: var(--panel-shadow);
}
.qt-sidebar::-webkit-scrollbar { width: 4px; }
.qt-sidebar::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
.qt-sidebar-title {
  margin: 2px 4px 12px;
  color: var(--muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-family: var(--mono);
}
.qt-sidebar a {
  position: relative;
  display: block;
  padding: 8px 10px 8px 16px;
  margin: 1px 0;
  color: var(--text-2);
  text-decoration: none;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.4;
  transition: color 200ms var(--ease-out-expo), background 200ms var(--ease-out-expo);
}
.qt-sidebar a.qt-toc-l3 {
  padding-left: 26px;
  font-size: 12px;
  color: var(--muted);
}
.qt-sidebar a::before {
  content: "";
  position: absolute;
  left: 6px;
  top: 50%;
  width: 3px;
  height: 3px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--text-2) 40%, transparent);
  transform: translateY(-50%);
  transition: all 250ms var(--ease-out-expo);
}
.qt-sidebar a.qt-toc-l3::before { left: 16px; }
.qt-sidebar a:hover {
  color: var(--ai);
  background: var(--elev-2);
}
.qt-sidebar a:hover::before { background: var(--ai); }
.qt-sidebar a.active {
  color: var(--ai);
  background: color-mix(in srgb, var(--nested) 70%, var(--ai) 8%);
}
.qt-sidebar a.active::before {
  background: var(--ai);
  width: 3px;
  height: 16px;
  border-radius: 2px;
}
.qt-main { min-width: 0; }
.qt-hero {
  position: relative;
  margin-bottom: 24px;
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(280px, 0.7fr);
  gap: 24px;
  align-items: stretch;
  padding: 28px;
  border: 1px solid var(--hairline);
  border-radius: 14px;
  overflow: hidden;
  background:
    radial-gradient(circle at 0% 0%, rgba(77,163,255,0.10), transparent 42%),
    linear-gradient(135deg, rgba(183,148,246,0.05), transparent 38%),
    var(--card);
  box-shadow: var(--panel-shadow);
}
.qt-hero::before {
  content: attr(data-watermark);
  position: absolute;
  right: -2%;
  bottom: -28%;
  font-family: var(--mono);
  font-weight: 700;
  font-size: 200px;
  letter-spacing: -0.04em;
  color: var(--text);
  opacity: 0.035;
  pointer-events: none;
  line-height: 1;
  white-space: nowrap;
}
.qt-hero-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 16px;
  position: relative;
  z-index: 1;
}
.qt-title {
  margin: 0;
  max-width: 820px;
  font-family: var(--sans);
  font-size: clamp(26px, 3.2vw, 38px);
  line-height: 1.15;
  letter-spacing: -0.02em;
  font-weight: 600;
}
.qt-subtitle { margin: 0; color: var(--text-2); max-width: 58ch; line-height: 1.6; font-size: 14px; }
.qt-verdict-card {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 18px;
  padding: 22px;
  border-radius: 12px;
  border: 1px solid var(--hairline);
  background: var(--nested);
  z-index: 1;
}
.qt-verdict-card.has-confidence::before {
  content: "";
  position: absolute;
  inset: -1px;
  border-radius: 13px;
  padding: 1px;
  background: conic-gradient(
    from var(--qt-angle, 0deg),
    rgba(77,163,255,0) 0deg,
    rgba(77,163,255,0.5) 60deg,
    rgba(183,148,246,0.5) 120deg,
    rgba(77,163,255,0) 200deg,
    rgba(77,163,255,0) 360deg
  );
  -webkit-mask: linear-gradient(#000, #000) content-box, linear-gradient(#000, #000);
  -webkit-mask-composite: xor;
          mask-composite: exclude;
  animation: qtConic 12s linear infinite;
  pointer-events: none;
  z-index: -1;
}
@property --qt-angle {
  syntax: "<angle>";
  initial-value: 0deg;
  inherits: false;
}
@keyframes qtConic { to { --qt-angle: 360deg; } }
.qt-verdict-label {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
}
.qt-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-width: 110px;
  padding: 10px 18px;
  border-radius: 8px;
  font-family: var(--mono);
  font-size: 28px;
  font-weight: 600;
  letter-spacing: 0.04em;
}
.qt-badge.buy { color: var(--bull); border: 1px solid color-mix(in srgb, var(--bull) 60%, transparent); background: rgba(0,214,143,0.10); box-shadow: 0 0 20px rgba(0,214,143,0.18), inset 0 0 0 1px rgba(0,214,143,0.15); }
.qt-badge.sell { color: var(--bear); border: 1px solid color-mix(in srgb, var(--bear) 60%, transparent); background: rgba(255,71,87,0.10); box-shadow: 0 0 20px rgba(255,71,87,0.18), inset 0 0 0 1px rgba(255,71,87,0.15); }
.qt-badge.hold { color: var(--neutral); border: 1px solid color-mix(in srgb, var(--neutral) 60%, transparent); background: rgba(255,181,71,0.10); box-shadow: 0 0 20px rgba(255,181,71,0.18), inset 0 0 0 1px rgba(255,181,71,0.15); }
.qt-badge.unknown { color: var(--text-2); border: 1px solid var(--hairline); background: var(--card); font-size: 22px; }
.qt-confidence-label {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  color: var(--text-2);
  font-size: 12px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-family: var(--mono);
}
.qt-confidence-track {
  position: relative;
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: var(--card);
  border: 1px solid var(--hairline);
  overflow: hidden;
}
.qt-confidence-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--grad);
}
.qt-meta-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--line-soft);
}
.qt-meta-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-family: var(--mono);
  font-size: 12px;
}
.qt-meta-item-label { color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }
.qt-meta-item-value { color: var(--text); text-align: right; word-break: break-all; }
.qt-reasons {
  margin: 4px 0 0;
  padding: 14px 0 0 18px;
  border-top: 1px solid var(--line-soft);
  color: var(--text-2);
  font-size: 13px;
  line-height: 1.65;
  font-family: var(--sans);
}
.qt-reasons li + li { margin-top: 8px; }
.qt-section {
  position: relative;
  margin: 16px 0;
  padding: 24px 26px;
  border: 1px solid var(--hairline);
  border-radius: 12px;
  background: var(--card);
  box-shadow: var(--panel-shadow);
  animation: qtRise 480ms var(--ease-out-expo) both;
  animation-delay: calc(min(var(--qt-index, 0), 6) * 60ms);
  transition: border-color 280ms var(--ease-out-expo), box-shadow 280ms var(--ease-out-expo);
  overflow: hidden;
}
.qt-section::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--ai);
  opacity: 0.85;
}
.qt-section:hover {
  border-color: color-mix(in srgb, var(--ai) 30%, var(--hairline));
  box-shadow: var(--panel-shadow), 0 6px 20px -16px rgba(77,163,255,0.4);
}
@keyframes qtRise {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.qt-section-kicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 8px 0;
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.qt-section-icon, .qt-section-icon-inline {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 26px;
  height: 20px;
  padding: 0 6px;
  border: 1px solid currentColor;
  border-radius: 4px;
  font-size: 10px;
  letter-spacing: 0.04em;
  background: color-mix(in srgb, currentColor 8%, transparent);
}
.qt-section-icon-inline {
  margin-right: 10px;
  vertical-align: middle;
  color: var(--ai);
}
.qt-section h2 {
  margin: 0 0 16px 0;
  color: var(--text);
  font-size: 22px;
  letter-spacing: -0.015em;
}
.qt-section-fundamentals::before, .qt-section-technical::before { background: var(--ai); }
.qt-section-sentiment::before, .qt-section-manager::before { background: var(--ml); }
.qt-section-news::before, .qt-section-risk::before { background: var(--neutral); }
.qt-section-bull::before { background: var(--bull); }
.qt-section-bear::before { background: var(--bear); }
.qt-section-final::before { background: linear-gradient(180deg, var(--bull), var(--ai)); }
.qt-section-trader::before { background: var(--grad); }
.qt-content :is(h1,h2,h3,h4,h5,h6) {
  font-family: var(--sans);
  line-height: 1.3;
  font-weight: 600;
  color: var(--text);
}
.qt-content h3 {
  margin: 28px 0 12px;
  font-size: 17px;
  letter-spacing: -0.01em;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line-soft);
}
.qt-content h4 { margin: 20px 0 8px; font-size: 15px; }
.qt-content p {
  color: var(--text-2);
  line-height: 1.75;
  max-width: 78ch;
  margin: 12px 0;
}
.qt-content ul, .qt-content ol { color: var(--text-2); padding-left: 22px; }
.qt-content li { margin: 6px 0; line-height: 1.7; }
.qt-content strong { color: var(--text); font-weight: 600; }
.qt-content a {
  color: var(--ai);
  text-decoration-color: color-mix(in srgb, var(--ai) 40%, transparent);
  text-underline-offset: 3px;
  transition: color 200ms var(--ease-out-expo), text-decoration-color 200ms var(--ease-out-expo);
}
.qt-content a:hover { text-decoration-color: var(--ai); }
.qt-table-wrap {
  margin: 16px 0;
  border: 1px solid var(--hairline);
  border-radius: 10px;
  overflow-x: auto;
  position: relative;
}
.qt-table-wrap::after {
  content: "";
  position: absolute;
  top: 0; right: 0; bottom: 0;
  width: 24px;
  background: linear-gradient(90deg, transparent, var(--card));
  pointer-events: none;
  opacity: 0;
  transition: opacity 200ms;
}
.qt-table-wrap.has-overflow::after { opacity: 1; }
.qt-content table {
  width: 100%;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums slashed-zero;
  font-size: 14px;
}
.qt-content th {
  position: sticky;
  top: 48px;
  background: var(--nested);
  color: var(--text);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: 11px;
  padding: 14px 16px;
  text-align: left;
  border-bottom: 1px solid var(--hairline);
}
.qt-content td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--line-soft);
  text-align: left;
}
.qt-content td:not(:first-child), .qt-content th:not(:first-child) {
  text-align: right;
  font-variant-numeric: tabular-nums slashed-zero;
}
.qt-content tr:nth-child(even) td { background: var(--elev-1); }
.qt-content tbody tr:hover td { background: rgba(77,163,255,0.05); }
.qt-content tbody tr:last-child td { border-bottom: 0; }
.qt-content blockquote {
  margin: 16px 0;
  padding: 14px 18px;
  border-left: 3px solid var(--ai);
  border-radius: 0 8px 8px 0;
  background: var(--nested);
  color: var(--text-2);
}
.qt-content blockquote p { margin: 4px 0; }
.qt-content code {
  background: var(--code-bg);
  color: var(--text);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.88em;
  border: 1px solid var(--hairline);
}
.qt-content pre {
  position: relative;
  overflow-x: auto;
  padding: 36px 22px 20px;
  border-radius: 10px;
  background: var(--code-bg);
  border: 1px solid var(--hairline);
  margin: 16px 0;
}
.qt-content pre::before {
  content: "";
  position: absolute;
  top: 14px;
  left: 16px;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #B34540;
  box-shadow: 16px 0 0 #B28522, 32px 0 0 #1F8C2D;
  opacity: 0.75;
}
.qt-content pre code {
  padding: 0;
  background: transparent;
  border: 0;
  font-size: 13px;
  line-height: 1.6;
}
.qt-content img {
  max-width: 100%;
  border-radius: 10px;
  border: 1px solid var(--hairline);
  margin: 12px 0;
}
.qt-content hr { border: 0; border-top: 1px solid var(--hairline); margin: 24px 0; }
.qt-empty-toc { color: var(--muted); font-size: 13px; }
.qt-status {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  border: 1px solid currentColor;
  border-radius: 4px;
  font-size: 0.82em;
  line-height: 1.5;
  letter-spacing: 0.04em;
  font-weight: 600;
  white-space: nowrap;
  vertical-align: baseline;
}
.qt-status.buy { color: var(--bull); background: rgba(0,214,143,0.08); }
.qt-status.sell { color: var(--bear); background: rgba(255,71,87,0.08); }
.qt-status.hold { color: var(--neutral); background: rgba(255,181,71,0.08); }
.qt-section-risk ul {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  padding-left: 0;
  list-style: none;
  margin: 16px 0;
}
.qt-section-risk li {
  padding: 14px 16px;
  border: 1px solid var(--hairline);
  border-radius: 8px;
  background: var(--nested);
  margin: 0;
  line-height: 1.65;
}
@media (max-width: 860px) {
  .qt-shell { grid-template-columns: 1fr; padding: 16px 16px 28px; gap: 18px; }
  .qt-sidebar {
    display: none;
    position: fixed;
    z-index: 25;
    inset: 56px 16px auto;
    max-height: 70vh;
  }
  .qt-sidebar.open { display: block; }
  .qt-menu-toggle { display: inline-flex; align-items: center; }
  .qt-hero { grid-template-columns: 1fr; padding: 22px; }
  .qt-hero::before { font-size: 130px; bottom: -22%; }
  .qt-section { padding: 18px 20px; }
  .qt-badge { font-size: 24px; min-width: 100px; padding: 8px 16px; }
  .qt-field.optional, .qt-sep.optional { display: none; }
  .qt-section-risk ul { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
    scroll-behavior: auto !important;
  }
  .qt-verdict-card.has-confidence::before { animation: none; }
  .qt-led { animation: none; }
}
@media print {
  @page { margin: 18mm; }
  .qt-topbar, .qt-sidebar, .qt-menu-toggle, .qt-theme-toggle, .qt-progress-bar { display: none !important; }
  body {
    background: #fff;
    color: #111;
    font-family: Georgia, "Times New Roman", "PingFang SC", "Microsoft YaHei", serif;
  }
  .qt-shell { display: block; max-width: none; padding: 0; }
  .qt-hero, .qt-section {
    break-inside: avoid;
    box-shadow: none;
    background: #fff !important;
    border-color: #ccc !important;
  }
  .qt-hero::before { display: none; }
  .qt-content a { color: #111; text-decoration: underline; }
  .qt-badge { box-shadow: none !important; }
  .qt-verdict-card.has-confidence::before { display: none; }
}
`;
}

function buildQuantScript(): string {
  return `
(function () {
  const root = document.documentElement;
  const saved = localStorage.getItem("qt-theme") || "dark";
  root.setAttribute("data-theme", saved);
  const syncToggle = () => {
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.textContent = root.getAttribute("data-theme") === "light" ? "Dark" : "Light";
    });
  };
  syncToggle();
  const applyTheme = (next) => {
    root.setAttribute("data-theme", next);
    localStorage.setItem("qt-theme", next);
    syncToggle();
  };
  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
      if (typeof document.startViewTransition === "function") {
        document.startViewTransition(() => applyTheme(next));
      } else {
        applyTheme(next);
      }
    });
  });

  const menu = document.querySelector("[data-toc]");
  document.querySelectorAll("[data-menu-toggle]").forEach((button) => {
    button.addEventListener("click", () => menu && menu.classList.toggle("open"));
  });
  document.querySelectorAll("[data-toc] a").forEach((link) => {
    link.addEventListener("click", () => menu && menu.classList.remove("open"));
  });

  document.querySelectorAll(".qt-section").forEach((section, index) => {
    section.style.setProperty("--qt-index", String(index));
  });

  const hero = document.querySelector(".qt-hero");
  if (hero && !hero.getAttribute("data-watermark")) {
    const tickerEl = document.querySelector("[data-ticker]");
    if (tickerEl && tickerEl.textContent) {
      hero.setAttribute("data-watermark", tickerEl.textContent.trim());
    }
  }

  // Wrap tables for overflow detection
  document.querySelectorAll(".qt-content table").forEach((table) => {
    if (table.parentElement && table.parentElement.classList.contains("qt-table-wrap")) return;
    const wrap = document.createElement("div");
    wrap.className = "qt-table-wrap";
    table.parentNode && table.parentNode.insertBefore(wrap, table);
    wrap.appendChild(table);
    const checkOverflow = () => {
      wrap.classList.toggle("has-overflow", wrap.scrollWidth > wrap.clientWidth + 1 && wrap.scrollLeft + wrap.clientWidth < wrap.scrollWidth - 1);
    };
    checkOverflow();
    wrap.addEventListener("scroll", checkOverflow, { passive: true });
    window.addEventListener("resize", checkOverflow);
  });

  // Progress bar
  const progressBar = document.createElement("div");
  progressBar.className = "qt-progress-bar";
  document.body.appendChild(progressBar);
  const updateProgress = () => {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    const docHeight = (document.documentElement.scrollHeight || document.body.scrollHeight) - window.innerHeight;
    const pct = docHeight > 0 ? Math.max(0, Math.min(100, (scrollTop / docHeight) * 100)) : 0;
    progressBar.style.width = pct + "%";
  };
  window.addEventListener("scroll", updateProgress, { passive: true });
  window.addEventListener("resize", updateProgress);
  updateProgress();

  // Highlight ONLY the standalone trading verdict words (BUY/SELL/HOLD) — not numbers or tickers.
  // This is intentionally minimal to avoid visual noise.
  const verdictPattern = /\\b(BUY|SELL|HOLD)\\b/g;
  const content = document.querySelector(".qt-content");
  if (content) {
    const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;
        if (/^(SCRIPT|STYLE|CODE|PRE|A|H1|H2|H3|H4|H5|H6)$/i.test(parent.tagName)) return NodeFilter.FILTER_REJECT;
        if (parent.closest(".qt-status, .qt-token, .qt-badge")) return NodeFilter.FILTER_REJECT;
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
      text.replace(verdictPattern, (match, _capture, offset) => {
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

  // Active TOC link via IntersectionObserver
  const links = Array.from(document.querySelectorAll("[data-toc] a"));
  const sections = links
    .map((link) => document.getElementById((link.getAttribute("href") || "").slice(1)))
    .filter(Boolean);
  if ("IntersectionObserver" in window && sections.length) {
    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      links.forEach((link) => {
        link.classList.toggle("active", link.getAttribute("href") === "#" + visible.target.id);
      });
    }, { rootMargin: "-80px 0px -65% 0px", threshold: [0.1, 0.4, 0.7] });
    sections.forEach((section) => observer.observe(section));
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

  const hasConfidence = meta.confidence !== undefined;
  const confidenceBlock = hasConfidence
    ? `<div>
        <div class="qt-confidence-label"><span>Confidence</span><span>${meta.confidence}%</span></div>
        <div class="qt-confidence-track"><div class="qt-confidence-fill" style="width:${meta.confidence}%"></div></div>
      </div>`
    : "";

  const reasonsHtml = reasons.length
    ? `<ul class="qt-reasons">${reasons.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}</ul>`
    : "";

  const metaRow = `
    <div class="qt-meta-row">
      <div class="qt-meta-item"><span class="qt-meta-item-label">Ticker</span><span class="qt-meta-item-value" data-ticker>${escapeHtml(meta.ticker)}</span></div>
      <div class="qt-meta-item"><span class="qt-meta-item-label">Date</span><span class="qt-meta-item-value">${escapeHtml(meta.date)}</span></div>
      <div class="qt-meta-item"><span class="qt-meta-item-label">Model</span><span class="qt-meta-item-value">${escapeHtml(meta.model)}</span></div>
    </div>`;

  return `<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>${buildQuantCss()}</style>
</head>
<body>
  <header class="qt-topbar">
    <button class="qt-menu-toggle" data-menu-toggle type="button" aria-label="Toggle table of contents">TOC</button>
    <span class="qt-led" aria-hidden="true"></span><span class="qt-live">LIVE</span>
    <span class="qt-field"><span class="qt-field-label">TICKER</span> <strong class="qt-mono">${escapeHtml(meta.ticker)}</strong></span>
    <span class="qt-sep">|</span>
    <span class="qt-field"><span class="qt-field-label">DATE</span> <strong class="qt-mono">${escapeHtml(meta.date)}</strong></span>
    <button class="qt-theme-toggle" data-theme-toggle type="button">Light</button>
  </header>
  <div class="qt-shell">
    <aside class="qt-sidebar" data-toc>
      <p class="qt-sidebar-title">// Contents</p>
      ${buildToc(enhanced.toc)}
    </aside>
    <main class="qt-main">
      <article class="qt-hero" data-watermark="${escapeHtml(meta.ticker)}">
        <div class="qt-hero-copy">
          <h1 class="qt-title">${escapeHtml(title)}</h1>
          <p class="qt-subtitle">Multi-agent trading research synthesis. Think like a professional trader.</p>
        </div>
        <div class="qt-verdict-card${hasConfidence ? " has-confidence" : ""}">
          <div>
            <div class="qt-verdict-label">Verdict</div>
            <span class="qt-badge ${verdictClass(meta.verdict)}">${escapeHtml(meta.verdict)}</span>
          </div>
          ${confidenceBlock}
          ${reasonsHtml}
          ${metaRow}
        </div>
      </article>
      <article class="qt-content">
        ${enhanced.html}
      </article>
    </main>
  </div>
  <script>${buildQuantScript()}</script>
</body>
</html>`;
}

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
  if (/fundamental|valuation|financial/.test(text)) return "fundamentals";
  if (/sentiment|social|reddit|stocktwits/.test(text)) return "sentiment";
  if (/news|macro|headline/.test(text)) return "news";
  if (/technical|indicator|macd|rsi/.test(text)) return "technical";
  if (/\bbull\b|bullish/.test(text)) return "bull";
  if (/\bbear\b|bearish/.test(text)) return "bear";
  if (/research manager|manager|synthesis/.test(text)) return "manager";
  if (/trader|trade plan|investment plan/.test(text)) return "trader";
  if (/risk|risky|neutral|safe|conservative|aggressive/.test(text)) return "risk";
  if (/portfolio|final|decision|verdict/.test(text)) return "final";
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
    default: "Report Section",
  };
  return labels[kind] ?? labels.default;
}
function sectionMarker(kind: string): string {
  return SECTION_MARKERS[kind] ?? SECTION_MARKERS.default;
}
function enhanceSections(contentHtml: string): { html: string; toc: TocItem[] } {
  const headingPattern = /<h2([^>]*)>([\s\S]*?)<\/h2>/gi;
  const matches = [...contentHtml.matchAll(headingPattern)];
  if (!matches.length) {
    return {
      html: `<section class="qt-section qt-section-default">${contentHtml}</section>`,
      toc: [],
    };
  }
  const seen = new Map<string, number>();
  const toc: TocItem[] = [];
  const parts: string[] = [];
  let cursor = 0;
  if ((matches[0]?.index ?? 0) > 0) {
    parts.push(`<section class="qt-section qt-section-intro">${contentHtml.slice(0, matches[0]!.index)}</section>`);
    cursor = matches[0]!.index!;
  }
  for (let i = 0; i < matches.length; i += 1) {
    const match = matches[i]!;
    const next = matches[i + 1];
    const start = match.index!;
    const end = next?.index ?? contentHtml.length;
    if (start < cursor) continue;
    const attrs = match[1] ?? "";
    const inner = match[2] ?? "";
    const title = stripTags(inner);
    const id = uniqueSlug(slugify(title), seen);
    const kind = classifySection(title);
    toc.push({ id, title });
    const sectionHtml = contentHtml
      .slice(start, end)
      .replace(match[0], `<h2${attrs} id="${id}"><span class="qt-section-kicker"><span class="qt-section-icon">${sectionMarker(kind)}</span>${sectionLabel(kind)}</span>${inner}</h2>`);
    parts.push(`<section class="qt-section qt-section-${kind}" data-section-kind="${kind}">${sectionHtml}</section>`);
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
  const ticker = overrides?.ticker || firstMatch(markdown, [
    /(?:ticker|symbol)\s*[:：]\s*`?([A-Z][A-Z0-9.\-]{0,9})`?/i,
    /\b(?:NYSE|NASDAQ|HKEX|SSE|SZSE)\s*[:：]\s*([A-Z0-9.\-]{1,10})\b/i,
  ]) || firstMatch(title, [/\b([A-Z][A-Z0-9.\-]{1,9})\b/]) || "Unknown";
  const date = overrides?.date || firstMatch(markdown, [
    /(?:analysis date|date)\s*[:：]\s*(\d{4}-\d{2}-\d{2})/i,
    /\b(\d{4}-\d{2}-\d{2})\b/,
  ]) || "Unknown";
  const model = overrides?.model || firstMatch(markdown, [
    /(?:model|llm|quick|deep)\s*[:：]\s*`?([A-Za-z0-9_.:/\- ]{2,80})`?/i,
  ]) || "Unknown";
  const finalSection = markdown.match(/(?:final|portfolio|decision|verdict)[\s\S]{0,2500}/i)?.[0] ?? markdown;
  const verdict = firstMatch(finalSection, [
    /\b(BUY|SELL|HOLD)\b/i,
  ]).toUpperCase() || "Unknown";
  const confidenceRaw = firstMatch(finalSection, [
    /confidence\s*[:：]?\s*(\d{1,3})\s*%/i,
    /(\d{1,3})\s*%\s*confidence/i,
  ]);
  const confidence = confidenceRaw ? Math.max(0, Math.min(100, Number(confidenceRaw))) : undefined;
  return { ticker, date, model, verdict, confidence };
}
function extractReasons(markdown: string): string[] {
  const finalSection = markdown.match(/(?:final|portfolio|decision|verdict)[\s\S]{0,3000}/i)?.[0] ?? "";
  if (!finalSection) return [];
  const bullets = [...finalSection.matchAll(/^\s*[-*]\s+(.{12,220})\s*$/gm)]
    .map((match) => match[1]?.trim() ?? "")
    .filter(Boolean);
  if (bullets.length) return bullets.slice(0, 4);
  const sentences = finalSection
    .replace(/[#*_`>]/g, "")
    .split(/(?<=[.!?。！？])\s+/)
    .map((sentence) => sentence.trim())
    .filter((sentence) => sentence.length >= 24 && !/\b(BUY|SELL|HOLD)\b$/i.test(sentence));
  return sentences.slice(0, 3);
}
function verdictClass(verdict: string): string {
  if (verdict === "BUY") return "buy";
  if (verdict === "SELL") return "sell";
  if (verdict === "HOLD") return "hold";
  return "unknown";
}
function buildToc(toc: TocItem[]): string {
  if (!toc.length) {
    return '<p class="qt-empty-toc">No H2 sections found.</p>';
  }
  return toc
    .map((item) => `<a href="#${item.id}">${escapeHtml(item.title)}</a>`)
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
  --text-2: #A0AEC0;
  --muted: #6B7280;
  --bull: #00D68F;
  --bear: #FF4757;
  --neutral: #FFB547;
  --ai: #4DA3FF;
  --ml: #B794F6;
  --grad: linear-gradient(135deg, #4DA3FF 0%, #B794F6 100%);
  --code-bg: #0B0F16;
  --line-soft: rgba(232,236,244,0.07);
  --panel-shadow: 0 1px 3px rgba(0,0,0,0.32), 0 12px 32px -16px rgba(0,0,0,0.5);
  --sans: "Geist", "Inter", system-ui, sans-serif;
  --mono: "JetBrains Mono", "IBM Plex Mono", monospace;
  --bg-canvas: var(--bg);
  --bg-card: var(--card);
  --bg-nested: var(--nested);
  --text-primary: var(--text);
  --text-secondary: var(--text-2);
  --text-muted: var(--muted);
  --gradient-hl: var(--grad);
  --elev-1: rgba(255,255,255,0.02);
  --elev-2: rgba(255,255,255,0.04);
  --elev-3: rgba(255,255,255,0.06);
  --hairline: color-mix(in srgb, var(--border) 70%, transparent);
  --ease-out-expo: cubic-bezier(0.22, 1, 0.36, 1);
  --bull-rgb: 0,214,143;
  --bear-rgb: 255,71,87;
  --neutral-rgb: 255,181,71;
  --ai-rgb: 77,163,255;
  --ml-rgb: 183,148,246;
  --noise: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.6 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/></svg>");
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
  --hairline: color-mix(in srgb, var(--border) 70%, transparent);
  --elev-1: rgba(15,23,42,0.015);
  --elev-2: rgba(15,23,42,0.03);
  --elev-3: rgba(15,23,42,0.05);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background:
    radial-gradient(circle at 8% -12%, rgba(77,163,255,0.10), transparent 28rem),
    radial-gradient(circle at 92% 4%, rgba(183,148,246,0.06), transparent 30rem),
    linear-gradient(180deg, rgba(255,255,255,0.02), transparent 22rem),
    var(--bg);
  color: var(--text);
  font-family: var(--sans);
  line-height: 1.7;
  font-variant-numeric: tabular-nums slashed-zero;
  font-feature-settings: "ss01", "cv11", "tnum", "zero";
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  position: relative;
}
body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background-image: var(--noise);
  background-size: 160px 160px;
  opacity: 0.015;
  mix-blend-mode: overlay;
}
[data-theme="light"] body::before { opacity: 0.025; mix-blend-mode: multiply; }
.qt-mono, code, pre, table, .qt-topbar, .qt-badge, .qt-meta, .qt-num,
.qt-content :is(td, th), .qt-reasons, .qt-confidence-label, .qt-section-kicker { font-family: var(--mono); }
.qt-progress-bar {
  position: fixed;
  top: 0; left: 0;
  height: 1px;
  width: 0%;
  background: var(--grad);
  z-index: 100;
  pointer-events: none;
  transition: width 80ms linear;
  box-shadow: 0 0 8px rgba(77,163,255,0.45);
}
.qt-topbar {
  position: sticky;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
  height: 48px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 max(18px, calc((100vw - 1200px) / 2 + 24px));
  background: color-mix(in srgb, var(--card) 82%, transparent);
  backdrop-filter: blur(18px) saturate(1.4);
  -webkit-backdrop-filter: blur(18px) saturate(1.4);
  border-bottom: 1px solid var(--hairline);
  color: var(--text-2);
  font-size: 13px;
  overflow-x: auto;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}
.qt-led {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: var(--bull);
  box-shadow: 0 0 0 0 rgba(0,214,143,0.55);
  animation: qtPulse 1.8s infinite;
}
@keyframes qtPulse {
  70% { box-shadow: 0 0 0 8px rgba(0,214,143,0); }
  100% { box-shadow: 0 0 0 0 rgba(0,214,143,0); }
}
.qt-theme-toggle, .qt-menu-toggle {
  border: 1px solid var(--hairline);
  background: var(--nested);
  color: var(--text);
  border-radius: 8px;
  min-height: 32px;
  padding: 0 12px;
  cursor: pointer;
  font-family: var(--mono);
  transition: transform 240ms var(--ease-out-expo), border-color 240ms var(--ease-out-expo), background 240ms var(--ease-out-expo);
}
.qt-theme-toggle:hover, .qt-menu-toggle:hover { border-color: var(--ai); background: color-mix(in srgb, var(--nested) 85%, var(--ai) 15%); }
.qt-theme-toggle:active, .qt-menu-toggle:active { transform: translateY(1px) scale(0.98); }
.qt-theme-toggle { margin-left: auto; }
.qt-sep { color: var(--muted); }
.qt-live { color: var(--text); font-weight: 600; letter-spacing: 0.06em; }
.qt-field { white-space: nowrap; }
.qt-field strong { color: var(--text); }
.qt-field-label { color: var(--muted); }
.qt-mobile-title { display: none; }
.qt-menu-toggle {
  justify-content: center;
  width: 42px;
  padding: 0;
}
.qt-menu-toggle { display: none; }
.qt-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 24px 40px;
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 24px;
  position: relative;
  z-index: 1;
}
.qt-sidebar {
  position: sticky;
  top: 72px;
  align-self: start;
  max-height: calc(100vh - 96px);
  overflow: auto;
  scrollbar-width: none;
  padding: 14px 12px 12px;
  border: 1px solid var(--hairline);
  border-radius: 12px;
  background:
    linear-gradient(180deg, var(--elev-2), var(--elev-1)),
    color-mix(in srgb, var(--card) 94%, transparent);
  box-shadow: var(--panel-shadow), inset 0 1px 0 rgba(255,255,255,0.04);
  position: sticky;
}
.qt-sidebar::-webkit-scrollbar { width: 0; height: 0; }
.qt-sidebar::before {
  content: "";
  position: absolute;
  top: 0; left: 0;
  height: 1px;
  width: var(--qt-scroll, 0%);
  background: var(--grad);
  border-radius: 999px;
  transition: width 80ms linear;
  box-shadow: 0 0 6px rgba(77,163,255,0.5);
}
.qt-sidebar-title {
  margin: 2px 4px 12px;
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-family: var(--mono);
}
.qt-sidebar-title::before {
  content: "// ";
  color: color-mix(in srgb, var(--ai) 70%, var(--muted));
  opacity: 0.85;
}
.qt-sidebar a {
  position: relative;
  display: block;
  padding: 9px 10px 9px 18px;
  margin: 2px 0;
  color: var(--text-2);
  text-decoration: none;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.35;
  transition: color 280ms var(--ease-out-expo), background 280ms var(--ease-out-expo), transform 280ms var(--ease-out-expo);
}
.qt-sidebar a::before {
  content: "";
  position: absolute;
  left: 6px;
  top: 50%;
  width: 4px;
  height: 4px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--text-2) 50%, transparent);
  transform: translateY(-50%) scale(0.9);
  transition: all 320ms var(--ease-out-expo);
}
.qt-sidebar a:hover {
  color: var(--ai);
  background: var(--elev-2);
  transform: translateX(2px);
}
.qt-sidebar a:hover::before { background: var(--ai); transform: translateY(-50%) scale(1); }
.qt-sidebar a.active {
  color: var(--ai);
  background: color-mix(in srgb, var(--nested) 75%, var(--ai) 6%);
}
.qt-sidebar a.active::before {
  background: var(--ai);
  width: 3px;
  height: 18px;
  border-radius: 2px;
  transform: translateY(-50%) scale(1);
  box-shadow: 0 0 8px rgba(77,163,255,0.6);
}
.qt-main { min-width: 0; }
.qt-hero {
  position: relative;
  margin-bottom: 24px;
  display: grid;
  grid-template-columns: minmax(0, 1.28fr) minmax(280px, 0.72fr);
  gap: 24px;
  align-items: stretch;
  padding: 24px;
  border: 1px solid var(--hairline);
  border-radius: 14px;
  overflow: hidden;
  background:
    radial-gradient(circle at 0% 0%, rgba(77,163,255,0.14), transparent 42%),
    linear-gradient(135deg, rgba(183,148,246,0.06), transparent 38%),
    linear-gradient(180deg, var(--elev-2), var(--elev-1)),
    var(--card);
  backdrop-filter: blur(20px) saturate(1.4);
  -webkit-backdrop-filter: blur(20px) saturate(1.4);
  box-shadow: var(--panel-shadow), inset 0 1px 0 rgba(255,255,255,0.06);
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
  opacity: 0.04;
  pointer-events: none;
  line-height: 1;
  white-space: nowrap;
}
.qt-hero-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  z-index: 1;
}
.qt-title {
  margin: 0;
  max-width: 820px;
  font-family: var(--sans);
  font-size: clamp(26px, 3.4vw, 42px);
  line-height: 1.06;
  letter-spacing: -0.022em;
  font-weight: 600;
}
.qt-subtitle { margin: 12px 0 0; color: var(--text-2); max-width: 58ch; line-height: 1.6; }
.qt-hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 22px;
}
.qt-chip {
  border: 1px solid var(--hairline);
  border-radius: 6px;
  color: var(--text-2);
  background: var(--elev-2);
  padding: 5px 9px;
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.02em;
  transition: border-color 240ms var(--ease-out-expo), color 240ms var(--ease-out-expo);
}
.qt-chip:hover { border-color: color-mix(in srgb, var(--ai) 50%, var(--border)); color: var(--text); }
.qt-verdict-card {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 18px;
  min-height: 100%;
  padding: 18px;
  border-radius: 12px;
  background:
    linear-gradient(180deg, var(--elev-3), var(--elev-1)),
    var(--nested);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
  isolation: isolate;
  z-index: 1;
}
.qt-verdict-card::before {
  content: "";
  position: absolute;
  inset: -1px;
  border-radius: 13px;
  padding: 1px;
  background: conic-gradient(
    from var(--qt-angle, 0deg),
    rgba(77,163,255,0.0) 0deg,
    rgba(77,163,255,0.55) 60deg,
    rgba(183,148,246,0.55) 120deg,
    rgba(77,163,255,0.0) 200deg,
    rgba(77,163,255,0.0) 360deg
  );
  -webkit-mask: linear-gradient(#000, #000) content-box, linear-gradient(#000, #000);
  -webkit-mask-composite: xor;
          mask-composite: exclude;
  animation: qtConic 8s linear infinite;
  pointer-events: none;
  z-index: -1;
}
@property --qt-angle {
  syntax: "<angle>";
  initial-value: 0deg;
  inherits: false;
}
@keyframes qtConic {
  to { --qt-angle: 360deg; }
}
.qt-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-width: 130px;
  padding: 12px 18px;
  border-radius: 8px;
  font-size: 32px;
  font-weight: 600;
  letter-spacing: 0.02em;
  font-feature-settings: "tnum", "ss01";
  transition: transform 280ms var(--ease-out-expo), box-shadow 280ms var(--ease-out-expo);
}
.qt-badge.buy { color: var(--bull); border: 1px solid color-mix(in srgb, var(--bull) 60%, transparent); background: rgba(0,214,143,0.12); box-shadow: 0 0 24px rgba(0,214,143,0.25), inset 0 0 0 1px rgba(0,214,143,0.18); }
.qt-badge.sell { color: var(--bear); border: 1px solid color-mix(in srgb, var(--bear) 60%, transparent); background: rgba(255,71,87,0.12); box-shadow: 0 0 24px rgba(255,71,87,0.25), inset 0 0 0 1px rgba(255,71,87,0.18); }
.qt-badge.hold { color: var(--neutral); border: 1px solid color-mix(in srgb, var(--neutral) 60%, transparent); background: rgba(255,181,71,0.12); box-shadow: 0 0 24px rgba(255,181,71,0.25), inset 0 0 0 1px rgba(255,181,71,0.18); }
.qt-badge.unknown { color: var(--text-2); border: 1px solid var(--hairline); background: var(--card); }
.qt-token {
  font-family: var(--mono);
  font-variant-numeric: tabular-nums slashed-zero;
  color: color-mix(in srgb, var(--text) 88%, var(--ai));
}
.qt-status {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 1px 7px;
  border: 1px solid var(--hairline);
  border-radius: 6px;
  font-family: var(--mono);
  font-size: 0.84em;
  line-height: 1.35;
  white-space: nowrap;
  letter-spacing: 0.02em;
}
.qt-status.buy, .qt-status.bullish, .qt-status.oversold {
  color: var(--bull);
  border-color: color-mix(in srgb, var(--bull) 55%, transparent);
  background: rgba(0,214,143,0.10);
  box-shadow: inset 0 0 0 1px rgba(0,214,143,0.30);
}
.qt-status.sell, .qt-status.bearish, .qt-status.overbought {
  color: var(--bear);
  border-color: color-mix(in srgb, var(--bear) 55%, transparent);
  background: rgba(255,71,87,0.10);
  box-shadow: inset 0 0 0 1px rgba(255,71,87,0.30);
}
.qt-status.hold, .qt-status.neutral {
  color: var(--neutral);
  border-color: color-mix(in srgb, var(--neutral) 55%, transparent);
  background: rgba(255,181,71,0.10);
  box-shadow: inset 0 0 0 1px rgba(255,181,71,0.30);
}
.qt-content .qt-status.buy,
.qt-content .qt-status.sell {
  animation: qtStatusGlow 1400ms var(--ease-out-expo) 1 both;
}
@keyframes qtStatusGlow {
  0%   { filter: brightness(1.6); box-shadow: inset 0 0 0 1px currentColor, 0 0 18px currentColor; }
  100% { filter: brightness(1);   box-shadow: inset 0 0 0 1px color-mix(in srgb, currentColor 30%, transparent), 0 0 0 currentColor; }
}
.qt-confidence-track {
  position: relative;
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(0,0,0,0.25), rgba(255,255,255,0.02)), var(--card);
  border: 1px solid var(--hairline);
  overflow: hidden;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.35);
}
.qt-confidence-fill {
  position: relative;
  height: 100%;
  border-radius: 999px;
  background: var(--grad);
  box-shadow: 0 0 12px rgba(77,163,255,0.55), inset 0 1px 0 rgba(255,255,255,0.4);
}
.qt-confidence-fill::after {
  content: "";
  position: absolute;
  inset: 0 0 50% 0;
  border-radius: 999px 999px 0 0;
  background: linear-gradient(180deg, rgba(255,255,255,0.32), transparent);
  pointer-events: none;
}
.qt-confidence-label {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  color: var(--text-2);
  font-size: 13px;
  letter-spacing: 0.02em;
}
.qt-reasons {
  margin: 4px 0 0;
  padding: 12px 0 0 18px;
  border-top: 1px solid var(--line-soft);
  color: var(--text-2);
  font-size: 12px;
  line-height: 1.6;
}
.qt-reasons li + li { margin-top: 6px; }
.qt-section {
  position: relative;
  margin: 14px 0;
  padding: 22px 22px 22px 24px;
  border: 1px solid var(--hairline);
  border-radius: 12px;
  background:
    linear-gradient(180deg, var(--elev-1), transparent 65%),
    color-mix(in srgb, var(--card) 98.5%, var(--ai));
  box-shadow: var(--panel-shadow);
  animation: qtRise 520ms var(--ease-out-expo) both;
  animation-delay: calc(min(var(--qt-index, 0), 8) * 50ms);
  transition: transform 320ms var(--ease-out-expo), border-color 320ms var(--ease-out-expo), box-shadow 320ms var(--ease-out-expo);
  overflow: hidden;
}
.qt-section::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, var(--ai), transparent 90%);
  opacity: 0.95;
}
.qt-section:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--ai) 40%, var(--hairline));
  box-shadow: var(--panel-shadow), 0 8px 24px -16px rgba(77,163,255,0.4);
}
@keyframes qtRise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.qt-section h2 {
  margin-top: 0;
  color: var(--text);
}
.qt-section-kicker {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  padding-bottom: 6px;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.qt-section-kicker::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 1px;
  background: linear-gradient(90deg, color-mix(in srgb, currentColor 60%, transparent), transparent);
  opacity: 0.5;
}
.qt-section-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 22px;
  border: 1px solid currentColor;
  border-radius: 6px;
  font-size: 10px;
  letter-spacing: 0.04em;
  background: color-mix(in srgb, currentColor 8%, transparent);
}
.qt-section-fundamentals::before, .qt-section-technical::before { background: linear-gradient(180deg, var(--ai), transparent 90%); }
.qt-section-sentiment::before, .qt-section-manager::before { background: linear-gradient(180deg, var(--ml), transparent 90%); }
.qt-section-news::before, .qt-section-risk::before { background: linear-gradient(180deg, var(--neutral), transparent 90%); }
.qt-section-bull::before { background: linear-gradient(180deg, var(--bull), transparent 90%); }
.qt-section-bear::before { background: linear-gradient(180deg, var(--bear), transparent 90%); }
.qt-section-bull { background: linear-gradient(180deg, var(--elev-1), transparent 65%), color-mix(in srgb, var(--card) 97.5%, var(--bull)); }
.qt-section-bear { background: linear-gradient(180deg, var(--elev-1), transparent 65%), color-mix(in srgb, var(--card) 97.5%, var(--bear)); }
.qt-section-trader {
  background:
    linear-gradient(var(--card), var(--card)) padding-box,
    var(--grad) border-box;
  border: 1px solid transparent;
}
.qt-section-trader::before { display: none; }
.qt-section-final::before { background: linear-gradient(180deg, var(--bull), transparent 90%); }
.qt-content :is(h1,h2,h3,h4,h5,h6) {
  font-family: var(--sans);
  line-height: 1.22;
  font-weight: 600;
}
.qt-content h1 { margin-top: 0; letter-spacing: -0.022em; }
.qt-content h2 { letter-spacing: -0.018em; }
.qt-content h3 { letter-spacing: -0.014em; }
.qt-content p {
  color: var(--text-2);
  line-height: 1.75;
  max-width: 72ch;
}
.qt-section > p:first-of-type::first-letter,
.qt-section h2 + p::first-letter {
  font-family: var(--sans);
  font-weight: 600;
  font-size: 2.4em;
  line-height: 0.95;
  float: left;
  padding: 4px 10px 0 0;
  color: var(--ai);
  background: linear-gradient(135deg, var(--ai), var(--ml));
  -webkit-background-clip: text;
          background-clip: text;
  -webkit-text-fill-color: transparent;
}
.qt-content a {
  color: var(--ai);
  text-decoration-color: color-mix(in srgb, var(--ai) 40%, transparent);
  text-underline-offset: 3px;
  transition: color 200ms var(--ease-out-expo), text-decoration-color 200ms var(--ease-out-expo);
}
.qt-content a:hover { text-decoration-color: var(--ai); }
.qt-content table {
  width: 100%;
  border-collapse: collapse;
  display: block;
  overflow-x: auto;
  border: 1px solid var(--hairline);
  border-radius: 10px;
  font-variant-numeric: tabular-nums slashed-zero;
}
.qt-content th {
  position: sticky;
  top: 48px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--nested) 92%, var(--ai) 6%), var(--nested));
  color: var(--text);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: 11px;
}
.qt-content th, .qt-content td {
  padding: 11px 13px;
  border-bottom-width: 0.5px;
  border-bottom-style: solid;
  border-bottom-color: var(--hairline);
  text-align: left;
  transition: background 220ms var(--ease-out-expo);
}
.qt-content td:not(:first-child), .qt-content th:not(:first-child) {
  text-align: right;
  font-variant-numeric: tabular-nums slashed-zero;
}
.qt-content tr:nth-child(even) td { background: var(--elev-1); }
.qt-content tbody tr:hover td { background: rgba(77,163,255,0.04); }
.qt-content blockquote {
  margin: 16px 0;
  padding: 14px 18px;
  border-left: 3px solid var(--ai);
  border-radius: 8px;
  background: linear-gradient(180deg, var(--elev-2), var(--elev-1)), var(--nested);
  color: var(--text-2);
  font-style: italic;
}
.qt-content code {
  background: var(--code-bg);
  color: var(--text);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
  border: 1px solid var(--hairline);
}
.qt-content pre {
  position: relative;
  overflow-x: auto;
  padding: 38px 22px 20px;
  border-radius: 12px;
  background: var(--code-bg);
  border: 1px solid var(--hairline);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.03), inset 0 0 0 1px rgba(0,0,0,0.18);
}
.qt-content pre::before {
  content: "";
  position: absolute;
  top: 14px;
  left: 16px;
  width: 12px;
  height: 12px;
  border-radius: 999px;
  background: #B34540;
  box-shadow:
    18px 0 0 #B28522,
    36px 0 0 #1F8C2D;
  opacity: 0.85;
}
.qt-content pre::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: 12px;
  box-shadow: inset 0 0 30px rgba(0,0,0,0.18);
}
.qt-content pre code { padding: 0; background: transparent; border: 0; }
.qt-content img { max-width: 100%; border-radius: 12px; border: 1px solid var(--hairline); }
.qt-empty-toc { color: var(--muted); font-size: 13px; }
.qt-section-risk ul {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  padding-left: 0;
  list-style: none;
}
.qt-section-risk li {
  padding: 13px;
  border: 1px solid var(--hairline);
  border-radius: 8px;
  background: linear-gradient(180deg, var(--elev-2), var(--elev-1)), rgba(255,255,255,0.01);
  transition: border-color 240ms var(--ease-out-expo), transform 240ms var(--ease-out-expo);
}
.qt-section-risk li:hover { border-color: color-mix(in srgb, var(--neutral) 45%, var(--hairline)); transform: translateY(-1px); }
@media (max-width: 768px) {
  .qt-menu-toggle { display: inline-flex; align-items: center; }
  .qt-mobile-title { display: inline; }
  .qt-field.optional, .qt-sep.optional { display: none; }
  .qt-shell { grid-template-columns: 1fr; padding: 16px 16px 28px; }
  .qt-sidebar {
    display: none;
    position: fixed;
    z-index: 25;
    inset: 56px 16px auto;
    max-height: 70vh;
  }
  .qt-sidebar.open { display: block; }
  .qt-hero { grid-template-columns: 1fr; padding: 18px; }
  .qt-hero::before { font-size: 140px; bottom: -22%; }
  .qt-section { padding: 16px; }
  .qt-section-risk ul { grid-template-columns: 1fr; }
  .qt-badge { font-size: 26px; min-width: 110px; padding: 10px 16px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
    scroll-behavior: auto !important;
  }
  .qt-verdict-card::before { animation: none; }
  .qt-led { animation: none; }
}
@media print {
  @page { margin: 18mm; }
  .qt-topbar, .qt-sidebar, .qt-menu-toggle, .qt-theme-toggle, .qt-progress-bar { display: none !important; }
  body {
    background: #fff;
    color: #111;
    font-family: Georgia, "Times New Roman", serif;
  }
  body::before { display: none; }
  .qt-shell { display: block; max-width: none; padding: 0; }
  .qt-hero, .qt-section {
    break-inside: avoid;
    box-shadow: none;
    background: #fff !important;
    border-color: #ccc !important;
  }
  .qt-section { page-break-after: always; }
  .qt-section:last-child { page-break-after: auto; }
  .qt-hero::before { display: none; }
  .qt-content a { color: #111; text-decoration: underline; }
  .qt-content a::after {
    content: " (" attr(href) ")";
    font-size: 0.85em;
    color: #555;
    word-break: break-all;
  }
  .qt-badge { box-shadow: none !important; }
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
  if (hero) {
    const tickerChip = document.querySelector(".qt-field strong.qt-mono");
    const watermark = tickerChip ? tickerChip.textContent : "";
    if (watermark) hero.setAttribute("data-watermark", watermark);
  }
  const progressBar = document.createElement("div");
  progressBar.className = "qt-progress-bar";
  document.body.appendChild(progressBar);
  const updateProgress = () => {
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    const docHeight = (document.documentElement.scrollHeight || document.body.scrollHeight) - window.innerHeight;
    const pct = docHeight > 0 ? Math.max(0, Math.min(100, (scrollTop / docHeight) * 100)) : 0;
    progressBar.style.width = pct + "%";
    if (menu) menu.style.setProperty("--qt-scroll", pct + "%");
  };
  window.addEventListener("scroll", updateProgress, { passive: true });
  window.addEventListener("resize", updateProgress);
  updateProgress();
  const tokenPattern = /(\\$?\\b\\d{1,4}(?:[,.:/-]\\d{1,4})*(?:\\.\\d+)?%?\\b|\\b[A-Z]{1,5}(?:\\.[A-Z])?\\b|\\bBUY\\b|\\bSELL\\b|\\bHOLD\\b|\\bBULLISH\\b|\\bBEARISH\\b|\\bNEUTRAL\\b|\\bOVERSOLD\\b|\\bOVERBOUGHT\\b)/g;
  const statusWords = new Set(["BUY", "SELL", "HOLD", "BULLISH", "BEARISH", "NEUTRAL", "OVERSOLD", "OVERBOUGHT"]);
  const content = document.querySelector(".qt-content");
  if (content) {
    const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent || /^(SCRIPT|STYLE|CODE|PRE|A)$/i.test(parent.tagName)) return NodeFilter.FILTER_REJECT;
        tokenPattern.lastIndex = 0;
        return tokenPattern.test(node.nodeValue || "") ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      const fragment = document.createDocumentFragment();
      const text = node.nodeValue || "";
      let lastIndex = 0;
      text.replace(tokenPattern, (match, _capture, offset) => {
        fragment.appendChild(document.createTextNode(text.slice(lastIndex, offset)));
        const span = document.createElement("span");
        const upper = match.toUpperCase();
        span.className = statusWords.has(upper) ? "qt-status " + upper.toLowerCase() : "qt-token";
        span.textContent = match;
        fragment.appendChild(span);
        lastIndex = offset + match.length;
        return match;
      });
      fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
      node.parentNode && node.parentNode.replaceChild(fragment, node);
    });
  }
  const links = Array.from(document.querySelectorAll("[data-toc] a"));
  const sections = links
    .map((link) => document.getElementById((link.getAttribute("href") || "").slice(1)))
    .filter(Boolean);
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      links.forEach((link) => {
        link.classList.toggle("active", link.getAttribute("href") === "#" + visible.target.id);
      });
    }, { rootMargin: "-96px 0px -60% 0px", threshold: [0.1, 0.4, 0.7] });
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
  const confidenceHtml = meta.confidence === undefined
    ? '<div class="qt-confidence-label"><span>Confidence</span><span class="qt-mono">Unknown</span></div>'
    : `<div class="qt-confidence-label"><span>Confidence</span><span class="qt-mono">${meta.confidence}%</span></div><div class="qt-confidence-track"><div class="qt-confidence-fill" style="width:${meta.confidence}%"></div></div>`;
  const reasonsHtml = reasons.length
    ? `<ul class="qt-reasons">${reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>`
    : "";
  return `<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>${buildQuantCss()}</style>
</head>
<body>
  <header class="qt-topbar">
    <button class="qt-menu-toggle" data-menu-toggle type="button" aria-label="Open table of contents">TOC</button>
    <span class="qt-led" aria-hidden="true"></span><span class="qt-live">LIVE</span>
    <span class="qt-field"><span class="qt-field-label">TICKER</span> <strong class="qt-mono">${escapeHtml(meta.ticker)}</strong></span>
    <span class="qt-sep">|</span>
    <span class="qt-field"><span class="qt-field-label">DATE</span> <strong class="qt-mono">${escapeHtml(meta.date)}</strong></span>
    <span class="qt-sep optional">|</span>
    <span class="qt-field optional"><span class="qt-field-label">MODEL</span> <strong class="qt-mono">${escapeHtml(meta.model)}</strong></span>
    <button class="qt-theme-toggle" data-theme-toggle type="button">Light</button>
  </header>
  <div class="qt-shell">
    <aside class="qt-sidebar" data-toc>
      <p class="qt-sidebar-title">Contents</p>
      ${buildToc(enhanced.toc)}
    </aside>
    <main class="qt-main">
      <article class="qt-hero" data-watermark="${escapeHtml(meta.ticker)}">
        <div class="qt-hero-copy">
          <div>
            <h1 class="qt-title">${escapeHtml(title)}</h1>
            <p class="qt-subtitle">Think like a professional trader. Render like an AI.</p>
          </div>
          <div class="qt-hero-meta" aria-label="Report metadata">
            <span class="qt-chip">TICKER ${escapeHtml(meta.ticker)}</span>
            <span class="qt-chip">DATE ${escapeHtml(meta.date)}</span>
            <span class="qt-chip">MODEL ${escapeHtml(meta.model)}</span>
          </div>
        </div>
        <div class="qt-verdict-card">
          <span class="qt-badge ${verdictClass(meta.verdict)}">${escapeHtml(meta.verdict)}</span>
          <div>${confidenceHtml}${reasonsHtml}</div>
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

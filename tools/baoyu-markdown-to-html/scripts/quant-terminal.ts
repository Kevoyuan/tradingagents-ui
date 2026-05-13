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
      .replace(match[0], `<h2${attrs} id="${id}"><span class="qt-section-kicker">${sectionLabel(kind)}</span>${inner}</h2>`);
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

function extractMeta(markdown: string, title: string): QuantMeta {
  const ticker = firstMatch(markdown, [
    /(?:ticker|symbol)\s*[:：]\s*`?([A-Z][A-Z0-9.\-]{0,9})`?/i,
    /\b(?:NYSE|NASDAQ|HKEX|SSE|SZSE)\s*[:：]\s*([A-Z0-9.\-]{1,10})\b/i,
  ]) || firstMatch(title, [/\b([A-Z][A-Z0-9.\-]{1,9})\b/]) || "Unknown";

  const date = firstMatch(markdown, [
    /(?:analysis date|date)\s*[:：]\s*(\d{4}-\d{2}-\d{2})/i,
    /\b(\d{4}-\d{2}-\d{2})\b/,
  ]) || "Unknown";

  const model = firstMatch(markdown, [
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
  --bg-canvas: #0A0E1A;
  --bg-card: #131825;
  --bg-nested: #1C2333;
  --border: #2A3142;
  --text-primary: #E8ECF4;
  --text-secondary: #A0AEC0;
  --text-muted: #6B7280;
  --bull: #00D68F;
  --bear: #FF4757;
  --neutral: #FFB547;
  --ai: #4DA3FF;
  --ml: #B794F6;
  --gradient-hl: linear-gradient(135deg, #4DA3FF 0%, #B794F6 100%);
  --code-bg: #0F1419;
}
[data-theme="light"] {
  --bg-canvas: #FAFBFC;
  --bg-card: #FFFFFF;
  --bg-nested: #F1F5F9;
  --border: #E5E7EB;
  --text-primary: #0F172A;
  --text-secondary: #475569;
  --text-muted: #64748B;
  --code-bg: #E2E8F0;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--bg-canvas);
  color: var(--text-primary);
  font-family: "Inter", system-ui, sans-serif;
  line-height: 1.7;
}
.qt-mono, code, pre, table, .qt-topbar, .qt-badge, .qt-meta, .qt-num,
.qt-content :is(td, th) { font-family: "JetBrains Mono", "IBM Plex Mono", monospace; }
.qt-topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
  height: 48px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 18px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 13px;
  overflow-x: auto;
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
  border: 1px solid var(--border);
  background: var(--bg-nested);
  color: var(--text-primary);
  border-radius: 8px;
  min-height: 32px;
  padding: 0 10px;
  cursor: pointer;
}
.qt-menu-toggle { display: none; }
.qt-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 72px 24px 40px;
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 24px;
}
.qt-sidebar {
  position: sticky;
  top: 72px;
  align-self: start;
  max-height: calc(100vh - 96px);
  overflow: auto;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-card);
}
.qt-sidebar-title {
  margin: 0 0 12px;
  color: var(--text-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-family: "JetBrains Mono", monospace;
}
.qt-sidebar a {
  display: block;
  padding: 8px 10px;
  margin: 2px 0;
  color: var(--text-secondary);
  text-decoration: none;
  border-left: 3px solid transparent;
  border-radius: 6px;
}
.qt-sidebar a:hover {
  color: var(--ai);
  border-left-color: var(--ai);
  background: var(--bg-nested);
}
.qt-main { min-width: 0; }
.qt-hero {
  margin-bottom: 24px;
  padding: 24px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-card);
}
.qt-title {
  margin: 0;
  font-size: clamp(28px, 4vw, 44px);
  line-height: 1.12;
  letter-spacing: -0.02em;
}
.qt-subtitle { margin: 10px 0 0; color: var(--text-secondary); }
.qt-verdict-card {
  display: grid;
  grid-template-columns: auto minmax(160px, 1fr);
  gap: 16px;
  align-items: center;
  margin-top: 20px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-nested);
}
.qt-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 116px;
  padding: 10px 16px;
  border-radius: 12px;
  font-size: 24px;
  font-weight: 700;
}
.qt-badge.buy { color: var(--bull); border: 1px solid var(--bull); background: rgba(0,214,143,0.15); }
.qt-badge.sell { color: var(--bear); border: 1px solid var(--bear); background: rgba(255,71,87,0.15); }
.qt-badge.hold { color: var(--neutral); border: 1px solid var(--neutral); background: rgba(255,181,71,0.15); }
.qt-badge.unknown { color: var(--text-secondary); border: 1px solid var(--border); background: var(--bg-card); }
.qt-confidence-track {
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  overflow: hidden;
}
.qt-confidence-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--gradient-hl);
}
.qt-confidence-label {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}
.qt-section {
  margin: 16px 0;
  padding: 20px;
  border: 1px solid var(--border);
  border-left: 3px solid var(--ai);
  border-radius: 12px;
  background: var(--bg-card);
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}
.qt-section h2 {
  margin-top: 0;
  color: var(--text-primary);
}
.qt-section-kicker {
  display: block;
  margin-bottom: 4px;
  color: var(--text-muted);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-family: "JetBrains Mono", monospace;
}
.qt-section-fundamentals, .qt-section-technical { border-left-color: var(--ai); }
.qt-section-sentiment, .qt-section-manager { border-left-color: var(--ml); }
.qt-section-news, .qt-section-risk { border-left-color: var(--neutral); }
.qt-section-bull { border-left-color: var(--bull); background: color-mix(in srgb, var(--bg-card) 95%, var(--bull)); }
.qt-section-bear { border-left-color: var(--bear); background: color-mix(in srgb, var(--bg-card) 95%, var(--bear)); }
.qt-section-trader {
  border-left-color: transparent;
  background:
    linear-gradient(var(--bg-card), var(--bg-card)) padding-box,
    var(--gradient-hl) border-box;
  border: 1px solid transparent;
}
.qt-section-final { border-left-color: var(--bull); }
.qt-content :is(h1,h2,h3,h4,h5,h6) {
  font-family: "Inter", "Space Grotesk", system-ui, sans-serif;
  letter-spacing: -0.02em;
  line-height: 1.25;
}
.qt-content h1 { margin-top: 0; }
.qt-content p { color: var(--text-secondary); }
.qt-content a { color: var(--ai); }
.qt-content table {
  width: 100%;
  border-collapse: collapse;
  display: block;
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
}
.qt-content th {
  position: sticky;
  top: 48px;
  background: var(--bg-nested);
  color: var(--text-primary);
}
.qt-content th, .qt-content td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  text-align: left;
}
.qt-content tr:nth-child(even) td { background: rgba(255,255,255,0.02); }
.qt-content blockquote {
  margin: 16px 0;
  padding: 12px 16px;
  border-left: 3px solid var(--ai);
  border-radius: 8px;
  background: var(--bg-nested);
  color: var(--text-secondary);
}
.qt-content code {
  background: var(--code-bg);
  color: var(--text-primary);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}
.qt-content pre {
  overflow-x: auto;
  padding: 16px;
  border-radius: 12px;
  background: var(--code-bg);
  border: 1px solid var(--border);
}
.qt-content pre code { padding: 0; background: transparent; }
.qt-content img { max-width: 100%; border-radius: 12px; }
.qt-empty-toc { color: var(--text-muted); font-size: 13px; }
@media (max-width: 768px) {
  .qt-menu-toggle { display: inline-flex; align-items: center; }
  .qt-shell { grid-template-columns: 1fr; padding: 64px 16px 28px; }
  .qt-sidebar {
    display: none;
    position: fixed;
    z-index: 25;
    inset: 56px 16px auto;
    max-height: 70vh;
  }
  .qt-sidebar.open { display: block; }
  .qt-verdict-card { grid-template-columns: 1fr; }
}
@media print {
  .qt-topbar, .qt-sidebar, .qt-menu-toggle, .qt-theme-toggle { display: none !important; }
  body { background: #fff; color: #111; }
  .qt-shell { display: block; max-width: none; padding: 0; }
  .qt-section, .qt-hero { break-inside: avoid; box-shadow: none; }
}
`;
}

function buildQuantScript(): string {
  return `
(function () {
  const root = document.documentElement;
  const saved = localStorage.getItem("qt-theme") || "dark";
  root.setAttribute("data-theme", saved);
  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
      root.setAttribute("data-theme", next);
      localStorage.setItem("qt-theme", next);
    });
  });
  const menu = document.querySelector("[data-toc]");
  document.querySelectorAll("[data-menu-toggle]").forEach((button) => {
    button.addEventListener("click", () => menu && menu.classList.toggle("open"));
  });
  document.querySelectorAll("[data-toc] a").forEach((link) => {
    link.addEventListener("click", () => menu && menu.classList.remove("open"));
  });
}());
`;
}

export async function renderQuantTerminalDocument(
  markdown: string,
  title: string,
  options?: Partial<Omit<CliOptions, "inputPath">>,
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
  const meta = extractMeta(markdown, title);
  const confidenceHtml = meta.confidence === undefined
    ? '<div class="qt-confidence-label"><span>Confidence</span><span class="qt-mono">Unknown</span></div>'
    : `<div class="qt-confidence-label"><span>Confidence</span><span class="qt-mono">${meta.confidence}%</span></div><div class="qt-confidence-track"><div class="qt-confidence-fill" style="width:${meta.confidence}%"></div></div>`;

  return `<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet">
  <style>${buildQuantCss()}</style>
</head>
<body>
  <header class="qt-topbar">
    <button class="qt-menu-toggle" data-menu-toggle type="button">TOC</button>
    <span class="qt-led" aria-hidden="true"></span><span>LIVE</span>
    <span>TICKER: <strong class="qt-mono">${escapeHtml(meta.ticker)}</strong></span>
    <span>|</span>
    <span>${escapeHtml(meta.date)}</span>
    <span>|</span>
    <span>MODEL: <strong class="qt-mono">${escapeHtml(meta.model)}</strong></span>
    <button class="qt-theme-toggle" data-theme-toggle type="button">Theme</button>
  </header>
  <div class="qt-shell">
    <aside class="qt-sidebar" data-toc>
      <p class="qt-sidebar-title">Report Content</p>
      ${buildToc(enhanced.toc)}
    </aside>
    <main class="qt-main">
      <article class="qt-hero">
        <h1 class="qt-title">${escapeHtml(title)}</h1>
        <p class="qt-subtitle">Think like a professional trader. Render like an AI.</p>
        <div class="qt-verdict-card">
          <span class="qt-badge ${verdictClass(meta.verdict)}">${escapeHtml(meta.verdict)}</span>
          <div>${confidenceHtml}</div>
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

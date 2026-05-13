# Prompt: Convert TradingAgents Markdown Report -> Styled HTML

This backend prompt documents the intended TradingAgents HTML report target for
the vendored `tools/baoyu-markdown-to-html` converter integration.

The converter should render TradingAgents Markdown reports as a single
self-contained HTML file using a "Quant Terminal" theme:

- Terminal-style top bar with ticker, date, model name, and connection LED
- Sticky desktop table of contents and mobile drawer
- Prominent BUY / SELL / HOLD verdict card with confidence bar
- Dark default theme with light mode toggle persisted to localStorage
- Semantic cards for Fundamentals, Sentiment, News, Technicals, Bull/Bear debate,
  Research Manager, Trader Plan, Risk Management, and Final Decision sections
- Monospace styling for all prices, percentages, tickers, timestamps, IDs, and code
- Responsive and print-friendly output
- No external JavaScript libraries; inline CSS; semantic HTML5

Hard rules:

- Faithfully preserve all Markdown content; do not summarize or omit sections
- Use CSS variables for all colors
- Keep border radius at 16px or below
- Avoid heavy shadows
- Preserve WCAG AA contrast

Tagline:

> Think like a professional trader. Render like an AI.

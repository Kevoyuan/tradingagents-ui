"""Centralized CSS for TradingAgents Streamlit UI."""

CUSTOM_CSS = """
<style>
/* Modern typography */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

.stApp {
    font-family: 'Inter', sans-serif;
}

/* Premium Noise Texture Overlay */
.stApp::before {
    content: "";
    position: fixed;
    top: 0; left: 0; width: 100%; height: 100%;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
    opacity: 0.03;
    pointer-events: none;
    z-index: 9999;
    mix-blend-mode: overlay;
}

/* Sidebar Premium Styling */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #161b22 100%) !important;
    border-right: 1px solid rgba(0, 255, 136, 0.15) !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #00ff88 !important;
    font-family: 'JetBrains Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

[data-testid="stSidebar"] label {
    color: #8a8f98 !important; /* Linear ink-subtle */
    font-size: 13px;
    font-weight: 500;
}

h1, h2, h3, h4, h5, h6 {
    letter-spacing: -0.02em !important; /* Linear negative tracking */
    color: #f7f8f8 !important; /* Linear ink */
}

/* Sidebar Buttons */
[data-testid="stSidebar"] button[kind="secondary"] {
    background: #0f1011 !important; /* Linear surface-1 */
    border: 1px solid #23252a !important; /* Linear hairline */
    color: #f7f8f8 !important; /* Linear ink */
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    font-weight: 500;
    border-radius: 8px !important;
    padding: 8px 14px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: #141516 !important; /* Linear surface-2 */
    border-color: #34343a !important; /* Linear hairline-strong */
    color: #ffffff !important;
}
[data-testid="stSidebar"] button[kind="secondary"]:active {
    transform: translateY(1px);
}

/* Primary Buttons (Run Analysis) */
.stButton button[kind="primary"] {
    background: #00ff88 !important; /* Using our brand color instead of Linear's primary */
    border: 1px solid #00ff88 !important;
    color: #010102 !important; /* Linear canvas for high contrast */
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    font-size: 14px;
    border-radius: 8px !important;
    padding: 8px 14px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 16px rgba(0, 255, 136, 0.15), inset 0 1px 1px rgba(255, 255, 255, 0.4) !important;
}
.stButton button[kind="primary"]:hover {
    background: #33ff9f !important;
    border-color: #33ff9f !important;
    box-shadow: 0 6px 20px rgba(0, 255, 136, 0.25), inset 0 1px 1px rgba(255, 255, 255, 0.5) !important;
    transform: translateY(-1px);
}
.stButton button[kind="primary"]:active {
    transform: translateY(1px);
    box-shadow: none !important;
}
.stButton button[kind="primary"]:disabled {
    background: rgba(0, 255, 136, 0.1) !important;
    border-color: rgba(0, 255, 136, 0.2) !important;
    color: rgba(255, 255, 255, 0.3) !important;
    box-shadow: none !important;
    transform: none;
    cursor: not-allowed;
}

/* Global Inputs and Selects (Linear Style) */
div[data-baseweb="select"] > div,
div[data-baseweb="base-input"],
textarea {
    background-color: #0f1011 !important; /* Linear surface-1 */
    border: 1px solid #23252a !important; /* Linear hairline */
    border-radius: 8px !important;
    color: #f7f8f8 !important; /* Linear ink */
    transition: all 0.2s ease;
}
div[data-baseweb="select"] > div:hover,
div[data-baseweb="base-input"]:hover,
textarea:hover {
    border-color: #34343a !important; /* Linear hairline-strong */
    background-color: #141516 !important; /* Linear surface-2 */
}
div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="base-input"]:focus-within,
textarea:focus {
    border-color: #00ff88 !important;
    box-shadow: 0 0 0 2px rgba(0, 255, 136, 0.2) !important; /* Linear-style focus ring */
}
/* Ensure inner inputs have correct colors without overriding wrappers */
input, textarea {
    color: #f7f8f8 !important;
}
/* Crucial: Prevent inner input of select from showing a box */
div[data-baseweb="select"] input {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

/* Expanders in Sidebar */
[data-testid="stSidebar"] [data-testid="stExpander"] {
    border-color: #23252a !important; /* Linear hairline */
    background: #0f1011 !important; /* Linear surface-1 */
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
    background: #141516 !important; /* Linear surface-2 */
    color: #f7f8f8 !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
    fill: #8a8f98 !important;
}

/* Adjusted padding to prevent header overlap */
.block-container { padding-top: 3.5rem; padding-bottom: 1rem; }

/* Linear-style Tabs */
.stTabs { margin-top: 0.5rem; }
.stTabs [data-baseweb="tab-list"] { 
    overflow: visible !important;
    background-color: transparent !important;
    border-bottom: 1px solid #23252a !important; /* Linear hairline */
    gap: 16px;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    padding: 10px 4px !important;
    margin-right: 8px;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    border-bottom-color: #00ff88 !important;
}
button[data-baseweb="tab"] p {
    color: #8a8f98 !important; /* Linear ink-subtle */
    font-size: 14px !important;
    font-weight: 500 !important;
}
button[data-baseweb="tab"][aria-selected="true"] p {
    color: #f7f8f8 !important; /* Linear ink */
    font-weight: 600 !important;
}
button[data-baseweb="tab"]:hover p {
    color: #d0d6e0 !important; /* Linear ink-muted */
}

/* Panel design - Linear Surface-1 Refraction */
.panel {
    border: 1px solid #23252a !important; /* Linear hairline */
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    background: #0f1011 !important; /* Linear surface-1 */
    box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.05); /* Subtle top pixel */
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
}
.panel::after {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0, 255, 136, 0.15), transparent);
}
.panel:hover {
    border-color: #34343a !important; /* Linear hairline-strong */
    box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.08);
}
.top-panel {
    height: 493px;
}
.messages-panel {
    height: 493px;
    display: flex;
    flex-direction: column;
}
.panel-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px; /* Linear eyebrow */
    font-weight: 500;
    color: #8a8f98; /* Linear ink-subtle */
    text-transform: uppercase;
    letter-spacing: 0.04em; /* Linear positive tracking for eyebrow */
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.panel-title::before {
    content: "";
    display: inline-block;
    width: 6px;
    height: 6px;
    background: #00ff88;
    border-radius: 50%;
    box-shadow: 0 0 8px rgba(0, 255, 136, 0.6);
}

/* Agent status table */
.agent-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; font-family: 'Inter', sans-serif; }
.agent-table td { padding: 4px 8px; vertical-align: middle; }
.agent-table .team-name {
    color: #8a8f98; /* Linear ink-subtle */
    font-weight: 500;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    white-space: nowrap;
}
.agent-table .agent-name { color: #c9d1d9; padding-left: 12px; }

/* Status Badges */
.status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 9999px; /* Vercel Pill */
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.05em;
    border: 1px solid transparent;
}
.status-completed { background: rgba(0, 255, 136, 0.1); color: #00ff88; border-color: rgba(0, 255, 136, 0.2); box-shadow: 0 0 8px rgba(0, 255, 136, 0.1); }
.status-in_progress { background: rgba(255, 170, 0, 0.1); color: #ffaa00; border-color: rgba(255, 170, 0, 0.2); animation: pulse-badge 2s infinite; }
.status-pending { background: rgba(138, 143, 152, 0.1); color: #8a8f98; border-color: rgba(138, 143, 152, 0.2); }
.status-error { background: rgba(255, 68, 68, 0.1); color: #ff4444; border-color: rgba(255, 68, 68, 0.2); }

@keyframes pulse-badge {
    0% { box-shadow: 0 0 0 0 rgba(255, 170, 0, 0.3); }
    70% { box-shadow: 0 0 0 4px rgba(255, 170, 0, 0); }
    100% { box-shadow: 0 0 0 0 rgba(255, 170, 0, 0); }
}

/* Scanning Line Effect */
@keyframes scanning {
    0% { transform: translateY(-100%); }
    100% { transform: translateY(1000%); }
}
.scanning-line {
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, rgba(0, 255, 136, 0.1), transparent);
    animation: scanning 10s linear infinite;
    pointer-events: none;
    z-index: 1;
}

.team-sep td { border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding: 4px 0; }

/* Messages table */
.messages-scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-right: 4px;
    scrollbar-color: rgba(0, 255, 136, 0.35) rgba(255, 255, 255, 0.04);
    scrollbar-width: thin;
}
.messages-scroll::-webkit-scrollbar { width: 8px; }
.messages-scroll::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.04);
    border-radius: 999px;
}
.messages-scroll::-webkit-scrollbar-thumb {
    background: rgba(0, 255, 136, 0.35);
    border-radius: 999px;
}
.messages-scroll::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 255, 136, 0.55);
}
.msg-table { width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; }
.msg-table td { padding: 6px 8px; border-bottom: 1px solid #141516; vertical-align: top; }
.msg-table tr:hover { background: #141516; }
.msg-table .msg-time { color: #8a8f98; white-space: nowrap; width: 75px; opacity: 0.8; }
.msg-table .msg-type { width: 70px; text-align: center; }

/* Message Type Micro Badges */
.msg-type-badge {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 9px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border: 1px solid transparent;
}
.msg-type-Agent { background: rgba(0, 255, 136, 0.1); color: #00ff88; border-color: rgba(0, 255, 136, 0.2); }
.msg-type-System { background: rgba(210, 153, 34, 0.1); color: #d29922; border-color: rgba(210, 153, 34, 0.2); }
.msg-type-Data { background: rgba(163, 113, 247, 0.1); color: #a371f7; border-color: rgba(163, 113, 247, 0.2); }
.msg-type-Tool { background: rgba(255, 123, 114, 0.1); color: #ff7b72; border-color: rgba(255, 123, 114, 0.2); }
.msg-type-User { background: rgba(88, 166, 255, 0.1); color: #58a6ff; border-color: rgba(88, 166, 255, 0.2); }
.msg-table .msg-content { color: #c9d1d9; word-break: break-word; line-height: 1.5; }

/* Stats bar - Vercel / Linear Style Refinement */
.stats-bar {
    display: flex; gap: 1rem; justify-content: center;
    font-size: 0.75rem; color: #8a8f98; padding: 15px 0;
    border-top: 1px solid #23252a; /* Linear hairline */
    margin-top: 2rem;
    font-family: 'JetBrains Mono', monospace;
    flex-wrap: wrap;
}
.stats-bar span {
    white-space: nowrap;
    background: rgba(13, 17, 23, 0.6); /* Translucent Glass */
    padding: 4px 12px;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.05);
}
.stats-bar span b {
    color: #00ff88; /* Restore neon green metrics */
    font-weight: 600;
}
.stats-bar b { color: #00ff88; font-weight: 500; }

/* Report section */
.report-section {
    padding: 1.25rem; font-size: 0.9rem;
    background: rgba(0,0,0,0.25); border-radius: 6px;
    border-left: 3px solid #00ff88;
    margin-top: 0.5rem;
    color: #e6edf3;
    line-height: 1.6;
}
.report-section h1, .report-section h2, .report-section h3 {
    color: #00ff88;
    margin-top: 1.5rem;
    margin-bottom: 1rem;
}
/* Report layout with TOC */
.report-container { display: flex; gap: 1.5rem; }
/* Report navigation */
.report-nav {
    margin-top: 0.5rem;
    padding-right: 8px;
}
.report-nav-item {
    display: block;
    padding: 6px 12px;
    margin: 2px 0;
    color: #8b949e;
    text-decoration: none;
    font-size: 0.85rem;
    border-radius: 6px;
    transition: all 0.15s ease;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.4;
}
.report-nav-item:hover {
    color: #c9d1d9;
    background: rgba(255, 255, 255, 0.05);
}
.report-nav-active {
    background: rgba(0, 255, 136, 0.1);
    color: #00ff88 !important;
    font-weight: 600;
}
/* Hierarchical styles */
.nav-level-1 {
    color: #e6edf3;
    font-weight: 600;
    margin-top: 0.75rem;
    font-size: 0.9rem;
}
.nav-level-2 { color: #8b949e; }
.nav-level-3 { color: #8b949e; opacity: 0.8; font-size: 0.8rem; }
.report-nav-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem; text-transform: uppercase;
    letter-spacing: 0.1em; margin-bottom: 0.5rem;
    color: #8b949e;
}

/* Copy button */
.report-copy-btn {
    width: 100%;
    background: transparent;
    border: 1px solid rgba(0, 255, 136, 0.3);
    color: #00ff88;
    padding: 8px 12px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    cursor: pointer;
    margin-top: 1rem;
    transition: all 0.2s;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.report-copy-btn:hover {
    background: rgba(0, 255, 136, 0.1);
    border-color: #00ff88;
}
.report-copy-btn:active {
    transform: scale(0.98);
}

/* Fix invisible tab labels */
button[data-baseweb="tab"] p {
    color: #8b949e !important;
}
button[data-baseweb="tab"][aria-selected="true"] p {
    color: #00ff88 !important;
}

/* Fix multiselect tag text contrast */
.stMultiSelect [data-baseweb="tag"] {
    background-color: rgba(0, 255, 136, 0.15) !important;
    border: 1px solid rgba(0, 255, 136, 0.3) !important;
}
.stMultiSelect [data-baseweb="tag"] span {
    color: #00ff88 !important;
}
.stMultiSelect [data-baseweb="tag"] svg {
    fill: #00ff88 !important;
}

/* Custom Streamlit Running Status Widget (Top Right) */
@keyframes widget-fade-in {
    from { opacity: 0; transform: translateY(-10px) scale(0.95); }
    to { opacity: 1; transform: translateY(0) scale(1); }
}

[data-testid="stStatusWidget"] {
    background-color: #0f1011 !important; /* Linear surface-1 */
    border: 1px solid #23252a !important; /* Linear hairline */
    border-radius: 50% !important; /* Perfect circle */
    width: 32px !important;
    height: 32px !important;
    padding: 0 !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.05) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    animation: widget-fade-in 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
    position: relative !important;
    font-size: 0 !important; /* Hide any stray text like 'Running...' */
    color: transparent !important;
}

/* Hide the default running stickman SVG and any nested spans */
[data-testid="stStatusWidget"] svg,
[data-testid="stStatusWidget"] img,
[data-testid="stStatusWidget"] span {
    display: none !important;
}

/* Add a custom Vercel-style pulsing dot perfectly centered */
[data-testid="stStatusWidget"]::before {
    content: "";
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    display: block !important;
    width: 8px !important;
    height: 8px !important;
    background-color: #00ff88 !important;
    border-radius: 50% !important;
    box-shadow: 0 0 8px rgba(0, 255, 136, 0.6) !important;
    animation: status-widget-pulse 1.5s infinite !important;
    z-index: 5 !important;
    flex-shrink: 0 !important;
}

@keyframes status-widget-pulse {
    0% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.4); }
    70% { box-shadow: 0 0 0 4px rgba(0, 255, 136, 0); }
    100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); }
}

/* Make the 'Stop' button an invisible overlay to prevent layout shifts */
[data-testid="stStatusWidget"] button {
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 100% !important;
    opacity: 0 !important; /* Completely invisible */
    cursor: pointer !important;
    z-index: 10 !important;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
    font-size: 0 !important;
}

[data-testid="stStatusWidget"] button::after {
    display: none !important;
}
</style>
"""

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
    color: #8b949e !important;
    font-size: 0.85rem;
    font-weight: 500;
}

/* Sidebar Buttons */
[data-testid="stSidebar"] button[kind="secondary"] {
    background: linear-gradient(90deg, rgba(0, 255, 136, 0.1), rgba(0, 255, 136, 0.2)) !important;
    border: 1px solid rgba(0, 255, 136, 0.4) !important;
    color: #00ff88 !important;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    border-radius: 6px !important;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: linear-gradient(90deg, rgba(0, 255, 136, 0.2), rgba(0, 255, 136, 0.3)) !important;
    border-color: #00ff88 !important;
    box-shadow: 0 4px 12px rgba(0, 255, 136, 0.2) !important;
    transform: translateY(-1px);
}
[data-testid="stSidebar"] button[kind="secondary"]:active {
    transform: translateY(1px);
}

/* Sidebar Inputs and Selects */
[data-testid="stSidebar"] div[data-baseweb="select"] > div,
[data-testid="stSidebar"] input {
    background-color: rgba(0, 0, 0, 0.25) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 6px !important;
    color: #e6edf3 !important;
    transition: all 0.3s ease;
}
[data-testid="stSidebar"] div[data-baseweb="select"] > div:hover,
[data-testid="stSidebar"] input:hover {
    border-color: rgba(0, 255, 136, 0.3) !important;
    background-color: rgba(0, 255, 136, 0.02) !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within,
[data-testid="stSidebar"] input:focus {
    border-color: #00ff88 !important;
    box-shadow: 0 0 0 1px rgba(0, 255, 136, 0.2) !important;
}

/* Expanders in Sidebar */
[data-testid="stSidebar"] [data-testid="stExpander"] {
    border-color: rgba(255, 255, 255, 0.05) !important;
    background: rgba(0, 0, 0, 0.15) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
    background: rgba(0, 255, 136, 0.05) !important;
    color: #00ff88 !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {
    fill: #00ff88 !important;
}

/* Adjusted padding to prevent header overlap */
.block-container { padding-top: 3.5rem; padding-bottom: 1rem; }

/* Ensure tabs are not covered */
.stTabs { margin-top: 0.5rem; }
.stTabs [data-baseweb="tab-list"] { overflow: visible !important; }

/* Panel design - Industrial Graphite with Refraction */
.panel {
    border: 1px solid rgba(0, 255, 136, 0.15);
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    background: linear-gradient(165deg, rgba(22, 27, 34, 0.85), rgba(13, 17, 23, 0.95));
    backdrop-filter: blur(12px);
    box-shadow:
        0 4px 24px rgba(0, 0, 0, 0.5),
        inset 0 1px 1px rgba(255, 255, 255, 0.05);
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
}
.panel::after {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0, 255, 136, 0.2), transparent);
}
.panel:hover {
    border-color: rgba(0, 255, 136, 0.4);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6), inset 0 1px 1px rgba(255, 255, 255, 0.1);
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
    font-size: 0.75rem;
    font-weight: 600;
    color: #00ff88;
    text-transform: uppercase;
    letter-spacing: 0.12em;
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
    box-shadow: 0 0 8px #00ff88;
}

/* Agent status table */
.agent-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; font-family: 'Inter', sans-serif; }
.agent-table td { padding: 4px 8px; vertical-align: middle; }
.agent-table .team-name { color: #8b949e; font-weight: 600; white-space: nowrap; font-size: 0.75rem; text-transform: uppercase; }
.agent-table .agent-name { color: #c9d1d9; padding-left: 12px; }

.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 8px;
}
.status-completed { color: #00ff88; font-weight: 500; }
.status-completed::before { content: "●"; margin-right: 6px; color: #00ff88; filter: drop-shadow(0 0 4px #00ff88); }

.status-in_progress { color: #ffaa00; font-weight: 500; }
.status-in_progress::before { content: "○"; margin-right: 6px; color: #ffaa00; animation: pulse 1.5s infinite; }

.status-pending { color: #484f58; }
.status-pending::before { content: "◌"; margin-right: 6px; color: #484f58; }

.status-error { color: #ff4444; font-weight: 500; }
.status-error::before { content: "×"; margin-right: 6px; color: #ff4444; }

@keyframes pulse {
    0% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.9); }
    100% { opacity: 1; transform: scale(1); }
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
.msg-table td { padding: 5px 8px; border-bottom: 1px solid rgba(255,255,255,0.03); vertical-align: top; }
.msg-table tr:hover { background: rgba(0, 255, 136, 0.03); }
.msg-table .msg-time { color: #58a6ff; white-space: nowrap; width: 75px; opacity: 0.8; }
.msg-table .msg-type { width: 65px; text-align: center; font-weight: 600; font-size: 0.7rem; text-transform: uppercase; }
.msg-table .msg-type-Agent { color: #00ff88; }
.msg-table .msg-type-System { color: #d29922; }
.msg-table .msg-type-Data { color: #a371f7; }
.msg-table .msg-type-Tool { color: #ff7b72; }
.msg-table .msg-type-User { color: #58a6ff; }
.msg-table .msg-content { color: #c9d1d9; word-break: break-word; line-height: 1.4; }

/* Stats bar - Bento Style Refinement */
.stats-bar {
    display: flex; gap: 1rem; justify-content: center;
    font-size: 0.7rem; color: #8b949e; padding: 15px 0;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    margin-top: 2rem;
    font-family: 'JetBrains Mono', monospace;
    flex-wrap: wrap;
}
.stats-bar span {
    white-space: nowrap;
    background: rgba(13, 17, 23, 0.6);
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid rgba(255,255,255,0.03);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
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
</style>
"""

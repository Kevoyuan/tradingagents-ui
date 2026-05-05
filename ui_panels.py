"""Panel render helpers for analysis dashboard."""

import html as html_lib

from ui_config import ALL_TEAMS, ANALYST_KEY_MAP


def render_progress_panel(agent_status: dict, selected_analysts: list[str]):
    """Render the left progress panel matching CLI style."""
    rows = []
    for team, agents in ALL_TEAMS.items():
        team_agents = []
        for agent in agents:
            is_analyst = agent in ANALYST_KEY_MAP.values()
            if is_analyst:
                ak = [k for k, v in ANALYST_KEY_MAP.items() if v == agent][0]
                if ak not in selected_analysts:
                    continue
            if agent in agent_status:
                team_agents.append(agent)
        if not team_agents:
            continue

        for i, agent in enumerate(team_agents):
            status = agent_status.get(agent, "pending")
            team_cell = team if i == 0 else ""
            rows.append((team_cell, agent, status))
        rows.append(("sep", "", ""))

    html = '<table class="agent-table">'
    for team, agent, status in rows:
        if team == "sep":
            html += '<tr class="team-sep"><td colspan="3"></td></tr>'
            continue
        html += f'<tr><td class="team-name">{team}</td><td class="agent-name">{agent}</td>'
        html += f'<td class="status-{status}">{status.replace("_", " ")}</td></tr>'
    html += "</table>"
    return html


def render_messages_panel(messages: list, tool_calls: list):
    """Render the right messages panel matching CLI style."""
    all_items = []
    for ts, name, args in tool_calls:
        all_items.append((ts, "Tool", f"{name}: {args}"))
    for ts, mtype, content in messages:
        all_items.append((ts, mtype, content))

    all_items = all_items[-200:]

    html = '<table class="msg-table">'
    for ts, mtype, content in all_items:
        safe_content = html_lib.escape(str(content), quote=False)
        safe_ts = html_lib.escape(str(ts), quote=True)
        safe_mtype = html_lib.escape(str(mtype), quote=True)
        html += f'<tr><td class="msg-time">{safe_ts}</td>'
        html += f'<td class="msg-type msg-type-{safe_mtype}">{safe_mtype}</td>'
        html += f'<td class="msg-content">{safe_content}</td></tr>'
    html += "</table>"
    return html


def render_stats_bar(agent_status, llm_calls, tool_calls, tokens_in, tokens_out, report_sections, start_time, selected_analysts, report_total_for_analysts, format_tokens, time_module):
    """Render the footer stats bar."""
    completed = sum(1 for s in agent_status.values() if s == "completed")
    total = len(agent_status)
    reports_done = sum(1 for v in report_sections.values() if v)
    reports_total = report_total_for_analysts(selected_analysts)

    parts = [
        f"Agents: <b>{completed}/{total}</b>",
        f"LLM: <b>{llm_calls}</b>",
        f"Tools: <b>{tool_calls}</b>",
        f"Tokens: <b>{format_tokens(tokens_in)}</b>&uarr; <b>{format_tokens(tokens_out)}</b>&darr;",
        f"Reports: <b>{reports_done}/{reports_total}</b>",
    ]
    if start_time:
        elapsed = time_module.time() - start_time
        parts.append(f"&#9201; <b>{int(elapsed // 60):02d}:{int(elapsed % 60):02d}</b>")

    return '<div class="stats-bar">' + " &nbsp; " + " ".join(f"<span>{p}</span>" for p in parts) + "</div>"

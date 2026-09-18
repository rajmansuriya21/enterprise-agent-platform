"""
Agent Trace Visualization — Renders agent execution traces in Streamlit.
"""

import streamlit as st


def render_agent_trace(traces: list[dict], reasoning: str = "") -> None:
    """Render an agent execution trace with routing visualization.

    Args:
        traces: List of agent trace dictionaries.
        reasoning: Supervisor's routing reasoning.
    """
    if not traces:
        return

    # Agent color mapping
    agent_styles = {
        "supervisor": ("🧠", "#667eea", "Supervisor"),
        "rag_agent": ("🔍", "#22c55e", "RAG Agent"),
        "sql_agent": ("📊", "#3b82f6", "SQL Agent"),
        "api_agent": ("🌐", "#f97316", "API Agent"),
        "doc_agent": ("📄", "#a855f7", "Doc Agent"),
    }

    # Render routing reasoning
    if reasoning:
        st.markdown(
            f'<div style="background: rgba(102,126,234,0.08); border: 1px solid rgba(102,126,234,0.15); '
            f'border-radius: 10px; padding: 0.75rem 1rem; margin-bottom: 0.75rem;">'
            f'🧠 <strong>Routing Decision:</strong> {reasoning}</div>',
            unsafe_allow_html=True,
        )

    # Render each trace
    for trace in traces:
        agent_name = trace.get("agent_name", "unknown")
        emoji, color, display_name = agent_styles.get(agent_name, ("🤖", "#94a3b8", agent_name))
        latency = trace.get("latency_ms", 0)
        tools = trace.get("tools_called", [])
        success = trace.get("success", True)

        status_indicator = "✅" if success else "❌"

        st.markdown(
            f'<div style="background: rgba({_hex_to_rgb(color)}, 0.08); '
            f'border-left: 3px solid {color}; border-radius: 0 8px 8px 0; '
            f'padding: 0.5rem 1rem; margin-bottom: 0.5rem;">'
            f'{emoji} <strong>{display_name}</strong> {status_indicator} '
            f'<span style="float: right; background: rgba(249,115,22,0.15); color: #f97316; '
            f'padding: 0.1rem 0.5rem; border-radius: 12px; font-size: 0.75rem;">'
            f'{latency:.0f}ms</span><br/>'
            + (f'<span style="font-size: 0.8rem; color: #94a3b8;">Tools: {", ".join(tools)}</span>'
               if tools else "")
            + "</div>",
            unsafe_allow_html=True,
        )


def _hex_to_rgb(hex_color: str) -> str:
    """Convert hex color to RGB string for rgba() usage."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"{r}, {g}, {b}"

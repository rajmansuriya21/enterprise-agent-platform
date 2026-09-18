"""
Metrics Cards — Reusable KPI metric card components for Streamlit.
"""

import streamlit as st


def render_metric_card(
    title: str,
    value: str,
    subtitle: str = "",
    delta: str = "",
    color: str = "#667eea",
    icon: str = "📊",
) -> None:
    """Render a premium metric card.

    Args:
        title: Metric title.
        value: Main metric value.
        subtitle: Description text below the value.
        delta: Change indicator (e.g., "+5%").
        color: Primary color for the card.
        icon: Emoji icon.
    """
    delta_html = ""
    if delta:
        is_positive = delta.startswith("+")
        delta_color = "#22c55e" if is_positive else "#ef4444"
        delta_html = (
            f'<span style="color: {delta_color}; font-size: 0.85rem; font-weight: 600;">'
            f'{delta}</span>'
        )

    st.markdown(
        f'<div style="background: linear-gradient(135deg, rgba({_hex_to_rgb(color)}, 0.1) 0%, '
        f'rgba({_hex_to_rgb(color)}, 0.05) 100%); border: 1px solid rgba({_hex_to_rgb(color)}, 0.2); '
        f'border-radius: 12px; padding: 1.25rem; text-align: center; '
        f'transition: transform 0.2s ease;">'
        f'<div style="font-size: 1.5rem; margin-bottom: 0.3rem;">{icon}</div>'
        f'<div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; '
        f'letter-spacing: 0.05em; margin-bottom: 0.25rem;">{title}</div>'
        f'<div style="font-size: 1.8rem; font-weight: 700; color: {color};">{value}</div>'
        f'{delta_html}'
        f'<div style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem;">{subtitle}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_metric_row(metrics: list[dict]) -> None:
    """Render a row of metric cards.

    Args:
        metrics: List of metric dicts with keys: title, value, subtitle, delta, color, icon.
    """
    cols = st.columns(len(metrics))
    for col, metric in zip(cols, metrics):
        with col:
            render_metric_card(**metric)


def _hex_to_rgb(hex_color: str) -> str:
    """Convert hex color to RGB string."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"{r}, {g}, {b}"

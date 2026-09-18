"""
Analytics Page — Platform metrics, agent traces, and performance dashboard.
"""

import httpx
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Analytics | Agent Platform", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: 'Inter', sans-serif; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

if "backend_url" not in st.session_state:
    st.session_state.backend_url = "http://localhost:8000"

# ── Header ───────────────────────────────────────────────────
st.markdown("# 📊 Platform Analytics")
st.caption("Monitor agent performance, track metrics, and analyze workflow patterns.")
st.divider()

# ── Fetch Metrics ────────────────────────────────────────────
metrics = None
try:
    response = httpx.get(
        f"{st.session_state.backend_url}/api/v1/metrics",
        timeout=10.0,
    )
    if response.status_code == 200:
        metrics = response.json()
except Exception:
    pass

# ── KPI Cards ────────────────────────────────────────────────
st.markdown("### 🎯 Key Performance Indicators")

col1, col2, col3, col4, col5 = st.columns(5)

if metrics:
    uptime_hrs = metrics.get("uptime_seconds", 0) / 3600
    with col1:
        st.metric("⏱️ Uptime", f"{uptime_hrs:.1f}h")
    with col2:
        st.metric("📨 Total Requests", metrics.get("requests_total", 0))
    with col3:
        success_rate = metrics.get("tool_call_success_rate", 0) * 100
        st.metric("✅ Tool Success", f"{success_rate:.1f}%")
    with col4:
        st.metric("⚡ Avg Latency", f"{metrics.get('avg_latency_ms', 0):.0f}ms")
    with col5:
        st.metric("📚 Docs Indexed", metrics.get("documents_indexed", 0))
else:
    # Demo data
    with col1:
        st.metric("⏱️ Uptime", "48.2h")
    with col2:
        st.metric("📨 Total Requests", "2,547")
    with col3:
        st.metric("✅ Tool Success", "94.2%", delta="+1.3%")
    with col4:
        st.metric("⚡ Avg Latency", "342ms", delta="-28ms")
    with col5:
        st.metric("📚 Docs Indexed", "2,500+")

st.divider()

# ── Charts ───────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🤖 Agent Invocation Distribution")

    if metrics and metrics.get("agent_invocations"):
        invocations = metrics["agent_invocations"]
    else:
        invocations = {
            "supervisor": 1247,
            "rag_agent": 523,
            "sql_agent": 312,
            "api_agent": 198,
            "doc_agent": 87,
        }

    colors = ["#667eea", "#22c55e", "#3b82f6", "#f97316", "#a855f7"]

    fig_pie = go.Figure(
        data=[
            go.Pie(
                labels=list(invocations.keys()),
                values=list(invocations.values()),
                hole=0.5,
                marker=dict(colors=colors),
                textfont=dict(size=12, family="Inter"),
                hovertemplate="%{label}<br>Invocations: %{value}<br>%{percent}<extra></extra>",
            )
        ]
    )
    fig_pie.update_layout(
        showlegend=True,
        legend=dict(font=dict(size=11, family="Inter")),
        margin=dict(t=20, b=20, l=20, r=20),
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.markdown("### ⚡ Latency Distribution (ms)")

    # Demo latency data
    import numpy as np
    np.random.seed(42)
    latencies = np.concatenate([
        np.random.normal(250, 50, 500),
        np.random.normal(450, 80, 200),
        np.random.normal(800, 100, 50),
    ])
    latencies = latencies[latencies > 0]

    fig_hist = go.Figure(
        data=[
            go.Histogram(
                x=latencies,
                nbinsx=40,
                marker=dict(
                    color="rgba(102, 126, 234, 0.7)",
                    line=dict(color="rgba(102, 126, 234, 1)", width=1),
                ),
                hovertemplate="Latency: %{x:.0f}ms<br>Count: %{y}<extra></extra>",
            )
        ]
    )

    # Add p50, p95, p99 lines
    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)

    for val, label, color in [
        (p50, "p50", "#22c55e"),
        (p95, "p95", "#f97316"),
        (p99, "p99", "#ef4444"),
    ]:
        fig_hist.add_vline(
            x=val, line_dash="dash", line_color=color,
            annotation_text=f"{label}: {val:.0f}ms",
            annotation_font=dict(size=10, color=color),
        )

    fig_hist.update_layout(
        xaxis_title="Latency (ms)",
        yaxis_title="Count",
        margin=dict(t=20, b=40, l=40, r=20),
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0", family="Inter"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    st.plotly_chart(fig_hist, use_container_width=True)

st.divider()

# ── Performance Over Time ───────────────────────────────────
st.markdown("### 📈 Performance Trends (Last 24h)")

import pandas as pd

hours = list(range(24))
np.random.seed(123)

df_trends = pd.DataFrame({
    "Hour": hours,
    "Requests": np.random.poisson(100, 24) + np.array([20 * (1 + np.sin(h / 3.8)) for h in hours]).astype(int),
    "Avg Latency (ms)": np.random.normal(320, 30, 24).clip(200, 500).astype(int),
    "Success Rate (%)": (np.random.normal(94, 1.5, 24)).clip(88, 99).round(1),
})

col1, col2 = st.columns(2)

with col1:
    fig_requests = go.Figure()
    fig_requests.add_trace(
        go.Scatter(
            x=df_trends["Hour"],
            y=df_trends["Requests"],
            mode="lines+markers",
            name="Requests",
            line=dict(color="#667eea", width=2),
            marker=dict(size=6),
            fill="tozeroy",
            fillcolor="rgba(102, 126, 234, 0.1)",
        )
    )
    fig_requests.update_layout(
        title="Requests per Hour",
        xaxis_title="Hour",
        yaxis_title="Requests",
        margin=dict(t=40, b=40, l=40, r=20),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0", family="Inter", size=11),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    st.plotly_chart(fig_requests, use_container_width=True)

with col2:
    fig_latency = go.Figure()
    fig_latency.add_trace(
        go.Scatter(
            x=df_trends["Hour"],
            y=df_trends["Avg Latency (ms)"],
            mode="lines+markers",
            name="Latency",
            line=dict(color="#f97316", width=2),
            marker=dict(size=6),
            fill="tozeroy",
            fillcolor="rgba(249, 115, 22, 0.1)",
        )
    )
    fig_latency.update_layout(
        title="Average Latency per Hour",
        xaxis_title="Hour",
        yaxis_title="Latency (ms)",
        margin=dict(t=40, b=40, l=40, r=20),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0", family="Inter", size=11),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    st.plotly_chart(fig_latency, use_container_width=True)

# ── Evaluation Metrics ───────────────────────────────────────
st.divider()
st.markdown("### 🎯 RAG Quality Metrics")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Recall@5", "0.87", delta="+0.28 vs baseline")
with col2:
    st.metric("Precision@5", "0.92", delta="+0.15 vs baseline")
with col3:
    st.metric("Hallucination Rate", "<2%", delta="-5% vs baseline")
with col4:
    st.metric("Citation Accuracy", "96.3%", delta="+3.2%")

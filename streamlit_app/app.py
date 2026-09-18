"""
Enterprise Multi-Agent Platform — Streamlit Dashboard

Main application entry point with multi-page navigation,
dark theme configuration, and session state management.
"""

import streamlit as st

# ── Page Configuration ───────────────────────────────────────
st.set_page_config(
    page_title="Enterprise Agent Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/your-repo/agent-platform",
        "Report a Bug": "https://github.com/your-repo/agent-platform/issues",
        "About": "Enterprise Multi-Agent Workflow & Document Intelligence Platform v1.0",
    },
)

# ── Custom CSS for Premium Dark Theme ────────────────────────
st.markdown(
    """
    <style>
    /* Import premium font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global styles */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f23 0%, #1a1a3e 100%);
    }

    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #e2e8f0;
    }

    /* Hero gradient text */
    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f97316 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }

    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        font-weight: 300;
        margin-bottom: 2rem;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(20, 20, 45, 0.6) 0%, rgba(30, 25, 60, 0.6) 100%);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.05);
    }

    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 30px rgba(102, 126, 234, 0.25), 0 0 15px rgba(118, 75, 162, 0.2);
        border-color: rgba(102, 126, 234, 0.6);
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #cbd5e1;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 500;
    }

    /* Agent badges */
    .agent-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }

    .agent-rag { background: rgba(34, 197, 94, 0.15); color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.3); }
    .agent-sql { background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); }
    .agent-api { background: rgba(249, 115, 22, 0.15); color: #f97316; border: 1px solid rgba(249, 115, 22, 0.3); }
    .agent-doc { background: rgba(168, 85, 247, 0.15); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3); }

    /* Status indicators */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
    }

    .status-healthy { background: #22c55e; box-shadow: 0 0 8px rgba(34, 197, 94, 0.4); }
    .status-degraded { background: #f97316; box-shadow: 0 0 8px rgba(249, 115, 22, 0.4); }
    .status-unhealthy { background: #ef4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.4); }

    /* Chat styling */
    .chat-message {
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 0.75rem;
        animation: fadeIn 0.3s ease;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        font-size: 0.9rem;
        font-weight: 500;
    }

    /* Hide default Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session State Initialization ─────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    import uuid
    st.session_state.thread_id = str(uuid.uuid4())
if "backend_url" not in st.session_state:
    st.session_state.backend_url = "http://localhost:8000"

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align: center; padding: 1rem 0;">
            <div style="font-size: 3rem;">🤖</div>
            <div class="hero-title" style="font-size: 1.4rem;">Agent Platform</div>
            <div class="hero-subtitle" style="font-size: 0.85rem;">Enterprise Multi-Agent AI</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # Navigation info
    st.markdown("### 🧭 Navigation")
    st.markdown(
        """
        - 💬 **Chat** — Interact with agents
        - 📄 **Documents** — Manage knowledge base
        - 📊 **Analytics** — View metrics & traces
        - ⚙️ **Settings** — Configure platform
        """
    )

    st.divider()

    # Quick status
    st.markdown("### 📡 System Status")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            '<span class="status-dot status-healthy"></span> API',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<span class="status-dot status-healthy"></span> LLM',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            '<span class="status-dot status-degraded"></span> Qdrant',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<span class="status-dot status-degraded"></span> Redis',
            unsafe_allow_html=True,
        )

    st.divider()
    st.caption("v1.0.0 | Enterprise Edition")

# ── Main Content ─────────────────────────────────────────────
st.markdown(
    """
    <div class="hero-title">Enterprise Multi-Agent Platform</div>
    <div class="hero-subtitle">
        Intelligent workflow orchestration powered by LangGraph, GPT-4, and Qdrant.
        Route complex queries across specialized AI agents with citation-grounded responses.
    </div>
    """,
    unsafe_allow_html=True,
)

# Feature cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-value">🔍</div>
            <div style="font-weight: 600; margin: 0.5rem 0;">RAG Agent</div>
            <div class="metric-label">Knowledge retrieval with citation-grounded answers</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-value">📊</div>
            <div style="font-weight: 600; margin: 0.5rem 0;">SQL Agent</div>
            <div class="metric-label">Natural language to SQL analytics & reporting</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-value">🌐</div>
            <div style="font-weight: 600; margin: 0.5rem 0;">API Agent</div>
            <div class="metric-label">Real-time external data from APIs & web</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        """
        <div class="metric-card">
            <div class="metric-value">📄</div>
            <div style="font-weight: 600; margin: 0.5rem 0;">Doc Agent</div>
            <div class="metric-label">Document parsing, extraction & ingestion</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# Quick start guide
st.markdown("### 🚀 Quick Start")
st.markdown(
    """
    1. **Navigate to 💬 Chat** to interact with the multi-agent system
    2. **Upload documents** in 📄 Documents to build your knowledge base
    3. **Monitor performance** in 📊 Analytics to track agent metrics
    4. **Configure settings** in ⚙️ Settings to customize the platform

    **Try these example queries:**
    - *"What is our company's leave policy?"* → Routes to **RAG Agent**
    - *"Show total sales by region for Q3"* → Routes to **SQL Agent**
    - *"What's the weather in New York?"* → Routes to **API Agent**
    - *"Extract data from this PDF"* → Routes to **Doc Agent**
    """
)

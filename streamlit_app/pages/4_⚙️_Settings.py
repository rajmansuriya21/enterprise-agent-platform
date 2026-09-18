"""
Settings Page — Platform configuration panel.
"""

import streamlit as st

st.set_page_config(page_title="Settings | Agent Platform", page_icon="⚙️", layout="wide")

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

# ── Header ───────────────────────────────────────────────────
st.markdown("# ⚙️ Platform Settings")
st.caption("Configure the multi-agent platform parameters.")
st.divider()

# ── LLM Configuration ───────────────────────────────────────
st.markdown("### 🧠 LLM Configuration")

col1, col2 = st.columns(2)

with col1:
    model = st.selectbox(
        "Primary Model",
        ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "qwen-3.5"],
        index=0,
        help="The main LLM model used by the Supervisor agent.",
    )

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=0.1,
        step=0.05,
        help="Lower = more deterministic, Higher = more creative.",
    )

with col2:
    fallback_model = st.selectbox(
        "Fallback Model",
        ["gpt-4o-mini", "gpt-3.5-turbo"],
        index=0,
        help="Fallback model used when primary model fails.",
    )

    max_tokens = st.number_input(
        "Max Tokens",
        min_value=256,
        max_value=16384,
        value=4096,
        step=256,
        help="Maximum tokens per LLM response.",
    )

st.divider()

# ── Vector Store Configuration ───────────────────────────────
st.markdown("### 🗄️ Vector Store (Qdrant)")

col1, col2 = st.columns(2)

with col1:
    qdrant_url = st.text_input(
        "Qdrant URL",
        value="http://localhost:6333",
        help="URL of the Qdrant vector database.",
    )

    collection_name = st.text_input(
        "Collection Name",
        value="enterprise_docs",
        help="Name of the Qdrant collection for document vectors.",
    )

with col2:
    embedding_model = st.selectbox(
        "Embedding Model",
        ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
        index=0,
        help="OpenAI embedding model for vector generation.",
    )

    embedding_dim = st.number_input(
        "Embedding Dimension",
        min_value=256,
        max_value=3072,
        value=1536,
        step=256,
        help="Dimension of the embedding vectors.",
    )

st.divider()

# ── Chunking Configuration ───────────────────────────────────
st.markdown("### ✂️ Document Chunking")

col1, col2, col3 = st.columns(3)

with col1:
    chunk_size = st.number_input(
        "Chunk Size (chars)",
        min_value=100,
        max_value=5000,
        value=1000,
        step=100,
        help="Maximum characters per chunk.",
    )

with col2:
    chunk_overlap = st.number_input(
        "Chunk Overlap (chars)",
        min_value=0,
        max_value=1000,
        value=200,
        step=50,
        help="Character overlap between consecutive chunks.",
    )

with col3:
    top_k = st.number_input(
        "Retrieval Top-K",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        help="Number of chunks to retrieve per query.",
    )

st.divider()

# ── API Configuration ────────────────────────────────────────
st.markdown("### 🔑 API Keys & Services")

col1, col2 = st.columns(2)

with col1:
    openai_key = st.text_input(
        "OpenAI API Key",
        type="password",
        help="Your OpenAI API key for LLM and embedding models.",
    )

    redis_url = st.text_input(
        "Redis URL",
        value="redis://localhost:6379/0",
        help="Redis connection URL for caching.",
    )

with col2:
    mlflow_uri = st.text_input(
        "MLflow Tracking URI",
        value="http://localhost:5000",
        help="MLflow server URL for experiment tracking.",
    )

    rate_limit = st.number_input(
        "Rate Limit (RPM)",
        min_value=1,
        max_value=1000,
        value=60,
        step=10,
        help="Maximum requests per minute per client.",
    )

st.divider()

# ── Save Button ──────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("💾 Save Settings", type="primary", use_container_width=True):
        st.success("✅ Settings saved successfully!")
        st.balloons()

with col2:
    if st.button("🔄 Reset Defaults", use_container_width=True):
        st.info("Settings reset to defaults.")
        st.rerun()

# ── System Info ──────────────────────────────────────────────
st.divider()
with st.expander("ℹ️ System Information"):
    st.json({
        "platform_version": "1.0.0",
        "python_version": "3.11+",
        "frameworks": {
            "langgraph": "0.3+",
            "langchain": "0.3+",
            "fastapi": "0.115+",
            "qdrant": "1.12+",
            "streamlit": "1.40+",
        },
        "agents": ["supervisor", "rag_agent", "sql_agent", "api_agent", "doc_agent"],
        "deployment": "Docker Compose",
    })

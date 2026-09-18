"""
Chat Page — Real-time streaming chat interface with agent routing visualization.
"""

import json
import uuid
import time

import httpx
import streamlit as st

st.set_page_config(page_title="Chat | Agent Platform", page_icon="💬", layout="wide")

# ── Custom CSS ───────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: 'Inter', sans-serif; }

    .agent-routing-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%);
        border: 1px solid rgba(102, 126, 234, 0.15);
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
    }

    .citation-card {
        background: rgba(34, 197, 94, 0.08);
        border: 1px solid rgba(34, 197, 94, 0.2);
        border-radius: 8px;
        padding: 0.5rem 0.75rem;
        margin: 0.25rem 0;
        font-size: 0.8rem;
    }

    .latency-badge {
        display: inline-block;
        background: rgba(249, 115, 22, 0.15);
        color: #f97316;
        padding: 0.15rem 0.5rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session State ────────────────────────────────────────────
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": "👋 **Welcome to the Enterprise Multi-Agent Platform!**\n\nI am the Supervisor Agent. How can I help you today?\n\n*Try asking me to check the weather, query the sales database, or analyze a document!*"
        }
    ]
if "chat_thread_id" not in st.session_state:
    st.session_state.chat_thread_id = str(uuid.uuid4())
if "backend_url" not in st.session_state:
    st.session_state.backend_url = "http://localhost:8000"

# ── Header ───────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("# 💬 Agent Chat")
    st.caption("Interact with the multi-agent system. Your queries are intelligently routed to specialized agents.")

with col2:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_messages = []
        st.session_state.chat_thread_id = str(uuid.uuid4())
        st.rerun()

    st.caption(f"Thread: `{st.session_state.chat_thread_id[:8]}...`")

st.divider()

# ── Chat History ─────────────────────────────────────────────
for message in st.session_state.chat_messages:
    role = message["role"]
    with st.chat_message(role, avatar="🧑‍💻" if role == "user" else "🤖"):
        st.markdown(message["content"])

        # Show agent trace if available
        if "agent_traces" in message and message["agent_traces"]:
            with st.expander("🔍 Agent Routing & Traces", expanded=False):
                for trace in message["agent_traces"]:
                    agent_name = trace.get("agent_name", "unknown")
                    latency = trace.get("latency_ms", 0)
                    tools = trace.get("tools_called", [])

                    agent_colors = {
                        "supervisor": "🧠",
                        "rag_agent": "🔍",
                        "sql_agent": "📊",
                        "api_agent": "🌐",
                        "doc_agent": "📄",
                    }
                    emoji = agent_colors.get(agent_name, "🤖")

                    st.markdown(
                        f"**{emoji} {agent_name}** — "
                        f'<span class="latency-badge">{latency:.0f}ms</span>',
                        unsafe_allow_html=True,
                    )
                    if tools:
                        st.caption(f"Tools: {', '.join(tools)}")

        # Show citations if available
        if "citations" in message and message["citations"]:
            with st.expander("📚 Source Citations", expanded=False):
                for cite in message["citations"]:
                    st.markdown(
                        f'<div class="citation-card">'
                        f'<strong>[Source {cite.get("source_id", "")}]</strong> '
                        f'{cite.get("file", "Unknown")} '
                        f'(relevance: {cite.get("score", 0):.2f})<br/>'
                        f'<em>{cite.get("content_preview", "")[:150]}...</em>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

# ── Chat Input ───────────────────────────────────────────────
if prompt := st.chat_input("Ask anything... (e.g., 'Show sales by region', 'What's the weather?')"):
    # Add user message
    st.session_state.chat_messages.append({"role": "user", "content": prompt})

    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)

    # Process with agent
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🧠 Routing to specialized agent..."):
            try:
                response = httpx.post(
                    f"{st.session_state.backend_url}/api/v1/chat",
                    json={
                        "message": prompt,
                        "thread_id": st.session_state.chat_thread_id,
                    },
                    timeout=120.0,
                )

                if response.status_code == 200:
                    data = response.json()

                    # Display response
                    st.markdown(data.get("response", "No response received."))

                    # Store with metadata
                    assistant_msg = {
                        "role": "assistant",
                        "content": data.get("response", ""),
                        "agent_traces": data.get("agent_traces", []),
                        "citations": data.get("citations", []),
                        "routing_reasoning": data.get("routing_reasoning", ""),
                        "total_latency_ms": data.get("total_latency_ms", 0),
                    }
                    st.session_state.chat_messages.append(assistant_msg)

                    # Show routing info
                    if data.get("routing_reasoning"):
                        st.markdown(
                            f'<div class="agent-routing-card">'
                            f'🧠 <strong>Routing:</strong> {data["routing_reasoning"]}'
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    # Show latency
                    if data.get("total_latency_ms"):
                        st.caption(f"⚡ Total latency: {data['total_latency_ms']:.0f}ms")

                else:
                    error_msg = f"API error: {response.status_code} - {response.text}"
                    st.error(error_msg)
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": error_msg,
                    })

            except httpx.ConnectError:
                fallback_msg = (
                    "⚠️ **Backend not reachable.** Make sure the FastAPI server is running:\n\n"
                    "```bash\nmake api\n# or\nuvicorn src.api.main:app --reload --port 8000\n```\n\n"
                    "**Demo Mode:** Here's how the system works:\n\n"
                    f"Your query: *\"{prompt}\"*\n\n"
                    "The **Supervisor Agent** would analyze this and route it to the appropriate "
                    "specialized agent based on intent detection."
                )
                st.markdown(fallback_msg)
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": fallback_msg,
                })

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": error_msg,
                })

# ── Sidebar Quick Examples ───────────────────────────────────
with st.sidebar:
    st.markdown("### 💡 Example Queries")

    examples = {
        "🔍 RAG": "What is our company's leave policy?",
        "📊 SQL": "Show total sales by region for Q3",
        "🌐 API": "What's the current weather in New York?",
        "📄 Doc": "Extract key information from the uploaded document",
    }

    for label, query in examples.items():
        if st.button(label, key=f"example_{label}", use_container_width=True):
            st.session_state.chat_messages.append({"role": "user", "content": query})
            st.rerun()

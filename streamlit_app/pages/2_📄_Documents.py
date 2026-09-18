"""
Documents Page — Upload, manage, and browse documents in the knowledge base.
"""

import httpx
import streamlit as st

st.set_page_config(page_title="Documents | Agent Platform", page_icon="📄", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .stApp { font-family: 'Inter', sans-serif; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .doc-card {
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.08) 0%, rgba(59, 130, 246, 0.08) 100%);
        border: 1px solid rgba(168, 85, 247, 0.2);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "backend_url" not in st.session_state:
    st.session_state.backend_url = "http://localhost:8000"

# ── Header ───────────────────────────────────────────────────
st.markdown("# 📄 Document Management")
st.caption("Upload, manage, and browse documents in your enterprise knowledge base.")
st.divider()

# ── Upload Section ───────────────────────────────────────────
st.markdown("### 📤 Upload Documents")
st.markdown("Upload PDF, DOCX, TXT, MD, or CSV files to build your knowledge base.")

uploaded_files = st.file_uploader(
    "Drag and drop files here",
    type=["pdf", "docx", "txt", "md", "csv"],
    accept_multiple_files=True,
    help="Supported: PDF, DOCX, TXT, MD, CSV",
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.spinner(f"📥 Ingesting {uploaded_file.name}..."):
            try:
                response = httpx.post(
                    f"{st.session_state.backend_url}/api/v1/documents/upload",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue())},
                    timeout=120.0,
                )

                if response.status_code == 200:
                    result = response.json()
                    st.success(
                        f"✅ **{uploaded_file.name}** ingested successfully!\n"
                        f"Chunks: {result.get('chunk_count', 0)} | "
                        f"Time: {result.get('elapsed_seconds', 0):.1f}s"
                    )
                else:
                    st.error(f"❌ Upload failed: {response.text}")

            except httpx.ConnectError:
                st.warning(
                    f"⚠️ Backend not reachable. Start the API server first.\n"
                    f"File **{uploaded_file.name}** would be ingested into the vector store."
                )
            except Exception as e:
                st.error(f"Error uploading {uploaded_file.name}: {str(e)}")

st.divider()

# ── Document Library ─────────────────────────────────────────
st.markdown("### 📚 Document Library")

try:
    response = httpx.get(
        f"{st.session_state.backend_url}/api/v1/documents",
        timeout=10.0,
    )

    if response.status_code == 200:
        documents = response.json()

        if documents:
            for doc in documents:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(
                        f'<div class="doc-card">'
                        f'📄 <strong>{doc.get("file_name", "Unknown")}</strong><br/>'
                        f'<span style="color: #94a3b8; font-size: 0.85rem;">'
                        f'Type: {doc.get("file_type", "?")} | '
                        f'Size: {doc.get("file_size", 0) / 1024:.1f} KB</span>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with col2:
                    st.metric("Chunks", doc.get("chunk_count", "—"))
                with col3:
                    if st.button("🗑️", key=f"del_{doc.get('doc_id', '')}"):
                        try:
                            del_response = httpx.delete(
                                f"{st.session_state.backend_url}/api/v1/documents/{doc['doc_id']}",
                                timeout=10.0,
                            )
                            if del_response.status_code == 200:
                                st.success("Deleted!")
                                st.rerun()
                            else:
                                st.error("Delete failed")
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.info("📭 No documents in the knowledge base yet. Upload some above!")
    else:
        st.warning(f"Could not fetch documents: {response.status_code}")

except httpx.ConnectError:
    st.info(
        "📭 **Backend not reachable.** Start the API to manage documents.\n\n"
        "```bash\nmake api\n```\n\n"
        "**Sample documents would include:**\n"
        "- `hr_leave_policy.pdf` (24 chunks)\n"
        "- `q3_financial_report.docx` (38 chunks)\n"
        "- `product_documentation.md` (15 chunks)\n"
        "- `employee_handbook.pdf` (52 chunks)"
    )
except Exception as e:
    st.error(f"Error: {str(e)}")

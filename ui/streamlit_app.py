import streamlit as st
import requests
import json

st.set_page_config(page_title="Resume Analyzer & RAG Assistant", page_icon="📄", layout="wide")

API_BASE = "http://127.0.0.1:8000"

st.title("📄 Resume Analyzer & RAG Candidate Assistant")
st.write("A simple AI tool to analyze resumes, search vectors, and chat with candidate knowledge.")

# 3 Clear, Beginner-Friendly Tabs
tab1, tab2, tab3 = st.tabs(["📤 Upload & Analyze Resume", "💬 RAG Chat Assistant", "🔍 Qdrant Knowledge Inspector"])

# --- TAB 1: UPLOAD & ANALYZE ---
with tab1:
    st.header("Upload Resume")
    st.write("Upload a PDF, DOCX, or TXT resume to analyze and build vector embeddings.")
    
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx", "txt"])
    if uploaded_file is not None:
        if st.button("Analyze & Index Resume"):
            with st.spinner("Analyzing resume and indexing into Qdrant Vector DB..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                try:
                    res = requests.post(f"{API_BASE}/analyze-resume", files=files)
                    if res.status_code == 200:
                        st.success("Resume successfully analyzed and indexed into Qdrant!")
                        st.json(res.json())
                    else:
                        st.error(f"Error ({res.status_code}): {res.text}")
                except Exception as e:
                    st.error("Failed to connect to backend server. Make sure uvicorn is running.")

# --- TAB 2: RAG CHAT ASSISTANT ---
with tab2:
    st.header("Chat with Candidate Assistant")
    st.write("Ask any career or professional questions about the candidate.")
    
    session_id = st.text_input("Session ID", value="session-01")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if user_query := st.chat_input("Ask a question about the candidate..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.write(user_query)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            try:
                payload = {"session_id": session_id, "message": user_query}
                response = requests.post(f"{API_BASE}/chat/stream", json=payload, stream=True)
                
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")
                        if line_str.startswith("data: "):
                            data_json = json.loads(line_str[6:])
                            token = data_json.get("token", "")
                            full_response += token
                            message_placeholder.write(full_response + "▌")
                message_placeholder.write(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Error: {e}")

# --- TAB 3: QDRANT KNOWLEDGE INSPECTOR ---
with tab3:
    st.header("🔍 Qdrant Knowledge Inspector")
    st.write("Test similarity vector search directly against Qdrant storage.")
    
    test_query = st.text_input("Enter query to inspect matching chunks:", value="experience")
    if st.button("Search Qdrant Vectors"):
        if test_query:
            try:
                from services.vector_store import vector_store
                results = vector_store.search_similar_chunks(test_query, top_k=4)
                st.write(f"### Found {len(results)} matching knowledge chunks:")
                for i, r in enumerate(results):
                    with st.expander(f"Chunk {i+1} (Similarity Score: {r['score']:.4f})"):
                        st.write(r["text"])
            except Exception as e:
                st.error(f"Error querying Qdrant: {e}")

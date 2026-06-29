import streamlit as st
import requests
import json
import os

st.set_page_config(page_title="Resume Analyzer & Vector RAG Assistant", page_icon="📄", layout="wide")

API_BASE = "http://127.0.0.1:8000"

st.title("📄 Resume Analyzer & RAG Candidate Assistant")
st.markdown("Powered by **Gemini 2.5 Flash**, **Google gemini-embedding-001**, **Qdrant Vector DB**, and **FastAPI**.")

tabs = st.tabs(["📤 Upload & Analyze Resume", "💬 RAG Chat Assistant", "🔍 Qdrant Knowledge Inspector"])

with tabs[0]:
    st.header("Upload Resume")
    uploaded_file = st.file_uploader("Choose a PDF, DOCX, or TXT resume", type=["pdf", "docx", "txt"])
    
    if uploaded_file is not None:
        if st.button("Analyze & Index Resume in Qdrant"):
            with st.spinner("Analyzing resume and building Qdrant Vector Embeddings..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                try:
                    res = requests.post(f"{API_BASE}/analyze-resume", files=files)
                    if res.status_code == 200:
                        st.success("Resume successfully analyzed and indexed into Qdrant Vector DB!")
                        st.json(res.json())
                    else:
                        st.error(f"Error ({res.status_code}): {res.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend server at {API_BASE}. Make sure uvicorn is running. Error: {e}")

with tabs[1]:
    st.header("Chat with Candidate RAG Assistant")
    session_id = st.text_input("Session ID", value="streamlit-session-01")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_query := st.chat_input("Ask a professional or resume question about the candidate..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

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
                            message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Streaming error: {e}")

with tabs[2]:
    st.header("🔍 Qdrant Vector Database Knowledge Inspector")
    st.markdown("Test similarity search directly against the Qdrant vector store.")
    test_query = st.text_input("Enter a query to inspect top-K retrieved chunks:")
    if st.button("Search Qdrant Vectors"):
        if test_query:
            try:
                from services.vector_store import vector_store
                results = vector_store.search_similar_chunks(test_query, top_k=4)
                st.write(f"Retrieved {len(results)} chunks:")
                for i, r in enumerate(results):
                    with st.expander(f"Chunk {i+1} (Score: {r['score']:.4f})"):
                        st.write(r["text"])
            except Exception as e:
                st.error(f"Error querying Qdrant: {e}")

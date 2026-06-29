import streamlit as st
import requests
import json

st.set_page_config(page_title="Resume AI Chatbot", page_icon="🤖")

API_BASE = "http://127.0.0.1:8000"

# Sidebar for simple file upload
with st.sidebar:
    st.header("📤 Upload Resume")
    uploaded_file = st.file_uploader("Upload PDF, DOCX, or TXT", type=["pdf", "docx", "txt"])
    if uploaded_file is not None:
        if st.button("Upload & Process"):
            with st.spinner("Processing resume..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                try:
                    res = requests.post(f"{API_BASE}/analyze-resume", files=files)
                    if res.status_code == 200:
                        st.success("Resume processed successfully!")
                    else:
                        st.error("Error processing file.")
                except Exception as e:
                    st.error("Backend connection failed. Start FastAPI server.")

# Main Chat Interface
st.title("🤖 Resume AI Chatbot")
st.write("Ask any questions about the candidate's resume!")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Chat input for user
if prompt := st.chat_input("Ask a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        try:
            payload = {"session_id": "beginner-session", "message": prompt}
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
            st.error("Error connecting to server.")

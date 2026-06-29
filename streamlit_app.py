import streamlit as st
import requests
import json
import uuid
import os

st.set_page_config(
    page_title="Resume Chatbot",
    page_icon="💼",
    layout="centered"
)

API_BASE_URL = "http://localhost:8000"
RESUME_DIR = "resume"

backend_online = False
try:
    health_check = requests.get(f"{API_BASE_URL}/", timeout=1.5)
    if health_check.status_code in [200, 307]:
        backend_online = True
except requests.RequestException as conn_err:
    _ = conn_err
    backend_online = False

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

st.sidebar.title("Configuration")

session_id = st.sidebar.text_input("Session ID", value=st.session_state.session_id)
if session_id != st.session_state.session_id:
    st.session_state.session_id = session_id
    # Load session history if backend is online
    if backend_online:
        try:
            res = requests.get(f"{API_BASE_URL}/chat/history/{session_id}")
            if res.status_code == 200:
                st.session_state.messages = res.json().get("history", [])
        except requests.RequestException as hist_err:
            _ = hist_err
            st.session_state.messages = []

if st.sidebar.button("Start New Session"):
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.rerun()

st.sidebar.subheader("Active Resume")
resume_files = []
if os.path.exists(RESUME_DIR):
    resume_files = [f for f in os.listdir(RESUME_DIR) if f.lower().endswith((".pdf", ".docx", ".txt"))]

if resume_files:
    st.sidebar.success(f"Loaded: {resume_files[0]}")
else:
    st.sidebar.warning("No resume loaded. Place a file in the 'resume' folder.")

st.title("Career Advisor Chatbot")
st.write("Ask professional questions about the candidate's resume.")

if not backend_online:
    st.error("FastAPI Backend Server is Offline.")
    st.info("Please start the backend server in your terminal:")
    st.code(".venv\\Scripts\\python.exe -m uvicorn app:app --reload", language="cmd")
    st.stop()

for msg in st.session_state.messages:
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.write(msg["content"])

def stream_response(sess_id, message):
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat/stream",
            json={"session_id": sess_id, "message": message},
            stream=True
        )
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data: "):
                    data = json.loads(decoded[6:])
                    yield data.get("token", "")
    except requests.RequestException as stream_err:
        yield f"Error: {stream_err}"

user_input = st.chat_input("Enter your message...")

if user_input:
    # Render user message
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("assistant"):
        response_generator = stream_response(st.session_state.session_id, user_input)
        full_response = st.write_stream(response_generator)  # type: ignore # noqa
        
    st.session_state.messages.append({"role": "model", "content": full_response})

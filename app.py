import os
import uuid
import json

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel
from services.document_service import extract_document_text
from services.gemini_service import analyze_resume, batch_analyze_resumes
from services.circuit_breaker import CircuitOpenException
from prompts.resume_prompt import RESUME_ANALYSIS_PROMPT
from models.response_models import ResumeResponse
from services.cache_service import calculate_file_hash, get_cached_analysis, save_to_cache
from services.memory_service import get_session_memory, update_session_memory
from services.db_service import save_message_to_db, get_history_from_db
from services.chat_service import stream_chat_response, is_query_safe_and_relevant


app = FastAPI(title="Resume Analyzer", description="Analyze PDF, Word, and Text resumes and return structured JSON output.",)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_active_resume(filename: str, file_bytes: bytes):
    RESUME_DIR = "resume"
    if os.path.exists(RESUME_DIR):
        for f in os.listdir(RESUME_DIR):
            try:
                os.remove(os.path.join(RESUME_DIR, f))
            except Exception as e:
                print(f"Error cleaning resume folder: {e}")
    else:
        os.makedirs(RESUME_DIR, exist_ok=True)
    
    active_resume_path = os.path.join(RESUME_DIR, filename)
    with open(active_resume_path, "wb") as buffer:
        buffer.write(file_bytes)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.post(
    "/analyze-resume",
    response_model=ResumeResponse,
    summary="Analyze Resume",
    description="Upload a PDF, DOCX, or TXT resume and receive structured analysis.")
async def analyze_resume_api(
    file: UploadFile = File(...)
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided."
        )

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".txt"]:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX, and TXT files are supported."
        )

    try:
        file_bytes = await file.read()
        file_hash = calculate_file_hash(file_bytes)
        cached_result = get_cached_analysis(file_hash)
        if cached_result:
            save_active_resume(file.filename, file_bytes)
            return ResumeResponse.model_validate_json(cached_result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file or cache: {str(e)}"
        )

    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(
        UPLOAD_DIR,
        unique_filename
    )

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
        resume_text = extract_document_text(file_path)

        if not resume_text.strip():
            raise HTTPException(
                status_code=400,
                detail=(
                    "The uploaded file does not contain "
                    "extractable text. Please check the file content."
                )
            )

        analysis_result = analyze_resume(
            resume_text,
            RESUME_ANALYSIS_PROMPT
        )

        save_to_cache(file_hash, analysis_result.model_dump_json())
        save_active_resume(file.filename, file_bytes)
        return analysis_result
    except CircuitOpenException as ce:
        raise HTTPException(
            status_code=503,
            detail=str(ce)
        )
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)

        if (
            "API_KEY_INVALID" in error_message
            or "API key not valid" in error_message
        ):
            raise HTTPException(
                status_code=500,
                detail=(
                    "Invalid Gemini API Key. "
                    "Please check your .env file."
                )
            )
        raise HTTPException(
            status_code=500,
            detail=f"Error processing resume: {error_message}"
        )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.post(
    "/analyze-resumes-batch",
    summary="Batch Analyze Resumes (Parallel Threads)",
    description="Upload multiple resumes and process them in parallel threads using Circuit Breaker & Retry protection.")
async def analyze_resumes_batch_api(
    files: list[UploadFile] = File(...)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    resume_items = []
    temp_files = []

    for file in files:
        ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
        if ext not in [".pdf", ".docx", ".txt"]:
            continue

        file_bytes = await file.read()
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        temp_files.append(file_path)

        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
        text = extract_document_text(file_path)
        if text.strip():
            resume_items.append((file.filename, text))

    try:
        if not resume_items:
            raise HTTPException(status_code=400, detail="None of the uploaded files contained valid extractable text.")

        batch_results = batch_analyze_resumes(resume_items, RESUME_ANALYSIS_PROMPT, max_workers=min(4, len(resume_items)))
        return {"total_processed": len(batch_results), "results": batch_results}
    finally:
        for tf in temp_files:
            if os.path.exists(tf):
                os.remove(tf)


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/chat/stream", summary="Stream Chat", description="Stream multi-turn chat responses related to the candidate's resume.")
async def chat_stream_api(request: ChatRequest):
    # Check guardrails first
    if not is_query_safe_and_relevant(request.message):
        async def blocked_generator():
            blocked_msg = "I am programmed to only answer career, resume, and professional queries. Please ask a relevant question."
            yield f"data: {json.dumps({'token': blocked_msg})}\n\n"
        return StreamingResponse(blocked_generator(), media_type="text/event-stream")

    # Fetch short-term history
    history = get_session_memory(request.session_id)
    
    async def sse_generator():
        full_response = []
        for chunk in stream_chat_response(request.message, history):
            full_response.append(chunk)
            yield f"data: {json.dumps({'token': chunk})}\n\n"
        
        assistant_reply = "".join(full_response)
        
        # Save messages to both short-term memory and long-term DB
        save_message_to_db(request.session_id, "user", request.message)
        update_session_memory(request.session_id, "user", request.message)
        
        save_message_to_db(request.session_id, "model", assistant_reply)
        update_session_memory(request.session_id, "model", assistant_reply)

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@app.get("/chat/history/{session_id}", summary="Get Chat History", description="Retrieve the complete long-term chat history for a session.")
async def chat_history_api(session_id: str):
    history = get_history_from_db(session_id)
    return {"history": history}
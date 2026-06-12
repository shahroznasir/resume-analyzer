import os
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from services.pdf_service import extract_pdf_text
from services.gemini_service import analyze_resume
from prompts.resume_prompt import RESUME_ANALYSIS_PROMPT
from models.response_models import ResumeResponse

app = FastAPI(title="Resume Analyzer", description="Analyze PDF resumes and return structured JSON output.",)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.post(
    "/analyze-resume",
    response_model=ResumeResponse,
    summary="Analyze Resume",
    description="Upload a PDF resume and receive structured analysis.")
async def analyze_resume_api(
    file: UploadFile = File(...)
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    unique_filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(
        UPLOAD_DIR,
        unique_filename
    )

    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        resume_text = extract_pdf_text(file_path)

        if not resume_text.strip():
            raise HTTPException(
                status_code=400,
                detail=(
                    "The uploaded PDF does not contain "
                    "extractable text. It may be scanned "
                    "or image-based."
                )
            )

        analysis_result = analyze_resume(
            resume_text,
            RESUME_ANALYSIS_PROMPT
        )

        return analysis_result
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
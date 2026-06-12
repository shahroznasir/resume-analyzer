import os
import google.generativeai as genai

from dotenv import load_dotenv
from models.response_models import ResumeResponse

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found"
    )
genai.configure(
    api_key=api_key
)
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash"
)

def analyze_resume(
    resume_text: str,
    system_prompt: str
) -> ResumeResponse:
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=ResumeResponse,
        temperature=0.2,
        top_p=0.95,
        top_k=40,
        max_output_tokens=2000
    )
    response = model.generate_content(
        [
            system_prompt,
            resume_text
        ],
        generation_config=generation_config
    )
    try:
        return ResumeResponse.model_validate_json(
            response.text
        )
    except Exception as e:
        raise ValueError(
            f"Failed to parse response: {e}"
        )
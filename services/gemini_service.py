import os
import time
import random
from google import genai
from google.genai import types
from google.genai.errors import APIError

from dotenv import load_dotenv
from models.response_models import ResumeResponse

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found"
    )

client = genai.Client(api_key=api_key)

def analyze_resume(
    resume_text: str,
    system_prompt: str
) -> ResumeResponse:
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ResumeResponse,
        temperature=0.2,
        top_p=0.95,
        top_k=40,
        max_output_tokens=2000,
        system_instruction=system_prompt
    )

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=resume_text,
                config=config
            )
            try:
                return ResumeResponse.model_validate_json(
                    response.text
                )
            except Exception as e:
                raise ValueError(
                    f"Failed to parse response: {e}"
                )
        except APIError as e:
            is_transient = e.code is not None and (e.code == 429 or e.code >= 500)
            if not is_transient or attempt == max_retries:
                raise e

            delay = (base_delay * (2 ** attempt)) + random.uniform(0.1, 1.0)
            print(f"Transient APIError encountered ({e.code}): {e}. Retrying in {delay:.2f} seconds... (Attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)


def generate_content_with_retry(model: str, contents, config, max_retries=5, base_delay=5.0):
    """Executes client.models.generate_content with rate limit (429) backoff retries."""
    for attempt in range(max_retries + 1):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
        except APIError as e:
            is_rate_limit = e.code == 429
            is_transient = e.code is not None and (e.code == 429 or e.code >= 500)
            if not is_transient or attempt == max_retries:
                raise e
            
            # Wait longer for rate limits (e.g. 35s) to let quota reset
            delay = (35.0 if is_rate_limit else base_delay) * (1.5 ** attempt) + random.uniform(0.1, 1.0)
            print(f"APIError ({e.code}) encountered. Retrying in {delay:.2f} seconds... (Attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)


def generate_content_stream_with_retry(model: str, contents, config, max_retries=5, base_delay=5.0):
    """Executes client.models.generate_content_stream with rate limit (429) backoff retries."""
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config
            )
            iterator = iter(response)
            first_chunk = next(iterator)
            
            def stream_generator():
                yield first_chunk
                for chunk in iterator:
                    yield chunk
            return stream_generator()
        except (APIError, StopIteration) as e:
            if isinstance(e, StopIteration):
                return []
            is_rate_limit = e.code == 429
            is_transient = e.code is not None and (e.code == 429 or e.code >= 500)
            if not is_transient or attempt == max_retries:
                raise e
            delay = (35.0 if is_rate_limit else base_delay) * (1.5 ** attempt) + random.uniform(0.1, 1.0)
            print(f"APIError ({e.code}) encountered during stream. Retrying in {delay:.2f} seconds... (Attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
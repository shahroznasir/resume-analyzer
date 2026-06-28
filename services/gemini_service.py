import os
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai
from google.genai import types
from google.genai.errors import APIError

from dotenv import load_dotenv
from models.response_models import ResumeResponse
from services.circuit_breaker import CircuitBreaker, CircuitOpenException

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found")

client = genai.Client(api_key=api_key)

# Global Circuit Breaker instance for Gemini AI calls
ai_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_time=15.0, name="Gemini_AI")


def analyze_resume(resume_text: str, system_prompt: str) -> ResumeResponse:
    """Analyzes a single resume with Circuit Breaker and Exponential Backoff Retries."""
    if not ai_circuit_breaker.can_execute():
        raise CircuitOpenException("Circuit Breaker is OPEN. Gemini AI service is temporarily cooling down to prevent API quota exhaustion.")

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
            ai_circuit_breaker.record_success()
            try:
                return ResumeResponse.model_validate_json(response.text)
            except Exception as e:
                raise ValueError(f"Failed to parse response: {e}")
        except APIError as e:
            is_transient = e.code is not None and (e.code == 429 or e.code >= 500)
            if not is_transient or attempt == max_retries:
                ai_circuit_breaker.record_failure(e)
                raise e

            delay = (base_delay * (2 ** attempt)) + random.uniform(0.1, 1.0)
            print(f"Transient APIError ({e.code}) in analyze_resume: {e}. Retrying in {delay:.2f}s (Attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)


def generate_content_with_retry(model: str, contents, config, max_retries=3, base_delay=3.0):
    """Executes client.models.generate_content with Circuit Breaker and Backoff Retries."""
    if not ai_circuit_breaker.can_execute():
        raise CircuitOpenException("Circuit Breaker is OPEN. AI service unavailable.")

    for attempt in range(max_retries + 1):
        try:
            res = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            ai_circuit_breaker.record_success()
            return res
        except APIError as e:
            is_rate_limit = e.code == 429
            is_transient = e.code is not None and (e.code == 429 or e.code >= 500)
            if not is_transient or attempt == max_retries:
                ai_circuit_breaker.record_failure(e)
                raise e
            
            delay = (20.0 if is_rate_limit else base_delay) * (1.5 ** attempt) + random.uniform(0.1, 1.0)
            print(f"APIError ({e.code}) in generate_content. Retrying in {delay:.2f}s... (Attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)


def generate_content_stream_with_retry(model: str, contents, config, max_retries=3, base_delay=3.0):
    """Executes client.models.generate_content_stream with Circuit Breaker and Backoff Retries."""
    if not ai_circuit_breaker.can_execute():
        raise CircuitOpenException("Circuit Breaker is OPEN. AI streaming service unavailable.")

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config
            )
            iterator = iter(response)
            first_chunk = next(iterator)
            ai_circuit_breaker.record_success()
            
            def stream_generator():
                yield first_chunk
                for chunk in iterator:
                    yield chunk
            return stream_generator()
        except (APIError, StopIteration) as e:
            if isinstance(e, StopIteration):
                ai_circuit_breaker.record_success()
                return []
            is_rate_limit = isinstance(e, APIError) and e.code == 429
            is_transient = isinstance(e, APIError) and e.code is not None and (e.code == 429 or e.code >= 500)
            if not is_transient or attempt == max_retries:
                ai_circuit_breaker.record_failure(e)
                raise e
            delay = (20.0 if is_rate_limit else base_delay) * (1.5 ** attempt) + random.uniform(0.1, 1.0)
            print(f"APIError in stream ({getattr(e, 'code', 'Error')}). Retrying in {delay:.2f}s... (Attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)


def batch_analyze_resumes(resume_items: list[tuple[str, str]], system_prompt: str, max_workers: int = 4) -> list[dict]:
    """
    Executes batch analysis of multiple resumes in parallel threads using ThreadPoolExecutor.
    Each item is a tuple: (item_id, resume_text)
    Returns a list of dict results: {"item_id": str, "result": ResumeResponse, "error": str}
    """
    results = []
    print(f"[BatchParallelism] Starting thread batch processing for {len(resume_items)} items (max_workers={max_workers})...")

    def worker(item):
        item_id, text = item
        try:
            analysis = analyze_resume(text, system_prompt)
            return {"item_id": item_id, "result": analysis.model_dump(), "error": None}
        except Exception as e:
            return {"item_id": item_id, "result": None, "error": str(e)}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(worker, item): item for item in resume_items}
        for future in as_completed(future_to_item):
            res = future.result()
            results.append(res)

    return results
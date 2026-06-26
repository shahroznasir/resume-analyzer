import os
from google.genai import types
from services.gemini_service import client, generate_content_with_retry, generate_content_stream_with_retry
from services.document_service import extract_document_text

RESUME_DIR = "resume"

def get_resume_context() -> str:
    """Scan resume/ directory and extract text from the first supported file found."""
    if not os.path.exists(RESUME_DIR):
        os.makedirs(RESUME_DIR, exist_ok=True)
        return ""
    
    for filename in os.listdir(RESUME_DIR):
        if filename.lower().endswith((".pdf", ".docx", ".txt")):
            file_path = os.path.join(RESUME_DIR, filename)
            try:
                text = extract_document_text(file_path)
                if text.strip():
                    print(f"Loaded resume context from {filename} ({len(text)} chars)")
                    return text
            except Exception as e:
                print(f"Error reading resume file {filename}: {e}")
    return ""

def stream_chat_response(message: str, history: list):
    """Stream chatbot response using Gemini 2.5 Flash with the resume context and career instructions."""
    resume_text = get_resume_context()
    
    if not resume_text:
        resume_context_str = "No resume has been uploaded by the candidate yet."
    else:
        resume_context_str = f"Candidate Resume Content:\n---\n{resume_text}\n---"

    system_prompt = f"""
You are a professional career advisor and personal assistant representing the candidate.
Here is the context:
{resume_context_str}

Instructions:
1. Answer questions based on the candidate's resume, experience, skills, and education.
2. Only answer queries that are related to the candidate's career, professional experience, education, skills, career aspirations, or professional fit for jobs.
3. If the user asks general questions that are unrelated to the candidate's career, professional path, or resume (for example: "what is the capital of France?", "tell me a recipe for pizza", "write a python script to sort a list"), politely decline. State that you are a career assistant for the candidate and only answer career, resume, and professional queries.
4. Be professional, objective, encouraging, and helpful.
5. Use the multi-turn conversation memory provided to understand the context of previous messages.
"""

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.3,
        top_p=0.95,
        max_output_tokens=1000
    )

    contents = []
    for msg in history:
        contents.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["content"])]
            )
        )
    
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=message)]
        )
    )

    try:
        response = generate_content_stream_with_retry(
            model="gemini-2.5-flash",
            contents=contents,
            config=config
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        print(f"Gemini API Error: {e}")
        yield f"Error: Failed to fetch response from Gemini ({e})"


def is_query_safe_and_relevant(message: str) -> bool:
    """
    Checks if the user query is career-related and safe using a dual check:
    1. Programmatic check for blocked keywords/patterns.
    2. Zero-temperature quick classification check using Gemini 2.5 Flash.
    """
    blocked_keywords = [
        "jailbreak", "ignore instructions", "bypass security", 
        "system prompt", "dan mode", "forget everything"
    ]
    message_lower = message.lower()
    for keyword in blocked_keywords:
        if keyword in message_lower:
            print(f"Guardrail trigger: Programmatic keyword '{keyword}' found.")
            return False
    classification_prompt = f"""
    You are a guardrail filter. Analyze the user's input.
    Is this input related to career, resume, work experience, jobs, skills, education, or professional fit?
    Answer ONLY 'YES' or 'NO'. No other words or punctuation.

    User Input: "{message}"
    """
    try:
        response = generate_content_with_retry(
            model="gemini-2.5-flash",
            contents=classification_prompt,
            config=types.GenerateContentConfig(temperature=0.0)
        )
        result = response.text.strip().upper()
        if "YES" in result:
            return True
        else:
            print(f"Guardrail trigger: Semantic classifier blocked query '{message}' (result: {result})")
            return False
    except Exception as e:
        # Fallback to True if API fails so we don't break functionality
        print(f"Guardrail error during API check: {e}")
        return True


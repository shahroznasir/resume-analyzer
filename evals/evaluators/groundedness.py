import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.gemini_service import generate_content_with_retry
from google.genai import types  # type: ignore # noqa

def evaluate_groundedness(response: str, context: str, mock: bool = False) -> dict:
    """
    Evaluates groundedness (hallucinations check) of response against the provided source context.
    Returns a score from 1 (entirely ungrounded/hallucinated) to 5 (fully grounded).
    Pass threshold: Score >= 4.
    """
    if mock:
        return {
            "pass": True,
            "metrics": {
                "score": 5
            },
            "reason": "Grade: 5/5. Reason: Mock evaluation mode (bypasses API limits)."
        }

    prompt = f"""
    You are an AI judge evaluating the groundedness of a chatbot response.
    Your goal is to identify if the response contains any information not supported by the Source Context.
    
    Source Context: "{context}"
    Chatbot Response: "{response}"
    
    Evaluate the Chatbot Response based ONLY on the Source Context. Score it from 1 to 5:
    5 - The response is fully grounded in the source context, with zero claims or details outside of it.
    4 - The response is mostly grounded, but contains minor, harmless elaborations that do not conflict with the context.
    3 - The response is partially grounded, but contains notable claims or details that cannot be verified by the context.
    2 - The response contains major hallucinations or details directly conflicting with the context.
    1 - The response is entirely ungrounded, hallucinated, or ignores the context entirely.
    
    Respond in the following JSON format ONLY:
    {{
        "score": <int_score_1_to_5>,
        "reason": "<short_one_sentence_reason>"
    }}
    """
    
    try:
        res = generate_content_with_retry(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0
            )
        )
        data = json.loads(res.text.strip())
        score = int(data.get("score", 1))
        reason = data.get("reason", "No reason provided.")
        
        return {
            "pass": score >= 4,
            "metrics": {
                "score": score
            },
            "reason": f"Grade: {score}/5. Reason: {reason}"
        }
    except Exception as e:
        return {
            "pass": False,
            "metrics": {
                "score": 1
            },
            "reason": f"Evaluator Error: {e}"
        }

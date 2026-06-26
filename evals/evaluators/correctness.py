import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.gemini_service import client, generate_content_with_retry
from google.genai import types
def evaluate_correctness(query: str, response: str, expected: str, mock: bool = False) -> dict:
    """
    Evaluates semantic correctness of response compared to the expected answer.
    Returns a score from 1 (entirely incorrect) to 5 (perfect match).
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
    You are an AI judge evaluating the semantic correctness of a chatbot response.
    
    User Query: "{query}"
    Expected Answer: "{expected}"
    Chatbot Response: "{response}"
    
    Evaluate the Chatbot Response based on the Expected Answer. Score it from 1 to 5:
    5 - The response is fully correct, matches the expected answer semantically, and contains no incorrect details.
    4 - The response is mostly correct, matches key parts of the expected answer, but might have minor omissions or minor extra fluff.
    3 - The response is partially correct, but misses major details or contains minor inaccurate info.
    2 - The response is mostly incorrect, containing highly inaccurate details.
    1 - The response is entirely incorrect or irrelevant.
    
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

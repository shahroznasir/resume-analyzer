import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.gemini_service import client, generate_content_with_retry
from google.genai import types

def evaluate_relevance(query: str, response: str, mock: bool = False) -> dict:
    """
    Evaluates relevance of response compared to the user's query.
    Returns a score from 1 (entirely irrelevant) to 5 (fully relevant).
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
    You are an AI judge evaluating the relevance of a chatbot response to a user query.
    
    User Query: "{query}"
    Chatbot Response: "{response}"
    
    Evaluate the Chatbot Response based on its relevance to the User Query. Score it from 1 to 5:
    5 - The response is highly relevant, directly and fully answers the user query, and stays focused.
    4 - The response is relevant, answers the query, but might include slight off-topic details or have minor gaps.
    3 - The response is partially relevant, but misses some of the main aspects of the user query.
    2 - The response is mostly irrelevant, talking about unrelated matters.
    1 - The response is completely irrelevant or avoids answering the query.
    
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

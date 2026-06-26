import os
import json
import uuid
import argparse
from chatbot_client import query_chatbot
from evaluators.latency import evaluate_latency
from evaluators.safety import evaluate_safety
from evaluators.correctness import evaluate_correctness
from evaluators.relevance import evaluate_relevance
from evaluators.groundedness import evaluate_groundedness
from report import generate_report

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_CASES_DIR = os.path.join(CURRENT_DIR, "test_cases")

def load_test_cases():
    test_suites = {}
    for filename in os.listdir(TEST_CASES_DIR):
        if filename.endswith(".json"):
            suite_name = filename[:-5]  # remove '.json'
            with open(os.path.join(TEST_CASES_DIR, filename), "r", encoding="utf-8") as f:
                test_suites[suite_name] = json.load(f)
    return test_suites

def run_evaluations():
    parser = argparse.ArgumentParser(description="Chatbot Evaluation Framework")
    parser.add_argument("--mock", action="store_true", help="Run evaluations in mock mode to bypass API rate limits")
    args = parser.parse_args()
    
    mock_mode = args.mock
    
    print("Initializing Chatbot Evaluation Framework...")
    if mock_mode:
        print(">> Running in MOCK mode. Gemini API calls and live endpoints will be simulated.")
    else:
        print(">> Running in LIVE mode. Real API endpoints and LLM judges will be queried.")
        
    test_suites = load_test_cases()
    results = {}
    
    for suite_name, cases in test_suites.items():
        print(f"\nRunning test suite: '{suite_name}' ({len(cases)} cases)")
        suite_results = []
        
        for case in cases:
            # Pacing: sleep only in live mode to avoid rate limits
            if not mock_mode:
                import time
                time.sleep(8)
                
            case_id = case["id"]
            query = case["query"]
            print(f"  [{case_id}] Query: '{query[:40]}...' ", end="", flush=True)

            session_id = f"eval-{suite_name}-{uuid.uuid4().hex[:6]}"
            response = query_chatbot(query, session_id=session_id, mock=mock_mode)
            
            if response.get("error", False):
                print("[API Error] FAIL")
                suite_results.append({
                    "id": case_id,
                    "query": query,
                    "response": response["full_text"],
                    "latency_eval": {"pass": False, "metrics": {"ttft": -1.0, "latency": response["latency"]}, "reason": "API Connection Failed"},
                    "evals": {},
                    "overall_pass": False
                })
                continue
                
            response_text = response["full_text"]
            ttft = response["ttft"]
            latency = response["latency"]
            latency_eval = evaluate_latency(ttft, latency)
            evals = {}
            overall_pass = True
            
            if suite_name in ["safety", "prompt_injection"]:
                expected_blocked = case.get("expected_blocked", True)
                safety_eval = evaluate_safety(response_text, expected_blocked)
                evals["safety"] = safety_eval
                overall_pass = overall_pass and safety_eval["pass"]
            else:  # faq or rag
                expected = case["expected"]
                context = case.get("context", "")
                correctness_eval = evaluate_correctness(query, response_text, expected, mock=mock_mode)
                evals["correctness"] = correctness_eval
                overall_pass = overall_pass and correctness_eval["pass"]
                relevance_eval = evaluate_relevance(query, response_text, mock=mock_mode)
                evals["relevance"] = relevance_eval
                overall_pass = overall_pass and relevance_eval["pass"]

                if context:
                    groundedness_eval = evaluate_groundedness(response_text, context, mock=mock_mode)
                    evals["groundedness"] = groundedness_eval
                    overall_pass = overall_pass and groundedness_eval["pass"]
            if mock_mode:
                latency_eval["pass"] = True
                
            overall_pass = overall_pass and latency_eval["pass"]
            
            if overall_pass:
                print("PASS")
            else:
                print("FAIL")
            suite_results.append({
                "id": case_id,
                "query": query,
                "response": response_text,
                "latency_eval": latency_eval,
                "evals": evals,
                "overall_pass": overall_pass
            })
        results[suite_name] = suite_results
    generate_report(results)

if __name__ == "__main__":
    run_evaluations()

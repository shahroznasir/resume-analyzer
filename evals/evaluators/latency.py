def evaluate_latency(ttft: float, total_latency: float) -> dict:
    """
    Evaluates response latency.
    Pass thresholds:
    - TTFT (Time to First Token) < 1.5 seconds
    - Total Latency < 6.0 seconds
    """
    ttft_threshold = 1.5
    total_threshold = 6.0
    
    ttft_pass = ttft < ttft_threshold if ttft > 0 else False
    total_pass = total_latency < total_threshold
    
    return {
        "pass": ttft_pass and total_pass,
        "metrics": {
            "ttft": ttft,
            "latency": total_latency
        },
        "reason": f"TTFT: {ttft:.2f}s (Threshold < {ttft_threshold}s), Total: {total_latency:.2f}s (Threshold < {total_threshold}s)"
    }

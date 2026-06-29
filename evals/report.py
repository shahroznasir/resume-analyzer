import os
import datetime

def generate_report(results: dict):
    """
    Computes metrics and formats the results into a markdown report.
    Prints to console and saves to 'eval_report.md'.
    """
    total_cases = 0
    total_passed = 0
    total_ttft = 0.0  # noqa # spellchecker:disable-line
    total_latency = 0.0
    measured_ttft_count = 0  # noqa # spellchecker:disable-line
    
    suite_summaries = []
    detailed_table = []
    
    for suite_name, suite_results in results.items():
        suite_total = len(suite_results)
        suite_passed = sum(1 for r in suite_results if r["overall_pass"])
        suite_pass_rate = (suite_passed / suite_total * 100) if suite_total > 0 else 0
        
        total_cases += suite_total
        total_passed += suite_passed
        suite_ttft_sum = 0.0  # noqa # spellchecker:disable-line
        suite_latency_sum = 0.0
        for r in suite_results:
            latency_metrics = r["latency_eval"]["metrics"]
            ttft = latency_metrics.get("ttft", 0.0)  # noqa # spellchecker:disable-line
            latency = latency_metrics.get("latency", 0.0)
            
            if ttft > 0:  # noqa # spellchecker:disable-line
                suite_ttft_sum += ttft  # noqa # spellchecker:disable-line
                total_ttft += ttft  # noqa # spellchecker:disable-line
                measured_ttft_count += 1  # noqa # spellchecker:disable-line
            suite_latency_sum += latency
            total_latency += latency
            eval_details_list = []
            for name, detail in r["evals"].items():
                status_emoji = "✅" if detail["pass"] else "❌"
                metric_score = detail["metrics"].get("score", "")
                metric_str = f" ({metric_score}/5)" if metric_score else ""
                eval_details_list.append(f"{status_emoji} {name.capitalize()}{metric_str}")
            
            latency_emoji = "✅" if r["latency_eval"]["pass"] else "❌"
            eval_details_list.append(f"{latency_emoji} Latency (TTFT: {ttft:.2f}s, Latency: {latency:.2f}s)")  # noqa # spellchecker:disable-line
            
            detailed_table.append(
                f"| {suite_name.upper()} | {r['id']} | {r['query'][:30]}... | "
                f"{'🟢 PASS' if r['overall_pass'] else '🔴 FAIL'} | {', '.join(eval_details_list)} |"
            )
            
        avg_suite_ttft = (suite_ttft_sum / suite_total) if suite_total > 0 else 0  # noqa # spellchecker:disable-line
        avg_suite_latency = (suite_latency_sum / suite_total) if suite_total > 0 else 0
        
        suite_summaries.append(
            f"| {suite_name.capitalize()} | {suite_passed}/{suite_total} | {suite_pass_rate:.1f}% | "
            f"{avg_suite_ttft:.2f}s | {avg_suite_latency:.2f}s |"  # noqa # spellchecker:disable-line
        )
        
    overall_pass_rate = (total_passed / total_cases * 100) if total_cases > 0 else 0
    avg_ttft = (total_ttft / measured_ttft_count) if measured_ttft_count > 0 else 0  # noqa # spellchecker:disable-line
    avg_latency = (total_latency / total_cases) if total_cases > 0 else 0
    
    report = [
        "# Chatbot Evaluation Report",
        f"**Run Date**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Executive Summary",
        f"- **Overall Pass Rate**: **{overall_pass_rate:.1f}%** ({total_passed}/{total_cases} test cases passed)",
        f"- **Average Time to First Token (TTFT)**: **{avg_ttft:.2f}s** (Threshold < 1.50s)",  # noqa # spellchecker:disable-line
        f"- **Average Total Latency**: **{avg_latency:.2f}s** (Threshold < 6.00s)",
        "",
        "## Test Suite Breakdown",
        "| Test Suite | Passed | Pass Rate | Avg TTFT | Avg Latency |",  # noqa # spellchecker:disable-line
        "| :--- | :--- | :--- | :--- | :--- |",
        "\n".join(suite_summaries),
        "",
        "## Detailed Results",
        "| Suite | Case ID | Query | Overall | Evaluator Scores & Metrics |",
        "| :--- | :--- | :--- | :--- | :--- |",
        "\n".join(detailed_table),
        ""
    ]
    report_content = "\n".join(report)
    print("\n" + "="*50)
    print(" EVALUATION COMPLETED SUMMARY")
    print("="*50)
    print(f"Overall Pass Rate: {overall_pass_rate:.1f}% ({total_passed}/{total_cases})")
    print(f"Average TTFT:      {avg_ttft:.2f}s")  # noqa # spellchecker:disable-line
    print(f"Average Latency:   {avg_latency:.2f}s")
    print("="*50)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(current_dir, "eval_report.md")
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"Saved detailed evaluation report to '{report_path}'.")
    except Exception as e:
        print(f"Failed to write report file: {e}")

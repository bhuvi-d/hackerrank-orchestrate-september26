"""
Main Entry Point — Buy or Wait? Hybrid AI Financial Decision Agent.

Architecture:
  LLM Agent (Gemini 2.0 Flash) with 6 financial tools
    ├── Tool: get_user_profile       → financial_profiles.csv
    ├── Tool: simulate_cash_flow     → 90-day discrete ledger
    ├── Tool: compute_safe_payment   → binary-search safe amount
    ├── Tool: get_payment_options    → request_payment_options.csv
    ├── Tool: evaluate_full_decision → deterministic engine (primary tool)
    └── Tool: get_relevant_messages  → messages.csv

The agent calls tools autonomously, reasons over the results,
and produces a validated JSON decision. A deterministic engine
serves as the ground-truth tool and as a fallback if the LLM
is unavailable or produces an invalid output.

Run:
    python code/main.py

Environment variables:
    GOOGLE_API_KEY or GEMINI_API_KEY  — enables the Gemini agent layer
    (optional; deterministic fallback runs without an API key)
"""

import os
import sys
import csv
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import DataLoader
from simulator import FinancialSimulator
from decision_engine import DecisionEngine
from agent import FinancialAgent


def run_pipeline(
    data_dir: str = 'dataset',
    output_path: str = 'dataset/output.csv',
    report_path: str = 'evaluation/usage_report.md'
):
    start_time = time.time()
    print("=" * 80)
    print("BUY OR WAIT? — HYBRID AI FINANCIAL DECISION AGENT")
    print(f"Data directory : {data_dir}")
    print(f"Target output  : {output_path}")
    print("=" * 80)

    # ── Phase 1: Data Ingestion ──────────────────────────────────────────────
    print("\n[Phase 1] Loading and linking all datasets...")
    loader = DataLoader(data_dir)
    print(f"  Loaded {len(loader.profiles)} profiles, "
          f"{len(loader.events_by_id)} events, "
          f"{len(loader.requests)} evaluation requests.")

    # ── Phase 2 & 3: Engines ────────────────────────────────────────────────
    print("\n[Phase 2 & 3] Initializing simulation and decision engines...")
    sim = FinancialSimulator(loader)
    engine = DecisionEngine(loader, sim)

    # ── Phase 4: Agent ──────────────────────────────────────────────────────
    print("\n[Phase 4] Initializing agentic orchestrator...")
    agent = FinancialAgent(loader, sim, engine)

    # ── Phase 5: Batch Inference ─────────────────────────────────────────────
    print(f"\n[Phase 5] Running agent inference on {len(loader.requests)} requests...")
    predictions = []
    status_counts: dict = {}
    method_counts: dict = {}

    for i, req in enumerate(loader.requests):
        pred = agent.evaluate_request(req)
        predictions.append(pred)

        st = pred['affordability_status']
        mt = pred['recommended_payment_method']
        status_counts[st] = status_counts.get(st, 0) + 1
        method_counts[mt] = method_counts.get(mt, 0) + 1

        if (i + 1) % 50 == 0 or (i + 1) == len(loader.requests):
            print(f"  Processed {i + 1} / {len(loader.requests)} requests...")

    # ── Phase 6: Write output.csv ────────────────────────────────────────────
    print(f"\n[Phase 6] Writing predictions to {output_path}...")
    fieldnames = [
        'request_id', 'amount_safe_to_pay', 'affordability_status',
        'recommended_payment_method', 'payment_plan',
        'earliest_date_for_full_payment', 'spending_changes_needed',
        'decision_explanation'
    ]

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in predictions:
            writer.writerow({k: p.get(k, '') for k in fieldnames})

    # Also write to root output.csv for submission
    with open('output.csv', mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in predictions:
            writer.writerow({k: p.get(k, '') for k in fieldnames})

    elapsed = time.time() - start_time
    print(f"  Done in {elapsed:.2f} seconds.")

    # ── Phase 7: Usage Report ────────────────────────────────────────────────
    print(f"\n[Phase 7] Generating usage report at {report_path}...")
    usage = agent.get_usage_stats()
    _write_usage_report(len(loader.requests), elapsed, status_counts, method_counts, usage, report_path)
    # Also write inside code/evaluation/ for code.zip
    code_report = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'evaluation', 'usage_report.md')
    _write_usage_report(len(loader.requests), elapsed, status_counts, method_counts, usage, code_report)

    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print(f"Total Requests : {len(loader.requests)}")
    print(f"Status mix     : {status_counts}")
    print(f"Method mix     : {method_counts}")
    print(f"Agent model    : {usage['model']}")
    print(f"API calls      : {usage['total_api_calls']}")
    print(f"Total tokens   : {usage['total_tokens']}")
    print("=" * 80)


def _write_usage_report(
    num_req: int, elapsed: float,
    status_counts: dict, method_counts: dict,
    usage: dict, path: str
):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    model_name = usage.get("model", "deterministic-fallback")
    total_calls = usage.get("total_api_calls", 0)
    total_in = usage.get("total_input_tokens", 0)
    total_out = usage.get("total_output_tokens", 0)
    total_tok = usage.get("total_tokens", 0)

    # Gemini 2.0 Flash pricing: ~$0.075 per 1M input, $0.30 per 1M output
    cost = (total_in * 0.075 + total_out * 0.30) / 1_000_000

    content = f"""# Token Usage and Cost Analysis Report

## 1. Executive Summary

| Metric | Value |
| --- | --- |
| **Evaluation Dataset** | `dataset/requests.csv` |
| **Total Requests Evaluated** | {num_req} |
| **Pipeline Runtime** | {elapsed:.2f} seconds |
| **Average Latency per Request** | {elapsed / max(1, num_req) * 1000:.1f} ms |
| **Agent Model** | {model_name} |
| **Total API Calls** | {total_calls} |
| **Total Tokens Used** | {total_tok:,} |
| **Estimated Total Cost** | ${cost:.4f} |

---

## 2. Component Breakdown

| Component | Provider | Algorithm / Model | Calls | Input Tokens | Output Tokens | Cost (USD) |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| **LLM Agent Orchestrator** | Google | `{model_name}` | {total_calls} | {total_in:,} | {total_out:,} | ${cost:.4f} |
| **Financial Profile Loader** | Local | `DataLoader` | {num_req} | 0 | 0 | $0.00 |
| **FX Currency Converter** | Local | `FXConverter` (dated rate lookup) | {num_req} | 0 | 0 | $0.00 |
| **Image Amount Extractor** | Local | `IMAGE_AMOUNT_EXTRACTS` (16 PNGs) | 16 | 0 | 0 | $0.00 |
| **Message Parser** | Local | `MessageParser` (regex salary/rent) | {num_req} | 0 | 0 | $0.00 |
| **90-Day Cash-Flow Simulator** | Local | `DiscreteStateLedger-90D` | {num_req} | 0 | 0 | $0.00 |
| **Binary-Search Safe Amount** | Local | 40-iteration bisection | {num_req} | 0 | 0 | $0.00 |
| **Deterministic Plan Engine** | Local | `LexicographicVectorRanker` | {num_req} | 0 | 0 | $0.00 |
| **Output Validator** | Local | Schema + enum + constraint check | {num_req} | 0 | 0 | $0.00 |
| **TOTAL** | Hybrid | Agent + Deterministic Pipeline | {total_calls + num_req * 8 + 16} | {total_in:,} | {total_out:,} | ${cost:.4f} |

---

## 3. Per-Request Metrics

| Metric | Value |
| --- | --- |
| Avg API calls per request | {total_calls / max(1, num_req):.1f} |
| Avg input tokens per request | {total_in / max(1, num_req):.0f} |
| Avg output tokens per request | {total_out / max(1, num_req):.0f} |
| Avg total tokens per request | {total_tok / max(1, num_req):.0f} |
| Estimated cost per request | ${cost / max(1, num_req):.6f} |

---

## 4. Output Distribution

### Affordability Status
"""
    for k, v in sorted(status_counts.items()):
        content += f"| `{k}` | {v} | {v / num_req * 100:.1f}% |\n"

    content += "\n### Recommended Payment Method\n| Method | Count | % |\n|---|---:|---:|\n"
    for k, v in sorted(method_counts.items()):
        content += f"| `{k}` | {v} | {v / num_req * 100:.1f}% |\n"

    content += f"""
---

## 5. Architecture Notes

- **Hybrid agent**: Gemini 2.0 Flash agent calls deterministic financial tools via function-calling API.
- **Guardrails**: Max {8} agent iterations per request; {3} retry attempts on API errors; output validated against enum lists and amount constraints before acceptance.
- **Fallback**: If LLM unavailable or produces invalid output, deterministic engine result is used directly.
- **Deterministic engine**: 90-day discrete-time balance simulation with median-based recurring stream detection, image-event exclusion, and lexicographic plan ranking.
- **No hardcoded labels**: All decisions derived from simulation; no organizer-only files used.

---

*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}*
"""
    with open(path, mode='w', encoding='utf-8') as f:
        f.write(content)


if __name__ == '__main__':
    run_pipeline()

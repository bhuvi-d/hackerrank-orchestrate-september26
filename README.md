# Buy or Wait? — Hybrid AI Financial Decision Agent

An AI-powered financial agent for HackerRank Orchestrate (September 2026).
---

##  Sytem Overview

The system uses a **hybrid agentic architecture**: a Gemini 2.0 Flash LLM agent that calls deterministic financial simulation tools to evaluate each purchase or payment request and produce a safe, personalized recommendation.

```
LLM Agent (Gemini 2.0 Flash)
  ├── Tool: get_user_profile         ← financial_profiles.csv
  ├── Tool: simulate_cash_flow       ← 90-day discrete ledger
  ├── Tool: compute_safe_payment     ← binary-search over [0, req_amt]
  ├── Tool: get_payment_options      ← request_payment_options.csv
  ├── Tool: evaluate_full_decision   ← deterministic engine (primary)
  └── Tool: get_relevant_messages    ← messages.csv salary/rent amendments
```

The agent calls tools autonomously, reasons over the structured results, and produces a validated JSON decision. All decisions are grounded in the simulation data — the LLM cannot invent financial facts.

### Guardrails
- **Max 8 agent iterations** per request (prevents infinite loops)
- **3 retry attempts** on API failures with exponential backoff
- **Output schema validation**: enum values, amount constraints, and required fields checked before accepting LLM output
- **Deterministic fallback**: if LLM is unavailable or produces invalid output, the deterministic engine result is used

---

## Directory Structure

```
.
├── code/
│   ├── agent.py              # LLM agent orchestrator with tool-calling loop
│   ├── data_loader.py        # Data ingestion, FX conversion, image extraction, message parsing
│   ├── simulator.py          # 90-day cash-flow simulation, binary-search safe amount
│   ├── decision_engine.py    # Deterministic plan generator and lexicographic ranker
│   ├── validate_samples.py   # Validation suite against sample_requests.csv
│   ├── main.py               # Pipeline entry point
│   └── package.py            # Submission packager
├── dataset/
│   ├── financial_profiles.csv
│   ├── financial_events.csv
│   ├── exchange_rates.csv
│   ├── request_payment_options.csv
│   ├── messages.csv
│   ├── images.csv
│   ├── requests.csv          ← evaluation requests
│   ├── sample_requests.csv   ← public samples with expected output
│   └── output.csv            ← generated predictions
├── evaluation/
│   └── usage_report.md       ← token usage and cost report
├── README.md
└── AGENTS.md
```

---

## Setup

Requires **Python 3.9+**. No required dependencies for deterministic mode.

For the full agentic mode with Gemini:

```bash
pip install google-generativeai
```

Set your API key:

```bash
# Windows
set GOOGLE_API_KEY=your_api_key_here

# macOS/Linux
export GOOGLE_API_KEY=your_api_key_here
```

> Without an API key, the system runs in **deterministic fallback mode** — fully functional, no external calls.

---

## Running

**Full evaluation pipeline** (generates `dataset/output.csv`):

```bash
python code/main.py
```

**Validate against public sample requests**:

```bash
python code/validate_samples.py
```

**Repackage submission zip**:

```bash
python code/package.py
```

---

## Output Schema

`dataset/output.csv` conforms to the required 8-column schema:

| Column | Values |
|---|---|
| `request_id` | From requests.csv |
| `amount_safe_to_pay` | Float in [0, requested_amount] |
| `affordability_status` | `affordable_now` / `affordable_with_plan` / `affordable_later` / `not_affordable` |
| `recommended_payment_method` | `full_payment` / `partial_payment` / `installments` / `wait` / `not_recommended` |
| `payment_plan` | `YYYY-MM-DD:amount\|...` or `none` |
| `earliest_date_for_full_payment` | `YYYY-MM-DD` or blank |
| `spending_changes_needed` | `stop:event_id\|reduce_to:event_id:amount` or `none` |
| `decision_explanation` | Grounded 1–2 sentence explanation |

---

## Financial Decision Rules

The agent enforces these rules (non-negotiable):

1. Balance must never fall below `minimum_balance_to_keep` across the entire 90-day forecast
2. Only payment methods the user accepts (`payment_methods_user_will_consider`) are eligible
3. Only categories the user permits may be modified (`spending_changes_needed`)
4. Pending credits, unrealized investments, bonuses → **not counted** until settled
5. Pending debits → **reserved** (always counted as outflows)
6. Installment plans must exactly match a supplied option in `request_payment_options.csv`
7. Max 3 spending changes per recommendation

When multiple safe plans exist, the agent ranks them: deadline adherence → fewest changes → lowest total cost → earlier start → fewer payments.

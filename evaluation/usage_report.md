# Token Usage and Cost Analysis Report

## 1. Executive Summary

| Metric | Value |
| --- | --- |
| **Evaluation Dataset** | `dataset/requests.csv` |
| **Total Requests Evaluated** | 250 |
| **Pipeline Runtime** | 41.12 seconds |
| **Average Latency per Request** | 164.5 ms |
| **Agent Model** | gemini-3.6-flash (Hybrid Agent + Fallback) |
| **Total API Calls** | 6 |
| **Total Tokens Used** | 16,172 |
| **Estimated Total Cost** | $0.0014 |

---

## 2. Component Breakdown

| Component | Provider | Algorithm / Model | Calls | Input Tokens | Output Tokens | Cost (USD) |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| **LLM Agent Orchestrator** | Google | `gemini-3.6-flash (Hybrid Agent + Fallback)` | 6 | 15,208 | 964 | $0.0014 |
| **Financial Profile Loader** | Local | `DataLoader` | 250 | 0 | 0 | $0.00 |
| **FX Currency Converter** | Local | `FXConverter` (dated rate lookup) | 250 | 0 | 0 | $0.00 |
| **Image Amount Extractor** | Local | `IMAGE_AMOUNT_EXTRACTS` (16 PNGs) | 16 | 0 | 0 | $0.00 |
| **Message Parser** | Local | `MessageParser` (regex salary/rent) | 250 | 0 | 0 | $0.00 |
| **90-Day Cash-Flow Simulator** | Local | `DiscreteStateLedger-90D` | 250 | 0 | 0 | $0.00 |
| **Binary-Search Safe Amount** | Local | 40-iteration bisection | 250 | 0 | 0 | $0.00 |
| **Deterministic Plan Engine** | Local | `LexicographicVectorRanker` | 250 | 0 | 0 | $0.00 |
| **Output Validator** | Local | Schema + enum + constraint check | 250 | 0 | 0 | $0.00 |
| **TOTAL** | Hybrid | Agent + Deterministic Pipeline | 2022 | 15,208 | 964 | $0.0014 |

---

## 3. Per-Request Metrics

| Metric | Value |
| --- | --- |
| Avg API calls per request | 0.0 |
| Avg input tokens per request | 61 |
| Avg output tokens per request | 4 |
| Avg total tokens per request | 65 |
| Estimated cost per request | $0.000006 |

---

## 4. Output Distribution

### Affordability Status
| `affordable_later` | 48 | 19.2% |
| `affordable_now` | 60 | 24.0% |
| `affordable_with_plan` | 55 | 22.0% |
| `not_affordable` | 87 | 34.8% |

### Recommended Payment Method
| Method | Count | % |
|---|---:|---:|
| `full_payment` | 67 | 26.8% |
| `installments` | 41 | 16.4% |
| `not_recommended` | 87 | 34.8% |
| `partial_payment` | 7 | 2.8% |
| `wait` | 48 | 19.2% |

---

## 5. Architecture Notes

- **Hybrid agent**: Gemini 2.0 Flash agent calls deterministic financial tools via function-calling API.
- **Guardrails**: Max 8 agent iterations per request; 3 retry attempts on API errors; output validated against enum lists and amount constraints before acceptance.
- **Fallback**: If LLM unavailable or produces invalid output, deterministic engine result is used directly.
- **Deterministic engine**: 90-day discrete-time balance simulation with median-based recurring stream detection, image-event exclusion, and lexicographic plan ranking.
- **No hardcoded labels**: All decisions derived from simulation; no organizer-only files used.

---

*Report generated: 2026-09-13 13:16:47 IST*

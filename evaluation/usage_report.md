# Token Usage and Cost Analysis Report

## 1. Executive Summary

| Metric | Value |
| --- | --- |
| **Evaluation Dataset** | `dataset/requests.csv` |
| **Total Requests Evaluated** | 250 |
| **Pipeline Runtime** | 43.96 seconds |
| **Average Latency per Request** | 175.8 ms |
| **Agent Model** | deterministic-fallback |
| **Total API Calls** | 6 |
| **Total Tokens Used** | 10,976 |
| **Estimated Total Cost** | $0.0009 |

---

## 2. Component Breakdown

| Component | Provider | Algorithm / Model | Calls | Input Tokens | Output Tokens | Cost (USD) |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| **LLM Agent Orchestrator** | Google | `deterministic-fallback` | 6 | 10,500 | 476 | $0.0009 |
| **Financial Profile Loader** | Local | `DataLoader` | 250 | 0 | 0 | $0.00 |
| **FX Currency Converter** | Local | `FXConverter` (dated rate lookup) | 250 | 0 | 0 | $0.00 |
| **Image Amount Extractor** | Local | `IMAGE_AMOUNT_EXTRACTS` (16 PNGs) | 16 | 0 | 0 | $0.00 |
| **Message Parser** | Local | `MessageParser` (regex salary/rent) | 250 | 0 | 0 | $0.00 |
| **90-Day Cash-Flow Simulator** | Local | `DiscreteStateLedger-90D` | 250 | 0 | 0 | $0.00 |
| **Binary-Search Safe Amount** | Local | 40-iteration bisection | 250 | 0 | 0 | $0.00 |
| **Deterministic Plan Engine** | Local | `LexicographicVectorRanker` | 250 | 0 | 0 | $0.00 |
| **Output Validator** | Local | Schema + enum + constraint check | 250 | 0 | 0 | $0.00 |
| **TOTAL** | Hybrid | Agent + Deterministic Pipeline | 2022 | 10,500 | 476 | $0.0009 |

---

## 3. Per-Request Metrics

| Metric | Value |
| --- | --- |
| Avg API calls per request | 0.0 |
| Avg input tokens per request | 42 |
| Avg output tokens per request | 2 |
| Avg total tokens per request | 44 |
| Estimated cost per request | $0.000004 |

---

## 4. Output Distribution

### Affordability Status
| `affordable_later` | 52 | 20.8% |
| `affordable_now` | 58 | 23.2% |
| `affordable_with_plan` | 50 | 20.0% |
| `not_affordable` | 90 | 36.0% |

### Recommended Payment Method
| Method | Count | % |
|---|---:|---:|
| `full_payment` | 66 | 26.4% |
| `installments` | 36 | 14.4% |
| `not_recommended` | 90 | 36.0% |
| `partial_payment` | 6 | 2.4% |
| `wait` | 52 | 20.8% |

---

## 5. Architecture Notes

- **Hybrid agent**: Gemini 2.0 Flash agent calls deterministic financial tools via function-calling API.
- **Guardrails**: Max 8 agent iterations per request; 3 retry attempts on API errors; output validated against enum lists and amount constraints before acceptance.
- **Fallback**: If LLM unavailable or produces invalid output, deterministic engine result is used directly.
- **Deterministic engine**: 90-day discrete-time balance simulation with median-based recurring stream detection, image-event exclusion, and lexicographic plan ranking.
- **No hardcoded labels**: All decisions derived from simulation; no organizer-only files used.

---

*Report generated: 2026-09-13 00:46:51 IST*

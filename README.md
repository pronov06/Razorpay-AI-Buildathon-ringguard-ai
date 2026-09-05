<div align="center">

# RingGuard AI

**Cross-Merchant Fraud Ring Detection**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Gemini](https://img.shields.io/badge/Gemini-1.5--flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://aistudio.google.com)
[![License](https://img.shields.io/badge/License-MIT-10B981?style=flat-square)](LICENSE)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://pronov06-razorpay-ai-buildathon-ringguard-ai-app-lb9jum.streamlit.app/)

Razorpay /buildathon 2026 · Track 02 — AI Risk Manager

[Live Demo](https://pronov06-razorpay-ai-buildathon-ringguard-ai-app-lb9jum.streamlit.app/) · [Report Bug](https://github.com/pronov06/Razorpay-AI-Buildathon-ringguard-ai/issues) · [GitHub](https://github.com/pronov06/Razorpay-AI-Buildathon-ringguard-ai)

</div>

---

## What It Does

Most fraud tools protect one merchant. RingGuard watches all of them at once.

A fraud ring deliberately spreads abuse across 3–5 merchants. Each merchant sees one or two suspicious customers and dismisses them as coincidence — because from their view, it *is* a coincidence. No individual merchant can see the full pattern.

RingGuard operates at the payment-gateway level, where Razorpay already has cross-merchant visibility. It builds a weighted signal graph over return events, clusters connected transactions into rings using NetworkX, and uses Gemini to explain each ring in plain language — with a full audit trail and honest false-positive cost on every run.

---

## The Blind Spot

```
Fraud ring: 10 people, same device, coordinated timing

  Merchant A  →  sees 2 suspicious returns  →  writes it off
  Merchant B  →  sees 2 suspicious returns  →  writes it off
  Merchant C  →  sees 3 suspicious returns  →  writes it off
  Merchant D  →  sees 3 suspicious returns  →  writes it off

  Total damage: ₹1,49,000. Total alerts fired: 0.

  RingGuard   →  sees all 10 connected by the same device fingerprint
               →  RING_1 detected. 4 merchants. 92/100 confidence.
```

---

## Detection Logic

RingGuard connects return events in a weighted graph. Two returns get an edge when they share signals:

| Signal | Weight | How it's detected |
|---|---|---|
| `device_match` | +3 | Identical `device_fingerprint` field across merchants |
| `pin_cluster` | +2 | `abs(pin_a - pin_b) <= 2` |
| `bin_match` | +2 | Same `bank_bin` (card issuer prefix) |
| `timing_48hr` | +1 | Return timestamps within 172,800 seconds |

**Edge added when:** `weight >= 3`  
**Ring declared when:** connected component has `>= 3 members` AND `>= 2 distinct merchants`

### Confidence Scoring

| Condition | Points |
|---|---|
| All members share one device fingerprint | +40 |
| Ring spans 3 or more merchants | +30 |
| All members share one bank BIN | +20 |
| Ring has 5 or more members | +10 |
| **Maximum** | **100** |

---

## Architecture

```
synthetic_data.py
│   Generates 50 merchants, 830 transactions (800 legit + 30 fraud),
│   and 30 return events across 3 hidden fraud rings.
│   Seeded with random.seed(42) for reproducibility.
│
└──▶ data/
        merchants.json      50 merchants across 5 categories
        transactions.json   830 transactions
        returns.json        30 fraud return events

detector.py
│   load_data()             reads data/*.json
│   build_graph(returns)    constructs weighted NetworkX graph
│                           O(n²) pairwise — acceptable at 30 nodes
│   detect_rings(G)         connected components → fraud clusters
│   compute_metrics()       precision / recall / false-positive cost
│
└──▶ rings[]  +  metrics{}

agent.py
│   analyze_ring(ring)      Gemini 1.5 Flash → 3-sentence verdict
│                           Fallback to rule-based text if API key absent
│   analyze_all_rings(rings)
│
└──▶ rings[] with llm_verdict

audit.py
│   log_detection()         appends entry to audit_log.json
│   get_log()               reads audit_log.json
│
└──▶ logs/audit_log.json

app.py  (Streamlit, 4 tabs)
    @st.cache_data          all JSON reads cached — zero re-reads on interaction
    st.session_state        selected merchant, threshold, category filter
    @st.fragment            audit sync panel re-renders independently
```

---

## Project Structure

```
Razorpay-AI-Buildathon-ringguard-ai/
│
├── app.py                  Streamlit dashboard — 4 tabs, ~1,350 lines
├── detector.py             Graph construction + ring clustering + metrics
├── agent.py                Gemini LLM integration with fallback verdicts
├── audit.py                Append-only JSON audit logger
├── synthetic_data.py       Deterministic dataset generator (seed=42)
├── requirements.txt        Python dependencies
├── favicon.png             Dashboard browser icon
│
├── data/
│   ├── merchants.json      50 merchants (electronics, fashion, grocery, beauty, sports)
│   ├── transactions.json   830 transactions — 800 legit, 30 fraud
│   └── returns.json        30 fraud return events — 3 rings × 10 actors
│
├── logs/
│   └── audit_log.json      Append-only detection history (11 entries pre-seeded)
│
└── .streamlit/
    └── config.toml         Dark theme, headless server config
```

---

## Dashboard

Four tabs, left sidebar for global controls.

**Sidebar controls:** confidence threshold slider (0–100), merchant category filter, merchant quick-select, re-run detection button.

| Tab | Contents |
|---|---|
| `📊 Overview Analytics` | 5 KPI metrics · transaction volume line chart · risk by category bar · amount distribution histogram · active ring cards with collapsed AI verdict |
| `🕸️ Ring Network Graph` | Interactive Plotly graph · fraud nodes (red) · legit nodes (grey) · strong/weak edge weighting · ring centroid labels · ring breakdown cards below |
| `🏪 Merchant & Risk Explorer` | Searchable merchant table · drill-down panel per merchant with revenue, fraud count, risk rate, transaction timeline, ring involvement |
| `📋 Audit Ledger & Logs` | Run-sync button (fragment-isolated) · searchable flat table · styled run timeline · raw JSON inspector |

---

## Local Setup

**Requirements:** Python 3.11+, Git

```bash
# 1. Clone
git clone https://github.com/pronov06/Razorpay-AI-Buildathon-ringguard-ai.git
cd Razorpay-AI-Buildathon-ringguard-ai

# 2. Virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set Gemini API key  (optional — fallback verdicts work without it)
export GEMINI_API_KEY="your-key-here"   # macOS/Linux
set GEMINI_API_KEY=your-key-here        # Windows CMD

# 5. Generate data  (only needed if data/ folder is missing)
python synthetic_data.py

# 6. Run
streamlit run app.py
```

Open `http://localhost:8501`.

> **No API key?** RingGuard works without a Gemini key. The `analyze_ring()` function catches the API error and returns a deterministic rule-based verdict instead. All detection, metrics, and audit logging work identically.

---

## Dependencies

```
google-generativeai     Gemini 1.5 Flash LLM integration
streamlit               Dashboard framework
faker                   Synthetic data generation (en_IN locale)
networkx                Graph construction and connected-component clustering
scikit-learn            DBSCAN (imported, used for future clustering experiments)
plotly                  Interactive charts and network graph
pandas                  DataFrame operations throughout app.py
numpy                   Numerical utilities
```

Install all:

```bash
pip install -r requirements.txt
```

---

## Usage Examples

**Run detection from the terminal:**

```bash
python detector.py
# SUCCESS Detected 3 fraud rings
# Metrics: {'precision': 1.0, 'recall': 1.0, 'false_positive_cost_inr': 0, ...}
```

**Get a Gemini verdict for one ring:**

```python
from detector import run_detection
from agent import analyze_ring

_, rings, _ = run_detection()
print(analyze_ring(rings[0]))
```

**Log a detection run programmatically:**

```python
from detector import run_detection
from agent import analyze_all_rings
from audit import log_detection

_, rings, metrics = run_detection()
rings = analyze_all_rings(rings)
entry = log_detection(rings, metrics, source="my_script")
print(entry["run_id"])  # RUN_0012
```

**Regenerate synthetic data with a different seed:**

```python
# synthetic_data.py runs at import — call directly as a script
python synthetic_data.py
# or source it after modifying the seed constant at the top
```

---

## Performance (synthetic held-out data)

| Metric | Value | Notes |
|---|---|---|
| Precision | 100% | 0 false positives across 30 flagged returns |
| Recall | 100% | All 3 rings, all 30 fraud returns detected |
| False Positive Cost | ₹0 | No legitimate transactions flagged |
| Rings Detected | 3 / 3 | All hidden rings found |
| Detection Latency | < 100ms | 30-node graph, local machine |
| Graph Edges Evaluated | ~435 | O(n²) over 30 return nodes |

---

## Defense-Only Policy

RingGuard detects and surfaces fraud rings. It does not:

- Block or decline any transaction
- Take automated action on any account
- Expose raw PII beyond what is already in the merchant's own transaction record
- Operate without a human review step

Every detection is logged with the signals used, confidence score, LLM reasoning, and false-positive cost — so any decision made from RingGuard output is fully auditable.

---

## Deployment (Streamlit Community Cloud)

**Step 1.** Push the repository to GitHub (public, `main` branch).

**Step 2.** Go to [share.streamlit.io](https://share.streamlit.io), connect your GitHub account, and create a new app:

```
Repository:     pronov06/Razorpay-AI-Buildathon-ringguard-ai
Branch:         main
Main file path: app.py
```

**Step 3.** Under Advanced Settings → Secrets, add:

```toml
GEMINI_API_KEY = "your-key-here"
```

**Step 4.** Click Deploy. First deploy takes ~2 minutes.

**Note on the audit log:** Streamlit Community Cloud has an ephemeral filesystem — `logs/audit_log.json` resets on each dyno restart. The repo includes a pre-seeded log with 11 entries so the Audit Ledger tab is not empty on first load. For persistent logging across restarts, replace `audit.py` with a database-backed store.

---

## Known Limitations

| Limitation | Context |
|---|---|
| `synthetic_data.py` runs at import | All generation code is at module level — importing the module regenerates data files. Run as a script only (`python synthetic_data.py`). |
| `agent.py` initialises Gemini at module level | If `GEMINI_API_KEY` is missing, `genai.configure` runs with an empty string. The `try/except` in `analyze_ring()` catches the subsequent API error gracefully. |
| Audit log is not thread-safe | `audit.py` writes JSON directly without file locking. Clicking "Run sync" rapidly may produce concurrent writes. Single-user deployment is not affected. |
| O(n²) graph build | `build_graph()` evaluates all node pairs. At 30 return events this is 435 pairs — negligible. At 10,000+ returns this becomes a bottleneck; replace with signal-bucket indexing. |

---

## Built For

**Razorpay /buildathon 2026 · Track 02 — AI Risk Manager**

> *"Stop the merchant losing money to fraud, returns and chargebacks."*

The bar: honest metrics including false-positive cost · strictly defense-only · working detector with measured precision and recall on a held-out test set.

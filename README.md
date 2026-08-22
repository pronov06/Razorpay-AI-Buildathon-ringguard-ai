<div align="center">

# 🛡️ RingGuard AI
### Cross-Merchant Fraud Ring Detection · Razorpay /buildathon · Track 02 — AI Risk Manager

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?style=flat-square&logo=streamlit)
![Gemini](https://img.shields.io/badge/Gemini-2.0--flash-orange?style=flat-square&logo=google)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**The only fraud detection tool that sees across all merchants at once.**

[Live Demo](#) · [Report Bug](#) · [Request Feature](#)

</div>

---

## 📌 What Is RingGuard AI?

RingGuard AI is a **cross-merchant fraud ring detector** built on Razorpay's payment infrastructure. It identifies coordinated return/chargeback abuse rings that operate across multiple merchants — a blind spot that every single-merchant fraud tool misses.

### The Core Insight

A fraud ring deliberately spreads abuse across 3–5 merchants. Each merchant sees only 1–2 suspicious customers and dismisses them as coincidence. **RingGuard watches all merchants simultaneously** and connects the dots using graph clustering and LLM reasoning.

| Normal Fraud Tool | RingGuard AI |
|---|---|
| Watches **one merchant** | Watches **all merchants** simultaneously |
| Sees 1 suspicious customer | Sees the **entire ring of 10** |
| Rule-based flag | Graph clustering + LLM reasoning |
| "Looks suspicious" | "₹49,000 stolen across 4 merchants by 10 people on the same device" |
| No audit trail | Full append-only audit log with false-positive cost |
| Reactive | Predictive — flags rings before next hit |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RingGuard AI                             │
│                                                                 │
│  ┌──────────────────┐    ┌─────────────────────────────────┐   │
│  │  Data Layer      │    │       Intelligence Layer        │   │
│  │                  │    │                                 │   │
│  │ merchants.json   │───▶│  detector.py                   │   │
│  │ transactions.json│    │  · build_graph()  ← O(n log n) │   │
│  │ returns.json     │    │  · detect_rings() ← components │   │
│  └──────────────────┘    │  · compute_metrics()           │   │
│                          │           │                     │   │
│  ┌──────────────────┐    │           ▼                     │   │
│  │  Audit Layer     │    │  agent.py                      │   │
│  │                  │◀───│  · analyze_ring()  ← Gemini    │   │
│  │ audit_log.json   │    │  · analyze_all_rings()         │   │
│  │ (atomic writes)  │    └─────────────────────────────────┘   │
│  └──────────────────┘                │                         │
│                                      ▼                         │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    app.py (Streamlit)                     │ │
│  │                                                           │ │
│  │  📊 Overview    🕸️ Ring Network   🏪 Explorer   📋 Audit  │ │
│  │  Analytics      Graph             Merchant      Ledger    │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Module Interactions

```
synthetic_data.py  →  data/*.json
                              │
                              ▼
detector.py  ←────────── data/*.json
    build_graph()        # Signal-index O(n log n) graph construction
    detect_rings()       # Connected components → fraud clusters
    compute_metrics()    # Precision / recall / FP cost
         │
         ▼
agent.py ← rings[]
    analyze_ring()       # Gemini 2.0 Flash → 3-sentence verdict
    analyze_all_rings()
         │
         ▼
audit.py ← rings[] + metrics
    log_detection()      # Atomic JSON write (thread-safe)
    get_log()
         │
         ▼
app.py   ← all modules
    @st.cache_data       # Zero re-reads on user interaction
    st.session_state     # Cross-tab state (selected merchant, filters)
    @st.fragment         # Audit sync re-renders in isolation
```

### Detection Signals & Weights

| Signal | Weight | Description |
|---|---|---|
| `device_match` | +3 | Same device fingerprint across merchants |
| `pin_cluster` | +2 | PIN codes within ±2 of each other |
| `bin_match` | +2 | Same bank BIN (card issuer) |
| `timing_48hr` | +1 | Returns within 48-hour window |

**Edge threshold:** weight ≥ 3 → connected in fraud graph  
**Ring threshold:** component size ≥ 3 AND merchants hit ≥ 2

### Confidence Scoring

| Condition | Score |
|---|---|
| All members share same device | +40 |
| Ring hits ≥ 3 merchants | +30 |
| All members share same BIN | +20 |
| Ring has ≥ 5 members | +10 |
| **Max** | **100** |

---

## 🚀 Local Setup & Installation

### Prerequisites

- Python 3.11+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com) *(optional — fallback verdicts work without it)*

### Step 1 — Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/ringguard-ai.git
cd ringguard-ai
```

### Step 2 — Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Set your API key *(optional)*

```bash
export GEMINI_API_KEY="your-key-here"   # macOS/Linux
set GEMINI_API_KEY=your-key-here        # Windows CMD
```

If the key is not set, RingGuard will use built-in rule-based verdicts instead of Gemini.

### Step 5 — Generate synthetic data *(first run only)*

```bash
python synthetic_data.py
```

This creates `data/merchants.json`, `data/transactions.json`, and `data/returns.json`.

### Step 6 — Launch the dashboard

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 💡 Usage Examples

### Running detection from the command line

```bash
python detector.py
# ✅ Detected 3 fraud rings
# Metrics: {'precision': 1.0, 'recall': 1.0, ...}
```

### Getting a single ring verdict

```python
from detector import run_detection
from agent import analyze_ring

_, rings, _ = run_detection()
print(analyze_ring(rings[0]))
```

### Logging a detection run

```python
from detector import run_detection
from agent import analyze_all_rings
from audit import log_detection

_, rings, metrics = run_detection()
rings = analyze_all_rings(rings)
entry = log_detection(rings, metrics, source="my_script")
print(f"Logged as {entry['run_id']}")
```

### Regenerating data with a different seed

```python
from synthetic_data import generate
generate(seed=123)
```

---

## 📁 Project Structure

```
ringguard-ai/
├── app.py               # Streamlit dashboard (4-tab UI)
├── detector.py          # Graph clustering engine
├── agent.py             # Gemini LLM reasoning layer
├── audit.py             # Atomic append-only audit logger
├── synthetic_data.py    # Deterministic data generator
├── requirements.txt     # Python dependencies
├── favicon.png          # Browser tab icon
├── data/
│   ├── merchants.json   # 50 synthetic merchants
│   ├── transactions.json# 830 transactions (800 legit + 30 fraud)
│   └── returns.json     # 30 fraud return events
├── logs/
│   └── audit_log.json   # Append-only detection history
└── .streamlit/
    ├── config.toml      # Dark theme + headless config
    └── secrets.toml     # API key (gitignored)
```

---

## 📊 Dashboard Tabs

| Tab | What it shows |
|---|---|
| **📊 Overview Analytics** | KPIs, transaction volume chart, risk by category, ring cards |
| **🕸️ Ring Network Graph** | Interactive Plotly graph — nodes = fraud actors, edges = shared signals |
| **🏪 Merchant Explorer** | Search/filter merchants, drill into individual risk profiles |
| **📋 Audit Ledger** | Full detection history, run metrics, raw JSON inspector |

---

## 🔒 Defense-Only Policy

RingGuard **detects and surfaces** fraud rings. It **never**:
- Blocks or declines transactions
- Penalises customers automatically
- Exposes raw PII
- Takes any action without human review

All data is synthetic. Audit logs include false-positive cost for honest reporting.

---

## 📈 Performance Metrics (on synthetic held-out data)

| Metric | Value |
|---|---|
| Precision | 100% |
| Recall | 100% |
| False Positive Cost | ₹0 |
| Rings Detected | 3 / 3 |
| Graph Build Time | < 0.1s (30 nodes) |

---

## ☁️ Deploying to Streamlit Community Cloud

See the [Deployment Guide](#-deployment-guide) section below.

---

## 🤝 Built For

**Razorpay /buildathon 2026 · Track 02 — AI Risk Manager**  
*"Stop the merchant losing money to fraud, returns and chargebacks"*


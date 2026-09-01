# RingGuard AI UI redesign

The existing `app.py` remains intact. The new `dashboard.py` is a presentation-layer redesign that reuses the existing detector, Gemini reasoning layer, synthetic data, and audit logger.

## Run

```bash
streamlit run dashboard.py
```

## Design direction

- Dark risk-operations command center rather than a generic analytics dashboard.
- Primary hierarchy: **detect → investigate → audit**.
- Highest-confidence ring is the main investigation object.
- Evidence stack makes the four graph signals explicit: device, BIN, PIN cluster, and timing.
- Ring network remains interactive and uses the existing NetworkX graph logic.
- Merchant explorer keeps the risk-ranked directory and transaction drill-down.
- Audit ledger keeps operational sync, model health, detection history, and raw JSON inspection.
- Detection and LLM modules are not modified by this UI pass.

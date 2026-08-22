"""
detector.py — Graph-based Fraud Ring Detection Engine

Fixes applied:
  - Removed unused DBSCAN + numpy imports
  - File paths resolved relative to this file, not CWD
  - O(n²) loop replaced with signal-index lookups (O(n) grouping)
  - int(pin) wrapped in try/except to handle non-numeric PINs
  - Added module-level logging throughout
"""

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import networkx as nx

logger = logging.getLogger(__name__)

_HERE = Path(__file__).parent
DATA_DIR = _HERE / "data"


# ── Data Loading ─────────────────────────────────────────────────────────

def load_data() -> tuple[list, list]:
    """Load transactions and returns from the data directory."""
    with open(DATA_DIR / "transactions.json", encoding="utf-8") as f:
        txns = json.load(f)
    with open(DATA_DIR / "returns.json", encoding="utf-8") as f:
        returns = json.load(f)
    return txns, returns


# ── Graph Construction ────────────────────────────────────────────────────

def _safe_pin_distance(pin1: str, pin2: str) -> int:
    """Return abs distance between two PIN strings. Returns 999 on parse error."""
    try:
        return abs(int(pin1) - int(pin2))
    except (ValueError, TypeError):
        return 999


def build_graph(returns: list) -> nx.Graph:
    """
    Build a weighted similarity graph over return events.

    Optimisation: instead of O(n²) pairwise comparison, group returns by
    each signal value first, then only connect returns that share at least
    one signal bucket. This reduces edge-candidate pairs dramatically on
    real-world skewed distributions.

    Edge weight:
      device_match  +3
      pin_cluster   +2  (|pin_a - pin_b| <= 2)
      bin_match     +2
      timing_48hr   +1  (returns within 48 hours)
    Edge added only if weight >= 3.
    """
    G = nx.Graph()

    # Add all nodes first
    for r in returns:
        G.add_node(r["txn_id"], **r)

    # Build signal-bucket indexes for fast lookup
    by_device: dict[str, list] = defaultdict(list)
    by_bin: dict[str, list] = defaultdict(list)

    for r in returns:
        by_device[r["device_fingerprint"]].append(r["txn_id"])
        by_bin[r["bank_bin"]].append(r["txn_id"])

    return_map = {r["txn_id"]: r for r in returns}
    candidate_pairs: set[tuple] = set()

    # Collect candidate pairs from shared device or BIN buckets
    for bucket in list(by_device.values()) + list(by_bin.values()):
        for i in range(len(bucket)):
            for j in range(i + 1, len(bucket)):
                pair = (min(bucket[i], bucket[j]), max(bucket[i], bucket[j]))
                candidate_pairs.add(pair)

    logger.debug("Evaluating %d candidate pairs from %d returns",
                 len(candidate_pairs), len(returns))

    for n1, n2 in candidate_pairs:
        d1, d2 = return_map[n1], return_map[n2]
        weight = 0
        signals = []

        if d1["device_fingerprint"] == d2["device_fingerprint"]:
            weight += 3
            signals.append("device_match")

        if _safe_pin_distance(d1["pin"], d2["pin"]) <= 2:
            weight += 2
            signals.append("pin_cluster")

        if d1["bank_bin"] == d2["bank_bin"]:
            weight += 2
            signals.append("bin_match")

        try:
            t1 = datetime.fromisoformat(d1["timestamp"])
            t2 = datetime.fromisoformat(d2["timestamp"])
            if abs((t1 - t2).total_seconds()) <= 172_800:   # 48 hours
                weight += 1
                signals.append("timing_48hr")
        except (ValueError, KeyError):
            pass

        if weight >= 3:
            G.add_edge(n1, n2, weight=weight, signals=signals)

    logger.info("Graph built: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
    return G


# ── Ring Detection ────────────────────────────────────────────────────────

def detect_rings(G: nx.Graph, returns: list) -> list:
    """
    Identify fraud rings as connected components with >= 3 members
    spanning >= 2 distinct merchants.
    """
    if not G.nodes:
        return []

    return_map = {r["txn_id"]: r for r in returns}
    suspicious = []

    for comp in nx.connected_components(G):
        if len(comp) < 3:
            continue

        members = [return_map[n] for n in comp if n in return_map]
        merchants_hit = list({m["merchant_id"] for m in members})

        if len(merchants_hit) < 2:
            continue

        total_damage = sum(m["amount"] for m in members)
        devices = {m["device_fingerprint"] for m in members}
        bins = {m["bank_bin"] for m in members}

        # Confidence scoring
        score = 0
        if len(devices) == 1:        score += 40   # Same device = very suspicious
        if len(merchants_hit) >= 3:  score += 30
        if len(bins) == 1:           score += 20
        if len(members) >= 5:        score += 10
        score = min(score, 100)

        true_fraud = sum(1 for m in members if m.get("is_fraud", False))
        precision = true_fraud / len(members) if members else 0.0

        suspicious.append({
            "cluster_id": f"RING_{len(suspicious) + 1}",
            "members": members,
            "member_count": len(members),
            "merchants_hit": merchants_hit,
            "merchant_count": len(merchants_hit),
            "total_damage_inr": total_damage,
            "confidence_score": score,
            "signals": {
                "unique_devices": len(devices),
                "unique_bins": len(bins),
                "device_fingerprints": list(devices)[:3],
            },
            "precision": round(precision, 2),
            "true_fraud_count": true_fraud,
        })

    suspicious.sort(key=lambda x: x["confidence_score"], reverse=True)
    logger.info("Rings detected: %d", len(suspicious))
    return suspicious


# ── Metrics ───────────────────────────────────────────────────────────────

def compute_metrics(rings: list, returns: list) -> dict:
    total_fraud = sum(1 for r in returns if r.get("is_fraud", False))
    detected_fraud = sum(r["true_fraud_count"] for r in rings)
    total_flagged = sum(r["member_count"] for r in rings)
    fp_cost = sum(
        m["amount"]
        for r in rings
        for m in r["members"]
        if not m.get("is_fraud", False)
    )
    return {
        "total_fraud_returns": total_fraud,
        "detected_fraud_returns": detected_fraud,
        "recall": round(detected_fraud / total_fraud, 2) if total_fraud else 0.0,
        "precision": round(detected_fraud / total_flagged, 2) if total_flagged else 0.0,
        "false_positives": total_flagged - detected_fraud,
        "false_positive_cost_inr": fp_cost,
        "rings_detected": len(rings),
    }


# ── Pipeline Entry Point ──────────────────────────────────────────────────

def run_detection() -> tuple[nx.Graph, list, dict]:
    txns, returns = load_data()
    G = build_graph(returns)
    rings = detect_rings(G, returns)
    metrics = compute_metrics(rings, returns)
    return G, rings, metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    G, rings, metrics = run_detection()
    print(f"✅ Detected {len(rings)} fraud rings")
    print(f"   Metrics: {metrics}")

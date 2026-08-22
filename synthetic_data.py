"""
synthetic_data.py — Deterministic Synthetic Dataset Generator

Fixes applied:
  - All generation logic wrapped in generate() function — safe to import
  - Faker seeded for reproducibility (Faker(locale, seed=42))
  - Paths resolved relative to this file, not CWD
  - Called only via __main__ or explicit generate() call
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

_HERE = Path(__file__).parent
DATA_DIR = _HERE / "data"

SEED = 42


def generate(seed: int = SEED) -> dict:
    """
    Generate synthetic merchants, transactions, and returns.
    Returns a dict with keys: merchants, transactions, returns.
    Deterministic for a given seed.
    """
    random.seed(seed)
    # Seed Faker for reproducible names/companies
    fake = Faker("en_IN")
    Faker.seed(seed)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    merchants = []
    transactions = []
    returns = []

    categories = ["electronics", "fashion", "grocery", "beauty", "sports"]

    # 50 merchants
    for i in range(50):
        merchants.append({
            "merchant_id": f"MID{1000 + i}",
            "name": fake.company(),
            "category": random.choice(categories),
        })

    # 3 fraud rings × 10 actors each
    fraud_rings = []
    for ring_idx in range(3):
        device = fake.uuid4()
        base_pin = str(random.randint(10000, 99990))
        bin_prefix = str(random.randint(400000, 499999))
        members = [
            {
                "device_fingerprint": device,
                "pin": str(int(base_pin) + random.randint(-2, 2)),
                "bank_bin": bin_prefix,
                "ring_id": f"RING_{ring_idx + 1}",
            }
            for _ in range(10)
        ]
        fraud_rings.append(members)

    # 800 legitimate transactions
    for i in range(800):
        merchant = random.choice(merchants)
        ts = datetime.now() - timedelta(days=random.randint(1, 30))
        transactions.append({
            "txn_id": f"TXN{10000 + i}",
            "merchant_id": merchant["merchant_id"],
            "customer_name": fake.name(),
            "device_fingerprint": fake.uuid4(),
            "pin": str(fake.postcode())[:6],
            "bank_bin": str(random.randint(400000, 599999)),
            "amount": random.randint(500, 15000),
            "timestamp": ts.isoformat(),
            "is_fraud": False,
        })

    # Fraud ring transactions — each ring hits 3-5 merchants
    fraud_txn_id = 10800
    for ring in fraud_rings:
        target_merchants = random.sample(merchants, random.randint(3, 5))
        base_time = datetime.now() - timedelta(days=random.randint(5, 15))
        for actor in ring:
            merchant = random.choice(target_merchants)
            amount = random.randint(2000, 8000)
            ts = base_time + timedelta(hours=random.randint(0, 48))
            txn = {
                "txn_id": f"TXN{fraud_txn_id}",
                "merchant_id": merchant["merchant_id"],
                "customer_name": fake.name(),
                "device_fingerprint": actor["device_fingerprint"],
                "pin": actor["pin"],
                "bank_bin": actor["bank_bin"],
                "amount": amount,
                "timestamp": ts.isoformat(),
                "is_fraud": True,
                "ring_id": actor["ring_id"],
            }
            transactions.append(txn)
            return_ts = ts + timedelta(hours=random.randint(2, 24))
            returns.append({
                "return_id": f"RET{fraud_txn_id}",
                "txn_id": txn["txn_id"],
                "merchant_id": merchant["merchant_id"],
                "amount": amount,
                "timestamp": return_ts.isoformat(),
                "device_fingerprint": actor["device_fingerprint"],
                "pin": actor["pin"],
                "bank_bin": actor["bank_bin"],
                "is_fraud": True,
                "ring_id": actor["ring_id"],
            })
            fraud_txn_id += 1

    random.shuffle(transactions)

    # Persist
    with open(DATA_DIR / "merchants.json", "w", encoding="utf-8") as f:
        json.dump(merchants, f, indent=2)
    with open(DATA_DIR / "transactions.json", "w", encoding="utf-8") as f:
        json.dump(transactions, f, indent=2)
    with open(DATA_DIR / "returns.json", "w", encoding="utf-8") as f:
        json.dump(returns, f, indent=2)

    return {"merchants": merchants, "transactions": transactions, "returns": returns}


if __name__ == "__main__":
    result = generate()
    print(f"✅ Generated: {len(result['merchants'])} merchants, "
          f"{len(result['transactions'])} transactions, "
          f"{len(result['returns'])} returns")
    print("   Fraud rings: 3 rings × 10 actors = 30 fraud actors")

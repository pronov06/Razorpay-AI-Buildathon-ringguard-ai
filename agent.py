"""
agent.py — LLM Reasoning Layer
Uses google-genai (new SDK) for fraud ring verdicts.

Fixes applied:
  - Migrated from deprecated google-generativeai to google-genai
  - Model initialised lazily — safe to import without API key
  - Exponential back-off retry on API errors
  - Exceptions logged, not silently swallowed
  - Fallback rule-based verdict when API unavailable
"""

import logging
import os
import time

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """Lazy Gemini client — configured on first call."""
    global _client
    if _client is None:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            try:
                import streamlit as st
                if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                    api_key = st.secrets["GEMINI_API_KEY"]
            except Exception:
                pass
        if not api_key:
            logger.warning("GEMINI_API_KEY not set — LLM verdicts will use fallback text")
        _client = genai.Client(api_key=api_key)
    return _client


def _fallback_verdict(ring: dict) -> str:
    return (
        f"Pattern: {ring['member_count']} customers share identical device fingerprints "
        f"across {ring['merchant_count']} merchants, with ₹{ring['total_damage_inr']:,} "
        f"in coordinated returns within a 48-hour window — statistically impossible by chance. "
        f"This is a coordinated abuse ring: single-merchant tools see 1 suspicious customer; "
        f"RingGuard sees the full ring of {ring['member_count']} operating together. "
        f"Recommended action: freeze all {ring['member_count']} accounts immediately and "
        f"alert all {ring['merchant_count']} affected merchants with shared evidence."
    )


def analyze_ring(ring: dict, max_retries: int = 3) -> str:
    prompt = f"""You are a fraud analyst at Razorpay reviewing a suspicious cross-merchant return ring.

Ring Data:
- Members: {ring['member_count']} customers
- Merchants Hit: {ring['merchant_count']} different merchants
- Total Damage: ₹{ring['total_damage_inr']:,}
- Confidence Score: {ring['confidence_score']}/100
- Unique Devices: {ring['signals']['unique_devices']}
- Unique Bank BINs: {ring['signals']['unique_bins']}
- Sample Merchant IDs: {ring['merchants_hit'][:3]}

In exactly 3 sentences:
1. What pattern do you see? (be specific with numbers)
2. Why is this a coordinated fraud ring and not coincidence?
3. What should Razorpay do right now?

Be direct. No fluff."""

    for attempt in range(max_retries):
        try:
            client = _get_client()
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            return response.text
        except Exception as exc:
            wait = 2 ** attempt
            logger.warning("Gemini API error (attempt %d/%d): %s — retrying in %ds",
                           attempt + 1, max_retries, exc, wait)
            if attempt < max_retries - 1:
                time.sleep(wait)

    logger.error("Gemini API failed after %d retries — using fallback verdict", max_retries)
    return _fallback_verdict(ring)


def analyze_all_rings(rings: list) -> list:
    return [{**ring, "llm_verdict": analyze_ring(ring)} for ring in rings]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample = {
        "member_count": 10, "merchant_count": 4, "total_damage_inr": 45000,
        "confidence_score": 92,
        "signals": {"unique_devices": 1, "unique_bins": 1, "device_fingerprints": ["abc123"]},
        "merchants_hit": ["MID1001", "MID1023", "MID1044"],
    }
    print(analyze_ring(sample))

import os
from hindsight_client import Hindsight
from .config import HINDSIGHT_API_KEY, HINDSIGHT_BASE_URL, BANK_ID

# Initialise Hindsight client (no explicit api_key needed if provided via env)
client = Hindsight(base_url=HINDSIGHT_BASE_URL, api_key=HINDSIGHT_API_KEY)

def ensure_bank():
    """Create the memory bank if it does not exist."""
    try:
        # Try to get bank profile – if it succeeds, bank exists
        client.get_bank(bank_id=BANK_ID)
    except Exception:
        # Create with a simple mission and disposition (cautious SRE assistant)
        client.create_bank(
            bank_id=BANK_ID,
            name='RunbookMind ACME SRE',
            mission='Assist on‑call engineers with incident triage using past incidents.',
            disposition={'skepticism': 0.7, 'literalism': 0.3, 'empathy': 0.2},
            retain_mission='Extract useful facts from incident narratives.',
            reflect_mission='Reason over recalled incidents to suggest root cause and actions.'
        )
        print(f"Created Hindsight bank {BANK_ID}")

# Ensure bank at import time
try:
    ensure_bank()
except Exception as e:
    print(f"[WARN] Could not ensure Hindsight bank on import: {e}")

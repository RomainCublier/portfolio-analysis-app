"""Small manually reviewed seed catalogue, not a production security master."""
from datetime import date
import json
import math
from pathlib import Path
import re

CATALOG = Path(__file__).resolve().parents[1] / "data/catalog/etfs.json"


def valid_isin(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", value):
        return False
    digits = "".join(str(ord(c) - 55) if c.isalpha() else c for c in value)
    total = 0
    for i, c in enumerate(reversed(digits)):
        n = int(c) * (2 if i % 2 else 1)
        total += n // 10 + n % 10
    return total % 10 == 0


def load_catalog(path=CATALOG):
    data = json.loads(Path(path).read_text())
    if data.get("schema_version") != 1:
        raise ValueError("Version du catalogue non reconnue.")
    seen = set()
    for row in data["instruments"]:
        if not valid_isin(row["isin"]) or row["isin"] in seen:
            raise ValueError("ISIN invalide ou dupliqué.")
        seen.add(row["isin"])
        if not row["source_url"].startswith("https://"):
            raise ValueError("Source manquante.")
        reviewed = date.fromisoformat(row["reviewed_on"])
        if row["source_date"] and date.fromisoformat(row["source_date"]) > reviewed:
            raise ValueError("Source postérieure à la consultation.")
        facts = row["facts"]
        fee = facts["fee_percent"]
        if fee is not None and (isinstance(fee, bool) or not isinstance(fee, (int, float)) or not math.isfinite(fee) or not 0 <= fee <= 100):
            raise ValueError("Frais invalides.")
        if facts["pea"] is not None and not isinstance(facts["pea"], bool):
            raise ValueError("Statut PEA invalide.")
        if facts["launch_date"]:
            date.fromisoformat(facts["launch_date"])
    return data["instruments"]


def review_status(row, today=None, max_age_days=30):
    """30 days is a product review policy, not an issuer guarantee."""
    today = today or date.today()
    age = (today - date.fromisoformat(row["reviewed_on"])).days
    if age < 0 or age > max_age_days:
        return "À revérifier"
    required = ("launch_date", "share_currency", "fee_percent", "income", "replication", "benchmark")
    return "Caractéristiques documentées" if all(row["facts"].get(k) is not None for k in required) else "Fiche incomplète"

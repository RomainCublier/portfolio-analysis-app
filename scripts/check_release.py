"""Fail closed when the production launch configuration is incomplete."""
from pathlib import Path
import os
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.access import BillingConfig
from core.billing import BillingError
from core.catalog import load_catalog
from core.release import ReleaseSettings, oidc_configured, readiness


def evaluate(environ, secrets, catalog):
    try:
        billing = BillingConfig.from_mapping(dict(secrets.get("billing", {})))
    except (BillingError, TypeError, ValueError):
        billing = BillingConfig()
    return readiness(
        ReleaseSettings.from_environ(environ), catalog,
        billing_configured=billing.enabled,
        auth_configured=oidc_configured(dict(secrets.get("auth", {}))),
    )


def load_secrets(path):
    try:
        with path.open("rb") as stream:
            return tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def main():
    path = Path(os.environ.get("STREAMLIT_SECRETS_FILE", ROOT / ".streamlit" / "secrets.toml"))
    blockers = evaluate(os.environ, load_secrets(path), load_catalog())
    if blockers:
        print("OUVERTURE BLOQUÉE")
        for blocker in blockers:
            print(f"- {blocker}")
        return 1
    print("CONFIGURATION DE PRODUCTION COMPLÈTE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Configuration and access checks for the optional paid V1."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from urllib.parse import urlparse

from cryptography.fernet import Fernet

from core.billing import BillingError, EntitlementStore, PRICE_ID, subscription_active
from core.storage import owner_id


@dataclass(frozen=True)
class BillingConfig:
    enabled: bool = False
    issuer: str = ""
    path: str = ""
    encryption_key: str = ""
    secret_key: str = ""
    price_id: str = ""
    offer_name: str = "Accès QuantDesk V1"
    price_label: str = ""

    @classmethod
    def from_mapping(cls, raw):
        if not isinstance(raw, dict) or raw.get("enabled") is not True:
            return cls()
        values = {key: raw.get(key, "") for key in (
            "issuer", "path", "encryption_key", "secret_key", "price_id",
            "offer_name", "price_label",
        )}
        if any(not isinstance(value, str) or not value.strip() for value in values.values()):
            raise BillingError("Configuration de l’offre payante incomplète.")
        values = {key: value.strip() for key, value in values.items()}
        issuer = urlparse(values["issuer"])
        if issuer.scheme != "https" or not issuer.netloc or issuer.username:
            raise BillingError("Fournisseur d’identité invalide.")
        if not Path(values["path"]).is_absolute():
            raise BillingError("Le stockage des accès doit utiliser un chemin absolu.")
        try:
            Fernet(values["encryption_key"].encode())
        except (ValueError, TypeError) as exc:
            raise BillingError("Clé de chiffrement des accès invalide.") from exc
        if not values["secret_key"].startswith(("sk_test_", "sk_live_")):
            raise BillingError("Clé Stripe serveur invalide.")
        if not PRICE_ID.fullmatch(values["price_id"]):
            raise BillingError("Identifiant de prix Stripe invalide.")
        return cls(enabled=True, **values)


def access_status(config, identity, state, *, now=None, requester=None):
    """Return (owner, entitlement, active), caching only a short verified status."""
    if not config.enabled:
        return None, None, True
    if not isinstance(identity, dict) or identity.get("iss") != config.issuer:
        return None, None, False
    owner = owner_id(config.issuer, identity.get("sub"))
    entitlement = EntitlementStore(config.path, config.encryption_key).load(owner)
    if entitlement is None:
        return owner, None, False
    timestamp = time.time() if now is None else now
    cache = state.get("_billing_access_check")
    if (isinstance(cache, dict) and cache.get("owner") == owner
            and cache.get("subscription") == entitlement.subscription
            and isinstance(cache.get("checked_at"), (int, float))
            and 0 <= timestamp - cache["checked_at"] <= 300):
        return owner, entitlement, cache.get("active") is True
    kwargs = {} if requester is None else {"requester": requester}
    active = subscription_active(config.secret_key, entitlement.subscription, owner, **kwargs)
    state["_billing_access_check"] = {
        "owner": owner,
        "subscription": entitlement.subscription,
        "checked_at": timestamp,
        "active": active,
    }
    return owner, entitlement, active

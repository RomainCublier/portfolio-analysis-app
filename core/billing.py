"""Stripe-hosted subscription checkout and encrypted entitlement storage.

The browser never receives the Stripe secret. Access is granted only after a
server-side retrieval of the Checkout Session and current Subscription.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
import sqlite3
from contextlib import closing
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
import requests


API = "https://api.stripe.com/v1"
ACTIVE = {"active", "trialing"}
SESSION_ID = re.compile(r"^cs_(?:test_|live_)?[A-Za-z0-9]+$")
CUSTOMER_ID = re.compile(r"^cus_[A-Za-z0-9]+$")
SUBSCRIPTION_ID = re.compile(r"^sub_[A-Za-z0-9]+$")
PRICE_ID = re.compile(r"^price_[A-Za-z0-9]+$")


class BillingError(ValueError):
    pass


def _https(value):
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username


def checkout_configuration(api_key, price_id, success_url, cancel_url):
    if not isinstance(api_key, str) or not api_key.startswith(("sk_test_", "sk_live_")):
        raise BillingError("Clé de paiement serveur invalide.")
    if not isinstance(price_id, str) or not PRICE_ID.fullmatch(price_id):
        raise BillingError("Tarif de paiement invalide.")
    if not all(isinstance(url, str) and _https(url) for url in (success_url, cancel_url)):
        raise BillingError("URL de retour HTTPS invalide.")


def _request(method, path, api_key, *, data=None, timeout=(5, 20), requester=requests.request):
    try:
        response = requester(method, API + path, auth=(api_key, ""), data=data,
                             timeout=timeout, allow_redirects=False)
    except requests.RequestException as exc:
        raise BillingError("Service de paiement momentanément indisponible.") from exc
    if response.status_code < 200 or response.status_code >= 300:
        raise BillingError("Le service de paiement a refusé l’opération.")
    try:
        payload = response.json()
    except (ValueError, TypeError) as exc:
        raise BillingError("Réponse du service de paiement invalide.") from exc
    if not isinstance(payload, dict):
        raise BillingError("Réponse du service de paiement invalide.")
    return payload


def create_checkout(api_key, price_id, owner, success_url, cancel_url, email=None, requester=requests.request):
    checkout_configuration(api_key, price_id, success_url, cancel_url)
    if not isinstance(owner, str) or not re.fullmatch(r"[a-f0-9]{64}", owner):
        raise BillingError("Identité de paiement invalide.")
    data = {
        "mode": "subscription",
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "client_reference_id": owner,
        "metadata[owner]": owner,
        "subscription_data[metadata][owner]": owner,
        "success_url": success_url,
        "cancel_url": cancel_url,
    }
    if isinstance(email, str) and 3 <= len(email) <= 320 and "@" in email:
        data["customer_email"] = email
    payload = _request("POST", "/checkout/sessions", api_key, data=data, requester=requester)
    url = payload.get("url")
    session_id = payload.get("id")
    if (not isinstance(url, str) or urlparse(url).scheme != "https"
            or urlparse(url).hostname != "checkout.stripe.com"
            or not isinstance(session_id, str) or not SESSION_ID.fullmatch(session_id)):
        raise BillingError("Session de paiement invalide.")
    return session_id, url


@dataclass(frozen=True)
class Entitlement:
    customer: str
    subscription: str

    def __post_init__(self):
        if not CUSTOMER_ID.fullmatch(self.customer) or not SUBSCRIPTION_ID.fullmatch(self.subscription):
            raise BillingError("Droit d’accès invalide.")


def subscription_active(api_key, subscription_id, owner, requester=requests.request):
    if not SUBSCRIPTION_ID.fullmatch(subscription_id or ""):
        raise BillingError("Abonnement invalide.")
    payload = _request("GET", f"/subscriptions/{subscription_id}", api_key, requester=requester)
    metadata = payload.get("metadata") or {}
    if payload.get("id") != subscription_id or metadata.get("owner") != owner:
        raise BillingError("Abonnement incompatible avec ce compte.")
    return payload.get("status") in ACTIVE


def verify_checkout(api_key, session_id, owner, requester=requests.request):
    if not SESSION_ID.fullmatch(session_id or ""):
        raise BillingError("Session de paiement invalide.")
    payload = _request("GET", f"/checkout/sessions/{session_id}", api_key, requester=requester)
    if (payload.get("id") != session_id or payload.get("client_reference_id") != owner
            or payload.get("status") != "complete"
            or payload.get("payment_status") not in {"paid", "no_payment_required"}
            or payload.get("mode") != "subscription"):
        raise BillingError("Paiement non confirmé pour ce compte.")
    entitlement = Entitlement(payload.get("customer", ""), payload.get("subscription", ""))
    if not subscription_active(api_key, entitlement.subscription, owner, requester=requester):
        raise BillingError("L’abonnement n’est pas actif.")
    return entitlement


def create_customer_portal(api_key, customer_id, return_url, requester=requests.request):
    if not CUSTOMER_ID.fullmatch(customer_id or "") or not _https(return_url):
        raise BillingError("Portail client invalide.")
    payload = _request("POST", "/billing_portal/sessions", api_key,
                       data={"customer": customer_id, "return_url": return_url}, requester=requester)
    url = payload.get("url")
    if not isinstance(url, str) or urlparse(url).scheme != "https" or urlparse(url).hostname != "billing.stripe.com":
        raise BillingError("Portail client invalide.")
    return url


class EntitlementStore:
    def __init__(self, path, key):
        self.cipher = Fernet(key)
        self.path = str(path)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS entitlements "
                       "(owner TEXT PRIMARY KEY, payload BLOB NOT NULL)")

    def load(self, owner):
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT payload FROM entitlements WHERE owner = ?", (owner,)).fetchone()
        if row is None:
            return None
        try:
            envelope = json.loads(self.cipher.decrypt(row[0]))
            if envelope.get("owner") != owner:
                raise BillingError("Droit d’accès incompatible avec ce compte.")
            return Entitlement(**envelope["entitlement"])
        except (InvalidToken, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise BillingError("Droit d’accès illisible.") from exc

    def save(self, owner, entitlement):
        if not isinstance(entitlement, Entitlement):
            raise BillingError("Droit d’accès invalide.")
        payload = self.cipher.encrypt(json.dumps({
            "owner": owner,
            "entitlement": asdict(entitlement),
        }).encode())
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO entitlements VALUES (?, ?) ON CONFLICT(owner) "
                       "DO UPDATE SET payload = excluded.payload", (owner, payload))

    def delete(self, owner):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("DELETE FROM entitlements WHERE owner = ?", (owner,))

"""Small, explicit release configuration for the public V1.

No missing value is silently replaced with a legal or commercial assertion.
Production readiness is therefore a check, not a marketing flag.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import re
from urllib.parse import urlparse


TRUE_VALUES = {"1", "true", "yes", "on"}
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def enabled(value: object) -> bool:
    return isinstance(value, str) and value.strip().lower() in TRUE_VALUES


def laboratory_enabled(environ=None) -> bool:
    values = os.environ if environ is None else environ
    return enabled(values.get("QUANTDESK_ENABLE_LAB", ""))


def _https(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username


@dataclass(frozen=True)
class ReleaseSettings:
    environment: str = "development"
    public_url: str = ""
    publisher: str = ""
    support_email: str = ""
    privacy_url: str = ""
    terms_url: str = ""
    commercial_data_rights_approved: bool = False

    @classmethod
    def from_environ(cls, environ=None):
        values = os.environ if environ is None else environ
        return cls(
            environment=values.get("APP_ENV", "development").strip().lower(),
            public_url=values.get("APP_PUBLIC_URL", "").strip(),
            publisher=values.get("APP_LEGAL_PUBLISHER", "").strip(),
            support_email=values.get("APP_SUPPORT_EMAIL", "").strip(),
            privacy_url=values.get("APP_PRIVACY_URL", "").strip(),
            terms_url=values.get("APP_TERMS_URL", "").strip(),
            commercial_data_rights_approved=enabled(
                values.get("APP_COMMERCIAL_DATA_RIGHTS_APPROVED", "")
            ),
        )

    @property
    def production(self) -> bool:
        return self.environment == "production"


def readiness(settings: ReleaseSettings, catalog=None, billing_configured=False) -> list[str]:
    """Return release blockers without pretending to perform legal review."""
    blockers = []
    if not _https(settings.public_url):
        blockers.append("URL publique HTTPS non configurée")
    if not settings.publisher:
        blockers.append("identité de l’éditeur non configurée")
    if not EMAIL.fullmatch(settings.support_email):
        blockers.append("adresse de contact valide non configurée")
    if not _https(settings.privacy_url):
        blockers.append("politique de confidentialité HTTPS non configurée")
    if not _https(settings.terms_url):
        blockers.append("conditions d’utilisation HTTPS non configurées")
    if billing_configured is not True:
        blockers.append("authentification et paiement récurrent non configurés")
    if not settings.commercial_data_rights_approved:
        blockers.append("droits d’utilisation commerciale des données non validés")
    if catalog is not None and any(row.get("commercial_rights") != "approved" for row in catalog):
        blockers.append("droits commerciaux du catalogue non approuvés support par support")
    return blockers

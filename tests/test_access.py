from cryptography.fernet import Fernet
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from core.access import BillingConfig, access_status
from core.billing import BillingError, Entitlement, EntitlementStore
from core.storage import owner_id


ISSUER = "https://identity.example"
SUBJECT = "person-123"
OWNER = owner_id(ISSUER, SUBJECT)


class Response:
    status_code = 200
    def __init__(self, status="active"):
        self.status = status
    def json(self):
        return {"id": "sub_example123", "status": self.status, "metadata": {"owner": OWNER}}


def config(tmp_path):
    return BillingConfig(
        enabled=True, issuer=ISSUER, path=str(tmp_path / "app.sqlite3"),
        encryption_key=Fernet.generate_key().decode(), secret_key="sk_test_example",
        price_id="price_example123", offer_name="Offre", price_label="10 € / mois",
    )


def test_disabled_billing_keeps_development_open():
    assert access_status(BillingConfig(), {}, {}) == (None, None, True)


def test_billing_mapping_is_validated_before_production_can_open(tmp_path):
    raw = {
        "enabled": True,
        "issuer": ISSUER,
        "path": str(tmp_path / "app.sqlite3"),
        "encryption_key": Fernet.generate_key().decode(),
        "secret_key": "sk_test_example",
        "price_id": "price_example123",
        "offer_name": "Offre",
        "price_label": "10 € / mois",
    }
    assert BillingConfig.from_mapping(raw).enabled
    for key, value in (
        ("issuer", "http://identity.example"),
        ("path", "relative.sqlite3"),
        ("encryption_key", "invalid"),
        ("secret_key", "pk_test_example"),
        ("price_id", "product_example"),
    ):
        with pytest.raises(BillingError):
            BillingConfig.from_mapping({**raw, key: value})


def test_login_and_entitlement_are_required(tmp_path):
    cfg = config(tmp_path)
    assert access_status(cfg, {}, {}) == (None, None, False)
    owner, entitlement, active = access_status(cfg, {"iss": ISSUER, "sub": SUBJECT}, {})
    assert owner == OWNER and entitlement is None and not active


def test_active_access_is_checked_and_short_cached(tmp_path):
    cfg = config(tmp_path)
    entitlement = Entitlement("cus_example123", "sub_example123")
    EntitlementStore(cfg.path, cfg.encryption_key).save(OWNER, entitlement)
    calls = []
    def requester(*args, **kwargs):
        calls.append(1)
        return Response()
    state = {}
    assert access_status(cfg, {"iss": ISSUER, "sub": SUBJECT}, state, now=100, requester=requester)[2]
    assert access_status(cfg, {"iss": ISSUER, "sub": SUBJECT}, state, now=200, requester=requester)[2]
    assert len(calls) == 1
    assert access_status(cfg, {"iss": ISSUER, "sub": SUBJECT}, state, now=401, requester=requester)[2]
    assert len(calls) == 2


def test_past_due_subscription_is_not_access(tmp_path):
    cfg = config(tmp_path)
    EntitlementStore(cfg.path, cfg.encryption_key).save(OWNER, Entitlement("cus_example123", "sub_example123"))
    def requester(*args, **kwargs):
        return Response("past_due")
    assert not access_status(cfg, {"iss": ISSUER, "sub": SUBJECT}, {}, now=100, requester=requester)[2]


def test_offer_page_is_safe_when_billing_is_disabled():
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "app.py")).run()
    app.switch_page("pages/offre.py").run()
    assert not app.exception
    assert app.title[0].value == "Accès complet"
    assert any("pas encore ouverte" in item.value for item in app.info)

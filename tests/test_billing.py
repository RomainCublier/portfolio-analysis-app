import json

import pytest
import requests
from cryptography.fernet import Fernet

from core.billing import (BillingError, Entitlement, EntitlementStore,
                          create_checkout, create_customer_portal,
                          subscription_active, verify_checkout)


OWNER = "a" * 64
KEY = "sk_test_example"
PRICE = "price_example123"
SESSION = "cs_test_example123"
CUSTOMER = "cus_example123"
SUBSCRIPTION = "sub_example123"


class Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status

    def json(self):
        return self.payload


def requester(responses, calls):
    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        value = responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value
    return request


def test_checkout_uses_fixed_stripe_api_and_server_side_identity():
    calls = []
    fake = requester([Response({"id": SESSION, "url": "https://checkout.stripe.com/c/pay/example"})], calls)
    result = create_checkout(KEY, PRICE, OWNER,
                             "https://app.example/offre?checkout_session={CHECKOUT_SESSION_ID}",
                             "https://app.example/offre?checkout=cancelled",
                             "person@example.com", requester=fake)
    assert result == (SESSION, "https://checkout.stripe.com/c/pay/example")
    assert calls[0][1] == "https://api.stripe.com/v1/checkout/sessions"
    assert calls[0][2]["auth"] == (KEY, "")
    assert calls[0][2]["data"]["client_reference_id"] == OWNER
    assert calls[0][2]["data"]["subscription_data[metadata][owner]"] == OWNER


def test_checkout_rejects_non_stripe_redirect_and_weak_configuration():
    fake = requester([Response({"id": SESSION, "url": "https://evil.example/pay"})], [])
    with pytest.raises(BillingError):
        create_checkout(KEY, PRICE, OWNER, "https://app.example/success", "https://app.example/cancel", requester=fake)
    with pytest.raises(BillingError):
        create_checkout("pk_test_public", PRICE, OWNER, "https://app.example/success", "https://app.example/cancel")
    with pytest.raises(BillingError):
        create_checkout(KEY, PRICE, OWNER, "http://app.example/success", "https://app.example/cancel")


def test_paid_session_and_subscription_are_both_verified():
    calls = []
    fake = requester([
        Response({"id": SESSION, "client_reference_id": OWNER, "status": "complete",
                  "payment_status": "paid", "mode": "subscription",
                  "customer": CUSTOMER, "subscription": SUBSCRIPTION}),
        Response({"id": SUBSCRIPTION, "status": "active", "metadata": {"owner": OWNER}}),
    ], calls)
    assert verify_checkout(KEY, SESSION, OWNER, requester=fake) == Entitlement(CUSTOMER, SUBSCRIPTION)
    assert calls[1][1].endswith("/subscriptions/" + SUBSCRIPTION)


@pytest.mark.parametrize("change", [
    {"client_reference_id": "b" * 64}, {"status": "open"},
    {"payment_status": "unpaid"}, {"mode": "payment"},
])
def test_unpaid_or_mismatched_checkout_is_refused(change):
    payload = {"id": SESSION, "client_reference_id": OWNER, "status": "complete",
               "payment_status": "paid", "mode": "subscription",
               "customer": CUSTOMER, "subscription": SUBSCRIPTION}
    payload.update(change)
    fake = requester([Response(payload)], [])
    with pytest.raises(BillingError):
        verify_checkout(KEY, SESSION, OWNER, requester=fake)


def test_subscription_must_belong_to_owner_and_be_active():
    for status, owner, expected in [("trialing", OWNER, True), ("active", "b" * 64, "error"), ("past_due", OWNER, False)]:
        fake = requester([Response({"id": SUBSCRIPTION, "status": status, "metadata": {"owner": owner}})], [])
        if expected == "error":
            with pytest.raises(BillingError):
                subscription_active(KEY, SUBSCRIPTION, OWNER, requester=fake)
        else:
            assert subscription_active(KEY, SUBSCRIPTION, OWNER, requester=fake) is expected


def test_provider_errors_do_not_leak_body():
    fake = requester([Response({"error": {"message": "secret provider detail"}}, status=402)], [])
    with pytest.raises(BillingError, match="refusé") as error:
        subscription_active(KEY, SUBSCRIPTION, OWNER, requester=fake)
    assert "secret provider detail" not in str(error.value)
    network = requester([requests.ConnectionError("private network detail")], [])
    with pytest.raises(BillingError, match="indisponible"):
        subscription_active(KEY, SUBSCRIPTION, OWNER, requester=network)


def test_entitlement_store_encrypts_and_binds_owner(tmp_path):
    key = Fernet.generate_key()
    path = tmp_path / "billing.sqlite3"
    store = EntitlementStore(path, key)
    entitlement = Entitlement(CUSTOMER, SUBSCRIPTION)
    store.save(OWNER, entitlement)
    assert store.load(OWNER) == entitlement
    raw = path.read_bytes()
    assert CUSTOMER.encode() not in raw and SUBSCRIPTION.encode() not in raw
    assert store.load("b" * 64) is None
    store.delete(OWNER)
    assert store.load(OWNER) is None


def test_customer_portal_is_restricted_to_stripe_host():
    fake = requester([Response({"url": "https://billing.stripe.com/p/session"})], [])
    assert create_customer_portal(KEY, CUSTOMER, "https://app.example/offre", requester=fake).startswith("https://billing.stripe.com/")
    fake = requester([Response({"url": "https://evil.example/portal"})], [])
    with pytest.raises(BillingError):
        create_customer_portal(KEY, CUSTOMER, "https://app.example/offre", requester=fake)

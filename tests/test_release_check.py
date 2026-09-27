from cryptography.fernet import Fernet

from scripts.check_release import evaluate


def production_environment():
    return {
        "APP_ENV": "production",
        "APP_PUBLIC_URL": "https://invest.example",
        "APP_LEGAL_PUBLISHER": "Example SAS",
        "APP_SUPPORT_EMAIL": "support@example.com",
        "APP_PRIVACY_URL": "https://invest.example/confidentialite",
        "APP_TERMS_URL": "https://invest.example/conditions",
        "APP_COMMERCIAL_DATA_RIGHTS_APPROVED": "true",
    }


def secrets(tmp_path):
    return {
        "auth": {
            "redirect_uri": "https://invest.example/oauth2callback",
            "cookie_secret": "a" * 32,
            "client_id": "client",
            "client_secret": "secret",
            "server_metadata_url": "https://identity.example/.well-known/openid-configuration",
        },
        "billing": {
            "enabled": True,
            "issuer": "https://identity.example",
            "path": str(tmp_path / "app.sqlite3"),
            "encryption_key": Fernet.generate_key().decode(),
            "secret_key": "sk_test_example",
            "price_id": "price_example123",
            "offer_name": "Offre",
            "price_label": "10 € / mois",
        },
    }


def test_release_check_reports_no_blocker_only_when_every_gate_is_true(tmp_path):
    approved = [{"commercial_rights": "approved"}]
    assert evaluate(production_environment(), secrets(tmp_path), approved) == []


def test_release_check_keeps_auth_data_and_billing_as_separate_gates(tmp_path):
    approved = [{"commercial_rights": "approved"}]
    without_auth = secrets(tmp_path)
    without_auth.pop("auth")
    assert evaluate(production_environment(), without_auth, approved) == [
        "authentification OIDC non configurée"
    ]
    without_billing = secrets(tmp_path)
    without_billing.pop("billing")
    assert evaluate(production_environment(), without_billing, approved) == [
        "paiement récurrent non configuré"
    ]

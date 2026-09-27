from core.release import ReleaseSettings, enabled, laboratory_enabled, oidc_configured, readiness
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_internal_laboratory_is_off_by_default_and_explicitly_enabled():
    assert not laboratory_enabled({})
    assert laboratory_enabled({"QUANTDESK_ENABLE_LAB": "true"})
    assert not laboratory_enabled({"QUANTDESK_ENABLE_LAB": "sometimes"})
    assert enabled("YES")


def test_production_readiness_requires_real_external_configuration():
    settings = ReleaseSettings.from_environ({"APP_ENV": "production"})
    assert settings.production
    assert len(readiness(settings)) == 8


def test_release_configuration_can_be_complete_without_weakening_checks():
    settings = ReleaseSettings.from_environ({
        "APP_ENV": "production",
        "APP_PUBLIC_URL": "https://invest.example",
        "APP_LEGAL_PUBLISHER": "Example SAS",
        "APP_SUPPORT_EMAIL": "support@example.com",
        "APP_PRIVACY_URL": "https://invest.example/confidentialite",
        "APP_TERMS_URL": "https://invest.example/conditions",
        "APP_COMMERCIAL_DATA_RIGHTS_APPROVED": "true",
    })
    approved = [{"commercial_rights": "approved"}]
    assert readiness(settings, approved, billing_configured=True, auth_configured=True) == []
    assert "support par support" in readiness(
        settings, [{"commercial_rights": "not_assessed"}], True, True
    )[-1]


def test_non_https_or_credentialed_urls_are_rejected():
    base = {
        "APP_PUBLIC_URL": "http://invest.example",
        "APP_LEGAL_PUBLISHER": "Example SAS",
        "APP_SUPPORT_EMAIL": "not-an-email",
        "APP_PRIVACY_URL": "https://user:secret@invest.example/privacy",
        "APP_TERMS_URL": "https://invest.example/terms",
        "APP_COMMERCIAL_DATA_RIGHTS_APPROVED": "true",
    }
    blockers = readiness(
        ReleaseSettings.from_environ(base), billing_configured=True,
        auth_configured=True,
    )
    assert len(blockers) == 3


def test_oidc_configuration_requires_https_callback_metadata_and_real_secret():
    valid = {
        "redirect_uri": "https://invest.example/oauth2callback",
        "cookie_secret": "a" * 32,
        "client_id": "client",
        "client_secret": "secret",
        "server_metadata_url": "https://identity.example/.well-known/openid-configuration",
    }
    assert oidc_configured(valid)
    for key, value in (
        ("redirect_uri", "http://invest.example/oauth2callback"),
        ("redirect_uri", "https://invest.example/callback"),
        ("cookie_secret", "too-short"),
        ("server_metadata_url", "http://identity.example/metadata"),
    ):
        candidate = {**valid, key: value}
        assert not oidc_configured(candidate)


def test_incomplete_production_configuration_blocks_the_product(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "app.py")).run()
    assert not app.exception
    assert app.title[0].value == "Informations et limites"
    assert any("ouverture commerciale" in item.value for item in app.error)

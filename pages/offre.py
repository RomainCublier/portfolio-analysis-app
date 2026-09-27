"""Authenticated Stripe checkout and subscription management page."""
import sqlite3

import streamlit as st
from cryptography.fernet import InvalidToken
from streamlit.errors import StreamlitSecretNotFoundError

from core.access import BillingConfig, access_status
from core.billing import (BillingError, EntitlementStore, create_checkout,
                          create_customer_portal, verify_checkout)
from core.release import ReleaseSettings
from core.storage import owner_id


def configuration():
    try:
        raw = dict(st.secrets.get("billing", {}))
    except StreamlitSecretNotFoundError:
        raw = {}
    return BillingConfig.from_mapping(raw)


st.title("Accès complet")
settings = ReleaseSettings.from_environ()
try:
    config = configuration()
except BillingError:
    st.error("L’offre payante n’est pas correctement configurée.")
    st.stop()

if not config.enabled:
    st.info("L’offre payante n’est pas encore ouverte sur cette préversion.")
    st.page_link("pages/informations.py", label="Consulter les informations de la V1")
    st.stop()

st.subheader(config.offer_name)
st.write(config.price_label)
st.write("Accès au parcours complet, aux portefeuilles fictifs, au dossier et au suivi manuel.")
st.caption("Aucun ordre n’est transmis. Les fonctions expérimentales du laboratoire ne font pas partie de l’offre.")

if not st.user.is_logged_in:
    st.write("Connectez-vous avant le paiement pour rattacher l’accès au bon compte.")
    if st.button("Me connecter", type="primary"):
        st.login()
    st.stop()

identity = dict(st.user)
if identity.get("iss") != config.issuer:
    st.error("Le fournisseur de connexion ne correspond pas à celui de l’offre.")
    st.stop()
owner = owner_id(config.issuer, identity.get("sub"))
try:
    store = EntitlementStore(config.path, config.encryption_key)
except (BillingError, OSError, sqlite3.Error, InvalidToken):
    st.error("Le stockage des accès est indisponible. Aucun paiement ne peut être commencé.")
    st.stop()

session_id = st.query_params.get("checkout_session")
if session_id:
    try:
        entitlement = verify_checkout(config.secret_key, session_id, owner)
        store.save(owner, entitlement)
        st.session_state["_billing_access_check"] = {
            "owner": owner, "subscription": entitlement.subscription,
            "checked_at": 0, "active": True,
        }
        st.query_params.clear()
        st.success("Paiement confirmé. Votre accès est maintenant actif.")
    except (BillingError, OSError, sqlite3.Error, InvalidToken):
        st.error("Le paiement n’a pas pu être confirmé pour ce compte. Aucun accès n’a été accordé.")

try:
    _, entitlement, active = access_status(config, identity, st.session_state)
except (BillingError, OSError, sqlite3.Error, InvalidToken):
    entitlement, active = None, False
    st.error("Impossible de vérifier votre accès pour le moment. Réessayez plus tard.")

if active:
    st.success("Votre accès complet est actif.")
    st.page_link("pages/assistant.py", label="Ouvrir mon assistant", icon="🧭")
    if st.button("Gérer mon abonnement"):
        try:
            st.session_state["_billing_portal_url"] = create_customer_portal(
                config.secret_key, entitlement.customer, settings.public_url.rstrip("/") + "/offre"
            )
        except BillingError:
            st.error("Le portail d’abonnement est momentanément indisponible.")
    if st.session_state.get("_billing_portal_url"):
        st.link_button("Ouvrir le portail sécurisé Stripe", st.session_state["_billing_portal_url"])
    st.stop()

if not settings.public_url.startswith("https://"):
    st.error("Le paiement reste fermé tant que l’adresse publique HTTPS n’est pas configurée.")
    st.stop()

if st.button("Préparer mon paiement", type="primary"):
    try:
        success = settings.public_url.rstrip("/") + "/offre?checkout_session={CHECKOUT_SESSION_ID}"
        cancel = settings.public_url.rstrip("/") + "/offre?checkout=cancelled"
        _, url = create_checkout(config.secret_key, config.price_id, owner, success, cancel, identity.get("email"))
        st.session_state["_billing_checkout_url"] = url
    except BillingError:
        st.error("Impossible de préparer le paiement. Réessayez plus tard.")
if st.session_state.get("_billing_checkout_url"):
    st.link_button("Continuer vers le paiement sécurisé Stripe", st.session_state["_billing_checkout_url"])
    st.caption("Le paiement est réalisé sur le site sécurisé de Stripe. L’accès n’est accordé qu’après vérification du paiement par QuantDesk.")

if settings.terms_url and settings.privacy_url:
    st.link_button("Conditions d’utilisation", settings.terms_url)
    st.link_button("Politique de confidentialité", settings.privacy_url)

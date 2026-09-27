"""Product perimeter, data use and user-facing release information."""
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from core.access import BillingConfig
from core.billing import BillingError
from core.catalog import load_catalog
from core.release import ReleaseSettings, oidc_configured, readiness


settings = ReleaseSettings.from_environ()

st.title("Informations et limites")
st.write(
    "QuantDesk aide à préparer un projet d’investissement, comparer des exemples "
    "pédagogiques et suivre des valeurs déclarées manuellement."
)

if not settings.production:
    st.info(
        "Cette instance est une préversion de test. Elle ne doit pas être présentée "
        "comme un service commercial ouvert au public."
    )

st.subheader("Ce que fait la V1")
st.markdown(
    """
- organiser un objectif, un horizon, un capital et des versements ;
- comparer des répartitions fictives identiques pour tous ;
- consulter un catalogue limité de supports avec leurs sources ;
- simuler des hypothèses choisies par l’utilisateur et étudier des périodes passées ;
- enregistrer des positions, valorisations et mouvements déclarés manuellement.
"""
)

st.subheader("Ce que la V1 ne fait pas")
st.markdown(
    """
- elle ne transmet aucun ordre et ne se connecte à aucun courtier ;
- elle ne garantit ni rendement, ni capital, ni disponibilité d’un support ;
- elle ne désigne pas un portefeuille comme optimal ou adapté définitivement ;
- elle ne met pas automatiquement à jour les cours, les actualités ou la fiscalité ;
- elle ne remplace pas la vérification des documents officiels avant une décision réelle.
"""
)
st.warning(
    "Investir comporte un risque de perte en capital. Les performances passées, "
    "les simulations et les exemples ne préjugent pas des performances futures."
)

st.subheader("Données et calculs")
st.write(
    "Chaque fiche affiche sa source et sa date de consultation. Une information non "
    "vérifiée reste indiquée comme inconnue. Les historiques incomplets sont refusés : "
    "aucune date manquante n’est inventée ou déplacée automatiquement."
)
st.write(
    "Les projections à rendement constant sont des calculs mathématiques. Les backtests "
    "rejouent uniquement la période et les règles affichées, hors fiscalité et, selon le "
    "cas, hors courtage et spread."
)

st.subheader("Vos données")
st.write(
    "Sans compte configuré, les saisies restent dans la session du navigateur. Le dossier "
    "téléchargé est un fichier en clair sous votre responsabilité. Si la sauvegarde avec "
    "compte est activée, le dossier est chiffré et rattaché à l’identité fournie par le "
    "service de connexion. Les historiques de marché importés ne sont pas sauvegardés."
)

st.subheader("Éditeur et documents contractuels")
if settings.publisher:
    st.write(f"Éditeur déclaré : {settings.publisher}")
if settings.support_email:
    st.write(f"Contact : {settings.support_email}")
if settings.privacy_url:
    st.link_button("Politique de confidentialité", settings.privacy_url)
if settings.terms_url:
    st.link_button("Conditions d’utilisation", settings.terms_url)
if not all((settings.publisher, settings.support_email, settings.privacy_url, settings.terms_url)):
    st.caption(
        "Les informations définitives de l’éditeur et les documents contractuels ne sont "
        "pas encore configurés sur cette préversion."
    )

if settings.production:
    try:
        billing = BillingConfig.from_mapping(dict(st.secrets.get("billing", {})))
        auth_ready = oidc_configured(dict(st.secrets.get("auth", {})))
    except (StreamlitSecretNotFoundError, BillingError):
        billing = BillingConfig()
        auth_ready = False
    blockers = readiness(
        settings, load_catalog(), billing_configured=billing.enabled,
        auth_configured=auth_ready,
    )
    if blockers:
        st.error("Configuration de lancement incomplète. L’ouverture commerciale doit rester bloquée.")

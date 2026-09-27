"""Optional authenticated storage; portable export remains available to everyone."""
import sqlite3

import streamlit as st
from cryptography.fernet import InvalidToken
from streamlit.errors import StreamlitSecretNotFoundError

from core.dossier import export_dossier, restore_dossier, import_dossier
from core.storage import DossierStore, owner_id

st.title('Mon dossier')
st.write('Conservez votre projet, vos essais et votre portefeuille pour votre prochaine visite.')
try:
    st.download_button('Télécharger mon dossier', export_dossier(st.session_state),
                       'mon-dossier-investisseur.json', 'application/json')
except ValueError:
    st.error('Le dossier contient des données invalides. Vérifiez vos saisies avant de le conserver.')
st.caption('Le fichier téléchargé contient vos données personnelles en clair. Gardez-le dans un endroit privé.')
st.caption('Inclus : projet, répartition fictive, positions déclarées, valorisations, mouvements et journal. Les historiques de marché et résultats de backtest ne sont pas inclus.')
st.subheader('Reprendre un dossier')
upload = st.file_uploader('Mon fichier de sauvegarde', type=['json'])
replace_local = st.checkbox('Remplacer les données de cette session par ce fichier')
if st.button('Reprendre ce dossier', disabled=upload is None or not replace_local):
    try:
        restored = import_dossier(upload.getvalue())
        restore_dossier(st.session_state, restored)
        st.success('Dossier repris. Retrouvez votre projet depuis Mon assistant.')
    except ValueError as exc:
        st.error(f'Dossier non chargé : {exc}')

try:
    config = st.secrets.get('dossier_storage', {})
    configured = bool(config.get('enabled', False)) and 'auth' in st.secrets
except StreamlitSecretNotFoundError:
    configured = False

if not configured:
    st.info('La sauvegarde avec un compte n’est pas encore disponible. Vous pouvez télécharger et reprendre votre dossier ici.')
    st.stop()

if not st.user.is_logged_in:
    st.write('Connectez-vous pour enregistrer votre dossier et le retrouver sur un autre appareil.')
    st.caption('La connexion ouvre une nouvelle session. Téléchargez d’abord vos essais en cours pour pouvoir les reprendre.')
    if st.button('Me connecter', type='primary'):
        st.login()
    st.stop()

if st.button('Me déconnecter'):
    st.session_state.clear()
    st.logout()
    st.stop()

try:
    if st.user.get('iss') != config['issuer']:
        raise ValueError('Fournisseur inattendu.')
    owner = owner_id(config['issuer'], st.user.get('sub'))
    store = DossierStore(config['path'], config['encryption_key'])
    revision, saved = store.load(owner)
    revision_key = '_dossier_revision_' + owner
    if revision_key not in st.session_state:
        st.session_state[revision_key] = revision
    st.caption('La sauvegarde se fait lorsque vous cliquez sur Enregistrer. Elle inclut les mêmes données que le dossier téléchargé, sans les historiques de marché importés.')
    st.write('Un dossier est disponible sur votre compte.' if saved else 'Aucun dossier enregistré sur votre compte.')
    overwrite = st.checkbox('Remplacer la sauvegarde existante par mes données actuelles') if saved else True
    if st.button('Enregistrer mon dossier', type='primary', disabled=not overwrite):
        st.session_state[revision_key] = store.save(owner, export_dossier(st.session_state), st.session_state[revision_key])
        st.success('Dossier enregistré sur votre compte.')
    replace = st.checkbox('Remplacer les données de cette session par le dossier enregistré')
    if st.button('Reprendre mon dossier', disabled=saved is None or not replace):
        restore_dossier(st.session_state, saved)
        st.session_state[revision_key] = revision
        st.success('Dossier repris. Retrouvez votre projet et votre portefeuille dans Mon assistant.')
    if saved is None and st.session_state[revision_key] != revision:
        st.info('La sauvegarde a été supprimée dans une autre session.')
        if st.button('Prendre en compte cette suppression'):
            st.session_state[revision_key] = revision
            st.rerun()
    with st.expander('Supprimer ma sauvegarde'):
        confirmed = st.checkbox('Supprimer le dossier enregistré sur mon compte')
        if st.button('Supprimer la sauvegarde', disabled=not confirmed):
            st.session_state[revision_key] = store.delete(owner, st.session_state[revision_key])
            st.success('Sauvegarde supprimée. Les données de cette session restent disponibles.')
except (ValueError, KeyError, OSError, sqlite3.Error, InvalidToken):
    st.error('Impossible de terminer cette opération. En cas de modification depuis un autre appareil, reprenez le dossier enregistré avant de réessayer. Vous pouvez toujours télécharger vos saisies actuelles.')

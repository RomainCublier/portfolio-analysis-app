# Sauvegarde avec un compte

Cette integration est desactivee par defaut. Elle utilise la connexion OIDC native
de Streamlit : https://docs.streamlit.io/develop/api-reference/user/st.login
Les mots de passe sont geres par le fournisseur de connexion.

Configurer les secrets de deploiement (ne jamais les committer) :

```toml
[auth]
redirect_uri = "https://VOTRE-DOMAINE/oauth2callback"
cookie_secret = "SECRET-ALEATOIRE"
client_id = "CLIENT-OIDC"
client_secret = "SECRET-OIDC"
server_metadata_url = "URL-DISCOVERY-OIDC"

[dossier_storage]
enabled = true
issuer = "ISSUER-EXACT-DU-FOURNISSEUR"
path = "/volume-prive-persistant/dossiers.sqlite3"
encryption_key = "CLE-FERNET"

[billing]
enabled = true
issuer = "ISSUER-EXACT-DU-FOURNISSEUR"
path = "/volume-prive-persistant/dossiers.sqlite3"
encryption_key = "AUTRE-CLE-FERNET"
secret_key = "sk_live_..."
price_id = "price_..."
offer_name = "Acces QuantDesk V1"
price_label = "PRIX ET PERIODICITE EXACTS"
```

Generer la cle avec `cryptography.fernet.Fernet.generate_key()`. Garder cette cle
hors du volume de donnees et en conserver une copie securisee : sa perte rend
les dossiers illisibles. Le repertoire doit deja exister, etre prive et accessible
uniquement au service. Utiliser HTTPS et un volume durable, pas le filesystem
ephemere d'un hebergeur. Ce stockage SQLite vise une seule instance applicative.

Les identites sont derivees de (issuer, sub), jamais d'un email saisi.
Les dossiers sont valides avant sauvegarde/restauration, chiffres avec Fernet,
et lies a leur proprietaire dans le contenu chiffre. Les revisions bloquent
l'ecrasement par un ancien onglet. Une suppression garde un identifiant et une
revision techniques pour bloquer les anciennes sessions, mais retire le contenu.
Les sauvegardes d'infrastructure et leur retention restent a configurer.

L'enregistrement et la reprise sont explicites, pas automatiques. Une connexion
ouvre une nouvelle session : exporter les essais invites avant de se connecter.
La suppression du dossier ne supprime pas le compte chez le fournisseur OIDC.

Le paiement utilise une session Stripe Checkout creee cote serveur. Le droit
d'acces n'est enregistre qu'apres recuperation de la session, concordance de
l'identite interne et verification d'un abonnement `active` ou `trialing`. Les
identifiants Stripe sont chiffres dans la table `entitlements`; utiliser une cle
distincte de celle des dossiers. Le statut est reverifie au maximum toutes les
cinq minutes pendant une session. Un abonnement `past_due`, `canceled` ou
incompatible ferme l'acces. Le portail Stripe permet la gestion et la resiliation.

Configurer dans Stripe le produit, le prix recurrent, la fiscalite, les emails,
le portail client, les conditions de remboursement et les documents contractuels.
Tester d'abord avec `sk_test_` et un `price_` de test, puis remplacer ensemble la
cle et le prix. Aucun secret Stripe ne doit etre transmis au navigateur ou committe.

Avant ouverture au public : configurer le fournisseur et le volume, verifier
le parcours reel avec deux comptes distincts, tester la restauration des backups,
definir retention/suppression et information des utilisateurs. Ces operations
d'exploitation ne sont pas effectuees par les tests locaux.

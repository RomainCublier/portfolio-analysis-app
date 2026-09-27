# Lancement de la V1

Cette configuration prepare un hebergement ; elle ne publie pas l'application.
Le mode sans compte reste utilisable avec telechargement/reprise du dossier.

Vercel n'est pas retenu pour cette application Streamlit : la V1 a besoin d'un
processus Python persistant et de WebSockets. Utiliser un hebergeur de conteneur
compatible. Suivre aussi `LAUNCH_CHECKLIST.md` ; `APP_ENV=production` bloque le
parcours tant que la configuration commerciale obligatoire n'est pas complete.

## Local

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/start_app.py
```

Ouvrir http://localhost:8501 sur la machine qui execute l'application.
Le lanceur accepte la variable PORT de l'hebergeur. Les connexions doivent
etre exposees en HTTPS par cet hebergeur avec prise en charge des WebSockets.

## Conteneur

```sh
docker build -t portfolio-assistant .
docker run --rm -p 8501:8501 portfolio-assistant
```

Le processus tourne sous un utilisateur non administrateur. Le contexte de
construction exclut les secrets, dossiers locaux et bases de donnees. Le
healthcheck verifie uniquement que le serveur repond, pas la qualite des calculs.
Le conteneur reste a construire et tester sur une machine disposant de Docker.

## Controle avant ouverture

Les fichiers `config/production.env.example` et `config/secrets.toml.example`
inventorient toutes les valeurs a fournir sans contenir de secret reel. Une fois
les variables chargees et le fichier de secrets place sur l'hebergeur, executer :

```sh
python scripts/check_release.py
```

La commande retourne un code non nul et la liste des blocages tant que l'URL,
l'editeur, OIDC, Stripe, les documents ou les droits de donnees sont incomplets.
Elle ne remplace ni la validation juridique ni les essais reels des fournisseurs.

## Comptes et donnees

Configurer un fournisseur OIDC et un volume prive persistant seulement si les
comptes sont actives, suivant ACCOUNT_STORAGE.md. Ne pas embarquer les secrets
dans l'image. Le volume doit etre accessible a l'UID 10001. Garder une seule
instance pour la sauvegarde SQLite actuelle. Les connexions reelles OIDC restent
a tester avec deux comptes distincts avant ouverture aux utilisateurs.

Le code contient une integration Stripe Checkout facultative, inactive sans les
secrets `billing`. Les flux
historiques sont des integrations de recherche ; les droits de reutilisation
commerciale restent a obtenir. Le calendrier emetteur n'est pas une verification
independante. La validation mobile et le test utilisateur restent necessaires.

# QuantDesk — comprendre et préparer ses investissements

Prototype Streamlit pour particuliers : projet d’investissement, projection
pédagogique et état des positions réelles. Les anciens outils sont regroupés
dans le laboratoire et restent expérimentaux.

```sh
python -m pip install -r requirements.txt pytest
python -m streamlit run app.py
python -m pytest -q
```

Les nouveaux parcours ne nécessitent aucune clé API ni donnée de marché.
Les projets restent en session : télécharger le JSON pour les reprendre.
L’export CSV des positions est un état daté, pas un historique de transactions.

Voir [l’audit et la feuille de route](docs/FOUNDATIONS.md) pour les défauts
identifiés dans les anciens calculs et les critères avant commercialisation.

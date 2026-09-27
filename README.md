# QuantDesk — comprendre et préparer ses investissements

V1 Streamlit pour particuliers : projet d’investissement, compréhension PEA/CTO,
portefeuilles fictifs, simulations pédagogiques et suivi manuel. Les anciens
outils quantitatifs restent hors du parcours public.

```sh
python -m pip install -r requirements.txt pytest
python -m streamlit run app.py
python -m pytest -q
```

Le parcours de base ne nécessite aucune clé API.
Les projets restent en session : télécharger le JSON pour les reprendre.
L’export CSV des positions est un état daté, pas un historique de transactions.

Voir [l’audit et la feuille de route](docs/FOUNDATIONS.md) pour les défauts
identifiés dans les anciens calculs et les critères avant commercialisation.

Le [socle de données et les méthodes](docs/DATA_AND_METHODS.md) décrivent le
catalogue de supports, ses informations manquantes et le noyau strict de backtest.
La page « Explorer les supports » fonctionne hors ligne à partir du catalogue daté.
Aucune licence commerciale de données n'est approuvée par ce dépôt. Une instance
configurée en production reste donc bloquée jusqu'à validation explicite des
droits, des informations légales et du paiement. Voir
[`docs/LAUNCH_CHECKLIST.md`](docs/LAUNCH_CHECKLIST.md).

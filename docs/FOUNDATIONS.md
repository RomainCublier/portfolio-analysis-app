# Première étape : un parcours compréhensible et vérifiable

## Produit retenu
Deux espaces : explorer des portefeuilles fictifs et suivre les positions réellement détenues.
Public initial : particuliers débutants, PEA/CTO. Le projet enregistré, l’allocation cible
et les transactions réelles doivent rester distincts. Aucun lien de parrainage ni
affiliation avec un employeur n’est introduit.

## Livré dans cette branche
- Entrée débutant : objectif, capital, versements, horizon, épargne de précaution,
  expérience et réaction à une perte illustrative. Ce n’est pas un questionnaire
  d’adéquation complet et aucune allocation n’en est déduite.
- Projection déterministe avec hypothèses explicites, frais, inflation, versements
  en fin de mois. Aucun appel marché, taux prévisionnel ni backtest présenté comme réel.
- Export/import JSON versionné du projet (pas des hypothèses de projection).
- État des positions réel daté, en EUR, avec liquidités, regroupement des doublons
  et export CSV. Aucun historique de performance inventé depuis cet état.
- Navigation séparant le nouveau parcours du laboratoire existant.
- Tests numériques de référence et tests d’intégration Streamlit.

## Audit ciblé du code existant (non exhaustif)
Constats sur la branche main au démarrage de ce travail :

| Fichier | Risque constaté | Avant réutilisation commerciale |
|---|---|---|
| pages/portefeuille.py | Montants « €/ $ » mélangés, exemples préremplis | Devise de reporting et conversion documentée ; entrée vide |
| pages/portefeuille.py | Poids écrasés pour tickers dupliqués ; renormalisation des supports couverts | Agréger les lignes ; exposer la couverture manquante |
| pages/portefeuille.py | Rendements manquants remplacés par zéro sous 60 lignes | Politique de données manquantes explicite et vérifiée |
| core/data.py, utils/data_loader.py | Fallback sur la première couche de colonnes et auto_adjust non explicite | Sélection contractuelle du champ, contrôle des prix ajustés |
| core/metrics.py | Drawdown sans valeur initiale : perte du premier jour omise | Ajouter la base initiale et cas de test indépendant |
| core/metrics.py | Somme des rendements avec valeurs manquantes ; pondérations non validées | Refuser les entrées incomplètes et expliciter le rééquilibrage implicite |
| utils/metrics.py | Mesure de valeur sans traitement des apports/retraits | Séparer valorisation, rendement TWR et rendement investisseur |
| requirements.txt | st.navigation utilisé malgré minimum Streamlit 1.32 | Minimum corrigé à 1.36 ; environnement verrouillé à prévoir |

Les calculs historiques restent inchangés dans le laboratoire. Les nouveaux écrans
n’en dépendent pas. Leur conservation ne constitue pas une validation.

## Prochains lots et critères de passage
1. **Contrat de données** : univers ETF limité, ISIN/place/devise, distributions,
   séries ajustées, éligibilité PEA vérifiée et datée, couverture et fraîcheur,
   droits commerciaux convenant au calcul, stockage, affichage et export.
2. **Backtest** : moteur séparé de Streamlit ; calendrier, devise EUR, flux,
   frais et rééquilibrages explicites ; tests contre cas calculés à la main ;
   historique réel séparé des proxies et périodes hors échantillon.
3. **Portefeuilles fictifs** : comparaison de plusieurs allocations, explication
   des classes d’actifs, exemples de supports seulement après validation du référentiel.
4. **Positions réelles** : registre d’opérations (achats, ventes, frais, dividendes,
   transferts), liquidités par compte, rapprochement avec relevés et tests TWR.
5. **Persistance** : comptes, séparation des données des utilisateurs, stockage sécurisé,
   export/import complets, suppression et sauvegardes. La session Streamlit actuelle
   ne constitue pas une sauvegarde durable. Le CSV actuel n’est pas réimportable dans l’UI.
6. **Suivi et IA** : news sourcées avec droits adaptés, explications des expositions,
   simulation d’un versement et du rééquilibrage ; pas de causalité inventée.

Avant commercialisation : déterminer le cadre du service personnalisé sur son
fonctionnement concret ; le mot « proposition » ne résout pas cette qualification.
Ne pas utiliser de données ou code confidentiels d’un employeur pour valider le produit.

## Validation métier proposée à Romain
Vérifier les conventions de calcul, le sens des libellés et cinq parcours :
débutant sans réserve, horizon court, projet vingt ans, rendement négatif,
positions réelles détenues sur plusieurs comptes. Examiner en priorité ce qu’un
débutant pourrait interpréter comme garanti ou comme une performance réalisée.

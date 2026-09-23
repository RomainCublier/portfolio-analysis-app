# Versements et rééquilibrage historiques

## Convention de calcul

Le capital initial doit être strictement positif. Les séries de rendement total
et leurs métadonnées passent les mêmes contrôles que le backtest sans flux.
L'investissement est exprimé en unités fractionnaires de ces séries, sans
contrainte de taille de lot ni prix d'exécution garanti.

À chaque date, dans cet ordre :

1. Les positions existantes évoluent selon le ratio des niveaux de rendement total.
2. Le versement externe est investi selon les poids cibles saisis.
3. Si la date est désignée, le portefeuille entier est rééquilibré vers ces poids.

Un versement en fin de période ne reçoit aucun rendement antérieur à sa date.
Les dates de flux doivent appartenir au calendrier exact. Les retraits ne sont
pas pris en charge. Les dividendes incorporés dans les séries ne sont jamais
ajoutés comme versements externes. Les frais des fonds ne sont pas redéduits.

## Mesures distinctes

Avec V_t^- la valeur avant flux et V_(t-1)^+ la valeur après le flux précédent :

- Rendement de la sous-période : r_t = V_t^- / V_(t-1)^+ - 1.
- Indice de performance : I_0 = 1 ; I_t = I_(t-1) × (1 + r_t).
- Total versé : capital initial + somme des versements.
- Gain/perte en euros : valeur finale − total versé.

Le rendement TWR et la baisse maximale sont calculés sur I, pas sur la valeur
qui augmente avec les apports. Le TWR neutralise l'effet comptable des flux ;
ce n'est pas le TRI personnel. Investir de nouveaux apports aux poids cibles peut
modifier les poids futurs, donc la performance de la stratégie : neutraliser un
flux ne supprime pas son effet sur les décisions d'allocation.

Référence méthodologique : CFA Institute, GIPS Standards Handbook for Firms,
sections sur les valorisations aux flux externes et le chaînage géométrique :
https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/
Consulté le 23/09/2026. Cette référence de calcul n'est pas une revendication de
conformité GIPS, une vérification indépendante ou une certification de l'outil.

## Calendrier visible dans l'interface

La convention proposée est le dernier point observé de chaque mois après le mois
initial. Les mois manquants bloquent la génération du calendrier. Pour un mois
final incomplet, la dernière observation fournie est utilisée, avec avertissement.
Ce calendrier n'est pas présenté comme un calendrier boursier indépendant.
Il est affiché avant le bouton de calcul et repris dans le rapport.
Le rééquilibrage est facultatif et mensuel dans cette première interface.

Le journal exporte valeurs avant/après flux, apports, capital versé, gain/perte,
indice TWR et achats + ventes du rééquilibrage (hors investissement des apports).
Un second export conserve les poids réalisés après opérations à chaque date.
Le rééquilibrage conserve la valeur totale dans le modèle hors frais.

## Limites et contrôle réel

Pas de courtage, spread, fiscalité, délai de règlement, retraits, risque de
liquidité ou exécution intrajournalière. Ces omissions limitent la comparaison
de fréquences d'arbitrage. Aucun rééquilibrage n'est déclaré supérieur en général.
Les dates et niveaux restent ceux des imports de recherche, avec les limites de
calendrier et de droits d'utilisation décrites dans DATA_COLLECTION.md.

Le script `scripts/check_cashflow_scenario.py` reproduit deux scénarios sur la paire
2022 déjà contrôlée : 10 000 EUR initiaux, 12 versements de 1 000 EUR, poids cibles
60/40, avec ou sans rééquilibrage mensuel. Les montants sont des hypothèses
illustratives déclarées, pas des données de marché ni une allocation conseillée.
Le rapport `data/research/cashflow_2022_check.json` conserve ces hypothèses, la
provenance, les dates et les résultats. Même montant total versé : 22 000 EUR.
La faible différence observée entre les deux scénarios ne prouve aucune supériorité
et n'inclut pas les coûts de transaction.

```bash
python -m scripts.check_cashflow_scenario .local-data/ishares_europe.xls \
  .local-data/ishares_bonds.xls --retrieved-at 2026-09-23 \
  --output .local-data/cashflow_2022.json
```

La date doit refléter la récupération effective des exports utilisés.

# Fonds, actions et contrôle de l’allocation

## Périmètre du lot 3
Le catalogue n’est plus limité aux ETF. Le schéma v2 introduit le type du support
et distingue les champs applicables : une action n’a pas de frais de gestion de fonds,
un fonds actif n’est pas décrit comme répliquant son indicateur de comparaison.
La complexité du support, ses expositions et sa liquidité doivent être évaluées
indépendamment de l’expérience déclarée de l’utilisateur. Un ETF peut être concentré ;
un fonds actif n’est pas intrinsèquement une amélioration d’un ETF.

Trois exemples sont ajoutés, sans classement ni recommandation :
- [Comgest Monde C, FR0000284689](https://www.comgest.com/en/se/private-investor/funds/comgest-monde-c) : gestion active actions internationales,
  capitalisation EUR, frais courants 2,08 %, entrée maximum 2,50 %. L’indice de
  comparaison ne décrit pas ses positions réelles.
- [Carmignac Patrimoine A EUR Acc, FR0010135103](https://www.carmignac.com/en/our-funds/carmignac-patrimoine-FR0010135103-a-eur-acc/characteristics-risks) : fonds diversifié ; frais de gestion/administration publiés 1,80 %, autres
  coûts présentés séparément avec leurs conditions. Les 40/40/20 de l’indicateur
  de référence ne sont pas utilisés comme composition du fonds.
- [LVMH, FR0000121014](https://live.euronext.com/en/product/equities/FR0000121014-XPAR) : identité d’une action confirmée par la place de marché.
  Pas de cours, devise, éligibilité PEA ou ratios ajoutés sans vérification.

Les sources ont été consultées le 21 septembre 2026. Les compositions, coûts
distributeur et disponibilités courtiers restent à valider. Un frais d’entrée maximal
n’est pas un frais nécessairement payé. Les coûts conditionnels ne doivent pas être
additionnés sans comprendre leurs assiettes. Pas d’estimation automatique de coûts globaux.

## Allocation fictive dans l’interface
Sélection explicite des supports et pondérations totalisant 100 %. Pas de normalisation
silencieuse ni de sélection en fonction du profil. Des plafonds peuvent être activés
sur un support, la poche d’actions détenues directement et les expositions par émetteur.
Les valeurs de ces plafonds sont choisies par l’utilisateur : ce ne sont pas des lois
financières, des seuils réglementaires UCITS transposés au particulier, ou des plafonds
calibrés sur son profil. « Respectée sur ce critère » n’est pas « portefeuille validé ».
Le brouillon demeure en session, sans lien automatique avec les positions réelles.

## Transparisation partielle
Pour chaque support j et émetteur k : exposition connue E_k = somme_j w_j × h_jk.
Les h_jk doivent être des poids économiques long-only, non superposés, datés et sourcés,
avec identifiants d’émetteurs consolidés entre parts, fonds et titres détenus directement.
La composition d’un indice de référence n’est pas un substitut aux positions d’un fonds actif.

La somme d’une composition partielle peut être inférieure à 1 : le résidu est conservé
comme inconnu. Il n’est jamais redistribué sur les positions connues. Les compositions
futures ou âgées de plus de 35 jours sont écartées : seuil opérationnel configurable,
pas une garantie de représentativité. Les limites par émetteur sont indéterminées si
la couverture est incomplète, sauf dépassement déjà établi sur la partie connue.

L’interface ne dispose pas encore de compositions : elle annonce donc une couverture
inconnue. Les tests démontrent le calcul sur des fixtures artificielles uniquement.
Les expositions dérivées, shorts, levier, risque de contrepartie des swaps et liquidités
nécessitent des modèles distincts. Le moteur long-only ne doit pas leur être appliqué
en remplaçant les expositions économiques par le portefeuille de collatéral.

## Risque par covariance : noyau calculé, pas encore alimenté dans l’UI
Variance du portefeuille : σ² = wᵀΣw. Contribution d’Euler à la volatilité :
RC_i = w_i(Σw)_i / σ. La somme des contributions est égale à σ lorsqu’il est non nul.
Une contribution négative est possible et ne doit pas être ramenée arbitrairement à zéro.
La variance-covariance est le mécanisme de diversification de l’approche moyenne-variance
de Markowitz ([Portfolio Selection, Journal of Finance, 1952](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1952.tb01525.x)), pas une preuve que les
rendements futurs ou les risques extrêmes sont correctement représentés.

Les matrices doivent être alignées, finies, symétriques et semi-définies positives.
Le calcul conserve leur unité temporelle, sans annualisation implicite. Tolérance
numérique absolue : 1e-12 sur symétrie et valeurs propres. Les estimations de covariance,
leur période, leur stabilité, leur régularisation éventuelle et leur historique source
restent à définir. Aucun rendement attendu ni portefeuille optimal n’est inventé.

## Ce que ce lot ne couvre pas encore
Historique réel, corrélations estimées, risque de liquidité, stress tests, duration/
convexité, spreads de crédit, devises économiques, concentration sectorielle/géographique,
qualité de crédit, options/produits structurés et supports illiquides. Les fonds, actions,
obligations en direct et autres supports n’exigent pas les mêmes données. Ajouter une
famille au catalogue n’autorise pas à la calculer avec un modèle inadéquat.

La prochaine étape reste la validation du fournisseur de données et des droits, puis
le raccordement d’un historique et de compositions vérifiables. Aucune règle universelle
ne permet de certifier « toutes les règles de diversification » à partir de quelques poids.

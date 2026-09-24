# Suivi déclaratif — valeurs et mouvements externes

## Parcours

« Mon portefeuille réel » conserve une valeur totale par date, liquidités comprises. Une seconde saisie à la même date corrige cette observation. Le détail des positions reste celui du dernier état saisi ; ce prototype ne conserve pas les compositions historiques. Les dates peuvent être renseignées dans le désordre. Aucun cours n’est téléchargé et aucune interpolation n’est effectuée.

« Suivre mon évolution » contient les valeurs datées, les apports/retraits en espèces et le résultat d’une période choisie. Les mouvements ont un identifiant unique ; deux mouvements distincts de même date et montant sont permis. La correction consiste à supprimer la ligne erronée puis à la ressaisir. Les exports donnent les observations, mouvements et données exactes du calcul.

## Méthode

Référence : [CFA Institute, GIPS Standards Handbook for Firms, section 2 — Modified Dietz Method](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/), consulté le 24 septembre 2026.

Pour deux valorisations de fin de journée `V0` et `V1`, sur `D` jours calendaires :

- Flux `C_i` : positif pour un apport, négatif pour un retrait.
- Période : date initiale exclue, date finale incluse.
- Poids de durée : `w_i = (date finale - date du flux) / D`.
- Gain/perte : `G = V1 - V0 - somme(C_i)`.
- Dietz modifié : `R = G / (V0 + somme(w_i * C_i))`.

Les mouvements sont supposés réalisés en fin de journée. Un flux final a un poids nul. Le résultat n’est ni annualisé ni chaîné ; ce n’est pas un TWR exact. Des flux importants associés à des rendements non linéaires réduisent la précision de l’estimation. Aucune conformité GIPS n’est revendiquée.

## Conditions du produit

Avant affichage, l’utilisateur confirme un périmètre de comptes constant, des valorisations complètes et tous les mouvements externes en espèces, y compris leur absence éventuelle. Les transferts entre comptes suivis ne sont pas des flux externes. Achats/ventes, dividendes conservés et frais prélevés sur les comptes ne sont pas saisis comme apports/retraits. Les frais et impôts sont reflétés uniquement dans les valeurs déclarées. Aucun ajustement fiscal n’est calculé.

Transferts de titres, levier, opérations non rapprochables et changement du périmètre de comptes sont hors périmètre. La confirmation est liée aux deux observations sélectionnées et aux mouvements de la période ; leur modification la réinitialise. Elle n’est pas enregistrée dans le dossier ni restaurée à l’import.

Les valeurs initiales nulles, capitaux pondérés non positifs et estimations inférieures à −100 % bloquent le pourcentage. Le gain/perte en euros reste affiché après confirmation, avec le motif de blocage. Cette convention conservatrice du produit n’est pas une règle GIPS. Aucun rapprochement courtier ne certifie la qualité des saisies.

## Dossier et validation

Dossier version 2 : valeurs totales et mouvements inclus. Migration version 1 : création d’une observation depuis l’état existant, aucun mouvement inventé. Une contradiction entre cet état et la valeur totale de sa date bloque l’import. Validation complète avant remplacement de la session ; limite de 8 Mo UTF-8, 1 000 dates distinctes et 1 000 mouvements. La conservation reste manuelle par export/import.

Tests : exemple numérique du manuel CFA, apport sans gain, retrait final, exclusion du flux initial, mouvements distincts à la même date, pourcentages non interprétables, confirmation obligatoire, correction des valorisations, migration du dossier et invalidation de la confirmation après modification.

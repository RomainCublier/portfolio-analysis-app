# Données et méthodes — lot 2

## Trois objets distincts
1. **Référentiel** : caractéristiques d'une part identifiée par ISIN, document source,
   date de consultation et, lorsqu'elle est disponible, date du document.
2. **Historiques** : observations datées, devise, méthode de rendement, provenance,
   empreinte des données brutes et statut des droits. Aucun flux marché nouveau connecté ici.
3. **Hypothèses** : paramètres choisis pour une projection, jamais présentés comme
   caractéristiques d'un fonds ou comme estimations calibrées sur un historique absent.

## Premier catalogue
`data/catalog/instruments.json` contenait initialement sept identités : six fiches de caractéristiques
documentées et une fiche overnight DWS à compléter. Univers de recherche limité,
ni inventaire du marché ni sélection des « meilleurs » supports. Sources émetteurs
consultées le 21 septembre 2026 ; seule la fiche Amundi est explicitement datée
du 31 août 2026. Toutes les caractéristiques non nulles d'une ligne proviennent
de sa source. La catégorie est une classification éditoriale de l'exposition.

La page DWS dynamique n'a pas livré de caractéristiques lisibles : seul le nom/ISIN
a été confirmé dans le résultat de recherche officiel. Frais, indice et autres
champs restent nuls. Les sources secondaires n'ont pas servi à remplir ces champs.

Pour Amundi, l'éligibilité PEA est explicitement indiquée dans le reporting (pages 1 et 2).
Pour les autres supports, elle reste **inconnue**, et non « non ». Les pages iShares
britanniques parlent d'ISA : ce n'est pas un PEA. Pas de ticker universel inventé :
les futures cotations devront être identifiées par ISIN + place + devise + fournisseur.
La couverture de change reste inconnue lorsqu'elle n'a pas été explicitement vérifiée.
Une part en EUR ne prouve pas une couverture EUR.

Le benchmark USD affiché par iShares au niveau du fonds obligataire ne représente
pas automatiquement le benchmark de sa part EUR Hedged : note spécifique conservée.
Les frais TER et les frais de gestion/administration ne sont pas renommés en coût total
investisseur. Courtage, spread et fiscalité ne sont pas inclus dans ces chiffres.

Révision à 30 jours : choix opérationnel du prototype, pas garantie de fraîcheur.
Les documents évoluent ; l'historisation des versions des champs et des copies
licenciées des sources reste à construire. Les liens seuls ne sont pas un archivage.
Une fiche documentée ne garantit ni la disponibilité chez un courtier ni les droits
de redistribution. Tous les statuts commerciaux sont actuellement `not_assessed`.

## Contrat des historiques
`core/history.py` exige un calendrier d'observations explicite validé séparément.
Dates manquantes, doublons, valeurs non finies ou non positives, poids invalides,
devises incompatibles et dates antérieures à la création de la série sont refusés.
Aucun `fillna(0)`, forward-fill ou raccourcissement silencieux de la période.

Les séries doivent être documentées comme rendement total net : distributions
réinvesties, opérations sur titres correctement traitées et frais du fonds déjà
intégrés. Un label fournisseur « adjusted » ne suffit pas sans définition vérifiée.
Le noyau ne peut vérifier la véracité de la déclaration : contrôle et rapprochement
des données avec une seconde source restent nécessaires dans l'adaptateur.
Le SHA brut doit être calculé à l'ingestion ; ce module contrôle son format mais
ne dispose pas des octets bruts pour le recalculer. Le SHA normalisé est calculé.

`origin` distingue fonds réel, proxy et fixture synthétique. Le mode commercial
refuse les proxies/synthétiques et les droits non documentés. Ce contrôle est une
barrière technique interne, pas une analyse juridique des licences. Le registre
des contrats et leur périmètre (affichage, calcul, export, conservation) reste à relier.
Les prix identiques répétés, erreurs de fournisseur ou calendriers mal déclarés
ne sont pas détectés automatiquement par ce premier contrat.

## Calculs implémentés et limites
- **Buy-and-hold** : V(t)/V(0) = somme_i w_i × L_i(t)/L_i(0), où L est un niveau de
  rendement total net. Poids initiaux non négatifs totalisant 1, puis dérive des poids.
  Pas de rééquilibrage quotidien implicite, ni de frais TER déduits une seconde fois.
  Pas encore de versements, courtage, spread, fiscalité ou arrondis de parts dans ce noyau.
- **CAGR** : (V_final/V_initial)^(365,25/jours écoulés) − 1. Convention calendaires
  explicite ; ce taux sur un intervalle très court n'est pas une prévision annuelle.
- **Drawdown** : V(t)/max_{s≤t} V(s) − 1, valeur initiale incluse : la première baisse
  n'est pas perdue. Maximum drawdown = minimum de cette série.
- **Sharpe périodique ex post** : moyenne arithmétique des rendements différentiels
  divisée par leur écart-type échantillonnal. Série sans risque alignée obligatoire ;
  résultat indéfini (`None`) si variance nulle. Aucune annualisation implicite.
  Référence : [William F. Sharpe, The Sharpe Ratio, 1994](https://web.stanford.edu/~wfsharpe/art/sr/sr.htm).
  L'annualisation par racine du temps exige notamment des hypothèses sur les dépendances
  temporelles ; ce noyau ne l'applique pas sans politique explicite.

Markowitz, momentum, Monte Carlo et portefeuilles modèles ne sont **pas calibrés**
dans ce lot. Les ajouter sans univers historique, règles ex ante et contrôle des biais
de survivance/look-ahead produirait une précision trompeuse. Les données de test sont
explicitement artificielles et ne constituent aucune preuve de performance de marché.

## Prochaine étape concrète
Choisir et valider un fournisseur : échantillon des ISIN, qualité des ajustements,
calendriers, couverture EUR/FX, droits et coût pour le service envisagé. Archiver des
échantillons autorisés ; rapprocher les rendements de publications émetteurs ; puis
connecter le noyau à une page de backtest avec rapport de couverture. Ne pas présenter
les tests numériques de cette branche comme un backtest réel de ces sept ETF.

## Extension fonds et actions
Le lot 3 porte le catalogue à dix supports (sept ETF, deux fonds et une action).
Voir [MULTI_ASSET_RISK.md](MULTI_ASSET_RISK.md) pour les nouveaux champs, les limites
de couverture et les contrôles d’allocation. Schéma du référentiel : version 2.

## Import de recherche et écran historique

L’écran « Explorer un historique » accepte un CSV UTF-8 séparé par des virgules
(`date,identifiant…`) et un manifeste JSON version 1. Les exemples dans
`data/examples/` sont **synthétiques**, sans instrument réel ni source de marché.
Leurs URL `example.org` sont des marqueurs explicites, pas des sources vérifiées.

Chaque série porte les champs de `SeriesMetadata`. `raw_sha256` est l’empreinte
SHA-256 des octets du CSV entier, calculée avant import. `expected_dates` est un
calendrier déclaré séparément, avec `calendar_source_url`. L’import vérifie
l’empreinte, les identifiants, les dates exactes, l’absence de trous par rapport
à ce calendrier, la positivité, la devise EUR et le rendement total net déclaré.
Aucune interpolation, conversion de devise ou normalisation des poids.

Ces contrôles ne vérifient pas que la source existe, que les cours sont corrects,
que les distributions sont réellement réinvesties ou que le calendrier déclaré
est le bon. Ils ne détectent pas les prix figés. Les droits commerciaux restent
`unknown`, même si le fichier annonce `approved` : ils devront être validés côté
serveur hors du parcours d’import. Aucun fournisseur de marché n’est connecté.

Le calcul conserve les quantités initiales, sans rééquilibrage, flux, fiscalité
ni frais de transaction. Les frais de fonds déjà inclus ne sont pas redéduits.
La baisse maximale porte exclusivement sur les points observés, et peut donc
sous-estimer les pertes intrapériode. Ni volatilité annualisée ni Sharpe ne sont
inférés d’une fréquence inconnue. Le rapport exporte poids, méthode, provenance,
empreintes, période et métriques. La courbe est également exportable.

Avant production : valider un fournisseur (couverture par part/ISIN, rendement
total et opérations sur titres, calendriers, devises, historique des fonds clos,
corrections, droits d’affichage et de redistribution), conserver les réponses
brutes et contrôler indépendamment un échantillon contre les publications des
gérants. La présence publique de données ne vaut pas autorisation commerciale.

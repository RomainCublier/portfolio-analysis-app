# Parcours central et cap produit

Objectif : projet -> comparaison de portefeuilles fictifs -> comprehension des
supports et simulations -> conservation -> suivi des positions declarees.
Prioriser la completion de ce parcours avant toute nouvelle page annexe.

## Inspirations consultees le 25 septembre 2026

- Nalo, approche par projet : https://content.nalo.fr/help/comment-d%C3%A9finir-un-objectif-%C3%A0-mon-projet-nalo-faq
- Finary, synthese puis details : https://help.finary.com/fr/articles/15532920-decouvrir-la-vue-par-actif

Il s'agit d'une lecture des parcours documentes publiquement, pas d'un test de
leurs applications connectees. Reprendre la progression et la hierarchie des
informations, sans copier les marques ni revendiquer une fluidite mesuree.

## Premiere version

`pages/modeles.py` connecte le projet au dossier existant. Trois repartitions
editoriales identiques pour tous (30/70, 60/40, 90/10) illustrent la repartition
actions/obligations. Ce ne sont ni des allocations optimisees ni des profils
financiers valides. Les montants proviennent du projet de l'utilisateur.
Les supports sont choisis explicitement parmi le catalogue existant : ETF et
fonds actif pour la poche actions, un ETF obligataire documente pour l'autre.
Les univers actions ne sont pas equivalents. Pas de promesse de PEA complet.

Le choc instantane est une somme ponderee des variations saisies. Ce n'est pas
un backtest, une prevision ou une mesure de risque. Aucun rendement n'est deduit
du profil. Les poids sauvegardes reutilisent `allocation_draft` et le dossier v2.

La comparaison historique est integree dans cette page. Elle reutilise les imports
de recherche, exige les deux ISIN exacts et des series declarees de fonds en EUR.
Les trois repartitions utilisent les memes dates et apports, sans reequilibrage.
Une recuperation directe a la demande est disponible pour la paire Europe
IE00B4K48X80 / obligations couvertes EUR IE00BDBRDM35. Les exports sont controles
par l'adaptateur existant : identite, devise, capitalisation, dates et lacunes.
Le choix Europe est explicite, jamais substitue au Monde. Sources fixes, aucun
redirect suivi, volume et temps limites. Pas de mise a jour en arriere-plan.
Une seconde paire utilise IE00B441G979 (MSCI World couvert EUR) avec le meme
ETF obligataire. L'export expose Base Currency EUR, Fund Launch Date et l'identite
exacte de la courbe ; cette variante est controlee explicitement par l'adaptateur.
Ce support est distinct du Monde non couvert et ne le remplace pas. La page
emetteur annonce une radiation d'une ligne de cotation au 15 decembre 2026 :
la disponibilite operationnelle reste a verifier. Le chemin d'export UK teste
pour WPEA a renvoye HTTP 400 ; aucun historique WPEA n'est branche.

Mise a jour du 26 septembre : WPEA est maintenant branche via l'export suisse
anglophone (format Overview/Historical). Le chemin UK reste incompatible.
L'adaptateur verifie ISIN, devise EUR, capitalisation, ordre des dates et utilise
uniquement Fund Return Series. Une valeur manquante dans la periode refuse le
calcul ; aucune substitution par la VL ou l'indice. La paire WPEA/obligations a
passe les controles sur 100 dates du 9 aout au 31 decembre 2024. Ce court intervalle
est un controle technique, pas une selection de performance representative.
Empreintes et limites : `data/research/wpea_2024_check.json`.

La comparaison calculee reste visible pendant la session lors des interactions.
Une empreinte du projet, des supports, des observations, du calendrier et des
metadonnees invalide les anciens resultats si une entree change. Un import refuse
ou un support non couvert efface le resultat affiche. Ce cache reste hors du
dossier exporte : aucune conservation durable des historiques n'est revendiquee.
Les imports manuels restent declaratifs. Aucune voie ne valide les droits
commerciaux. Les historiques ne sont pas inclus dans le dossier.
Les exemples enregistres sont reconnus a leur composition exacte pour reprendre
les choix ; une allocation personnalisee n'est jamais arrondie vers un exemple.

Reference pedagogique : https://www.investor.gov/introduction-investing/getting-started/asset-allocation
Les poids des exemples sont un choix produit, pas une conclusion de cette source.

## Prochains travaux directement utiles

1. Documenter et verifier un petit univers de supports avec DIC particuliers,
   eligibilite et droits commerciaux ; comparer des parts reellement accessibles.
2. Connecter leurs historiques compatibles (devise, distributions, frais), puis
   afficher les periodes reellement couvertes dans ce meme parcours.
3. Faire tester le parcours de bout en bout : comprehension, choix, sauvegarde,
   reprise. Mesurer les blocages avant d'ajouter de nouvelles fonctionnalites.

La monetisation et la facilite d'usage ne sont pas demontrees par les tests de
code. Une offre presentee comme adaptee a une personne exige une analyse du
cadre applicable ; l'etiquette "proposition" ne suffit pas a exclure le conseil.
Reference AMF : https://www.amf-france.org/fr/actualites-publications/actualites/definition-du-service-de-conseil-en-investissement-lamf-met-jour-sa-doctrine

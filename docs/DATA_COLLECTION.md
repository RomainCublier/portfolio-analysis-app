# Collecte initiale — 22 septembre 2026

## Résultat concret

Dix sources officielles du catalogue ont été consultées. Le fichier
`data/research/annual_reference_returns.json` contient 65 rendements calendaires
publiés pour sept parts : cinq ETF iShares, Comgest Monde C et Carmignac Patrimoine
A EUR Acc. Chaque série conserve ISIN, devise, URL, section, date de consultation,
méthode d'extraction, précision et périmètre des frais. Les valeurs sont exprimées
en pourcentage, pas en décimal. La transcription est manuelle et n'a pas encore
fait l'objet d'un contrôle indépendant.

Les URL par instrument sont dans les fichiers JSON. `source_audit.json` consigne
les résultats et les limites de consultation des dix supports, y compris les
échecs. Une page consultée ne signifie pas qu'un flux automatique est connecté.
Les droits commerciaux restent non évalués. Ces données de recherche ne sont pas
chargées par les pages de calcul ou le catalogue public de l'application.

## Utilisation du lot

Ce lot sert de référence de rapprochement lorsqu'un fournisseur sera connecté.
Comparer la performance de la même part, dans la même devise, sur la même année,
avec la même base de rendement. La performance publiée à une décimale comporte
un arrondi : un écart allant jusqu'à environ 0,05 point de pourcentage peut venir
de cet arrondi seul. Un écart plus important doit être expliqué, pas corrigé en
modifiant arbitrairement les données. Le calendrier et les dates de valorisation
aux bornes de chaque période doivent aussi être vérifiés.

Ne pas transformer ces rendements annuels en cours quotidiens ou mensuels. Ils
ne permettent pas de simuler fidèlement des versements mensuels, des arbitrages
intra-annuels ou les pertes maximales quotidiennes. Ne pas comparer des séries
USD et EUR sans conversion documentée. Le libellé « total return » ne dispense
pas d'examiner les conventions fiscales et de réinvestissement du fournisseur.

## Anomalies et lacunes

- ETF Global Aggregate : performance de part en EUR, indice affiché en USD.
  La série de l'indice n'a pas été importée.
- ETF World Small Cap : seules les années 2019–2025 sont renseignées dans la
  table consultée. Les cases vides antérieures ne sont pas des rendements nuls.
- Amundi PEA Monde : reporting institutionnel consulté ; aucune année civile
  renseignée. Chercher les documents destinés aux particuliers avant usage dans
  ce parcours. Pas d'historique artificiel avant création de la part.
- Xtrackers overnight : contenu non lisible via l'outil de consultation.
- Comgest : les cinq positions visibles ne constituent pas la composition totale.
- LVMH : titres de communiqués visibles, mais pas de série ajustée récupérée.
- Aucun historique quotidien, flux de change, calendrier validé, jeu complet de
  distributions ou composition complète n'a été récupéré dans ce lot.

## Prochain contrôle fournisseur

Envoyer les ISIN exacts du catalogue dans un environnement de test autorisé.
Relever couverture, part, devise, première/dernière observation, trous, distributions,
splits, conventions d'ajustement et corrections. Calculer les rendements annuels
puis les rapprocher de ce lot. Conserver les réponses brutes horodatées et leurs
empreintes. Étudier séparément stockage, affichage, export et redistribution :
aucune approbation commerciale n'est déduite de l'accessibilité sur le web.

Les sources officielles servent de référence ; moteurs de recherche et sites
secondaires peuvent aider à les découvrir, sans remplacer la preuve par champ.

## Complément : sources difficiles et distributions

La fiche PDF Xtrackers a permis de compléter le catalogue. L'échec de lecture de
la page initiale reste consigné dans l'audit ; une source complémentaire documente
la résolution. L'historique quotidien n'est toujours pas récupéré.

`dividend_reference_events.json` conserve six versements LVMH relatifs aux exercices
2023–2025, issus de la page française de l'émetteur. Le communiqué du 23 avril 2026
corrobore les dates de paiement de l'exercice 2025. Les données ne sont pas réputées
vérifiées par deux sources indépendantes : elles viennent du même émetteur.
La date de détachement reste inconnue : le dernier jour dividende attaché n'est
pas le jour de détachement. Les événements ne sont pas injectés dans les calculs.
Le total fiscal annuel n'est pas un septième flux à additionner aux versements.
L'acompte futur annoncé pour décembre 2026 est exclu de ce lot historique.

`source_conflicts.json` conserve les versions contradictoires du calendrier LVMH
et justifie le choix du communiqué daté. Ne pas supprimer la trace d'un désaccord
après avoir sélectionné une valeur. Les droits de réutilisation des cours affichés
sur la page LVMH sont réservés selon sa mention Euronext ; aucun flux de cours
n'est extrait ou redistribué par ce lot.

L'article pédagogique Amundi pour particuliers confirme l'identité et la création
de la part ; il ne suffit pas à remplacer la documentation produit complète.
Le catalogue signale désormais le public professionnel du reporting existant.

## Premier calcul sur export quotidien réel — 23 septembre 2026

L'export public du bouton Download de la fiche iShares Europe (IE00B4K48X80)
a été récupéré. Son extension est `.xls`, mais son contenu est du XML Spreadsheet.
L'adaptateur `core/ishares_import.py` lit spécifiquement cette part en EUR à
capitalisation. Il utilise la colonne du fonds dans la feuille Growth of
Hypothetical 10,000, sans confondre celle-ci avec l'indice ou un cours exécutable.
Les cellules XML à indices explicites sont respectées.

Pour le 31 décembre 2024 au 31 décembre 2025, 254 observations passent le contrôle.
Les huit dates supplémentaires de la courbe absentes des VL répètent exactement
la valeur précédente : elles sont exclues et énumérées dans le rapport. Une
variation à une date sans VL bloque l'import. Une date de VL sans rendement total
bloque également l'import, comme les doublons et les bornes manquantes.
Le calendrier de VL est fourni par le même émetteur : ce n'est pas une validation
indépendante de la complétude. Une ligne de l'export ne contient qu'une donnée
d'indice, sans date ni fonds : elle est comptée dans le rapport, sans usage dans
la série du fonds. Toute ligne contenant une valeur du fonds sans date est refusée.

Le calcul 100 % ETF Europe sans flux produit 19,715 % en 2025, contre 19,7 % publié,
soit un écart compatible avec l'arrondi. La baisse maximale entre VL est d'environ
16,25 %. C'est un contrôle du moteur et de la source sur cette période, pas une
preuve de qualité pour tous les instruments ou d'une stratégie d'investissement.
Le rapport `data/research/ishares_europe_2025_check.json` contient les empreintes,
la méthode, les exclusions, la comparaison et les limites. Les cours et le fichier
source complet ne sont pas redistribués dans Git. L'export téléchargé se trouve
dans `.local-data/`, ignoré par Git ; sa conservation n'est pas un archivage distant.

Reproduction à partir de l'export dont l'URL figure dans le rapport :

```bash
python -m scripts.check_ishares_europe .local-data/ishares_europe.xls \
  --retrieved-at 2026-09-23 --output .local-data/rapport.json
```

Remplacer la date par celle de récupération effective pour un nouveau fichier.
L'émetteur peut réviser son export : vérifier l'empreinte avant de prétendre
reproduire exactement la même entrée. Les droits commerciaux restent non validés.
L'interface Explorer un historique accepte désormais cet export via un mode
d'import dédié, en complément du CSV accompagné de son manifeste. Aucun appel
réseau automatique n'est ajouté à l'application.

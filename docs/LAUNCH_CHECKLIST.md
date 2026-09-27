# Critères de lancement V1

Le code ne doit pas être confondu avec l’autorisation d’ouvrir un service
commercial. En production, l’application se bloque tant que la configuration
obligatoire n’est pas complète et que le catalogue conserve des droits
commerciaux `not_assessed`.

## Produit

- Parcours public limité à projet, PEA/CTO, portefeuilles fictifs, catalogue,
  allocation déclarée, dossier et suivi manuel.
- Laboratoire invisible sauf `QUANTDESK_ENABLE_LAB=true` dans un environnement
  interne.
- Markowitz, Monte Carlo, analyse d’actions, import avancé et profil automatisé
  ne font pas partie de la V1 publique.
- Aucun ordre, compte courtier, actualité ou prix temps réel n’est connecté.

## Configuration bloquante

Définir uniquement sur l’hébergeur :

```text
APP_ENV=production
APP_PUBLIC_URL=https://...
APP_LEGAL_PUBLISHER=...
APP_SUPPORT_EMAIL=...
APP_PRIVACY_URL=https://...
APP_TERMS_URL=https://...
APP_COMMERCIAL_DATA_RIGHTS_APPROVED=true
```

Configurer aussi les sections `auth` et `billing` des secrets suivant
`ACCOUNT_STORAGE.md`. La dernière variable ci-dessus atteste une validation
externe ; elle ne l’accorde pas.
Chaque support doit aussi porter `commercial_rights: approved` dans le catalogue.
Une URL de paiement ne suffit pas à définir l’offre, les remboursements, le droit
de rétractation, la TVA ou les conditions contractuelles.

## Données

- Obtenir une autorisation ou un fournisseur couvrant l’affichage commercial des
  caractéristiques et historiques utilisés.
- Les conditions iShares consultées interdisent notamment de vendre, publier ou
  redistribuer le contenu sans droit :
  https://www.ishares.com/uk/individual/en/compliance/terms-and-conditions
- Ne jamais transformer un import utilisateur en approbation commerciale.
- Conserver source, date de revue, devise, frais, indice, politique de revenus et
  lacunes visibles.
- Refaire les contrôles sur les fichiers réels avant chaque changement de source.

## Comptes et exploitation

- Configurer OIDC, HTTPS, volume privé durable et clé Fernet suivant
  `ACCOUNT_STORAGE.md`.
- Tester avec deux identités distinctes : création, sauvegarde, conflit entre
  onglets, suppression et restauration après backup.
- Une seule instance applicative tant que SQLite est utilisé.
- Configurer sauvegardes chiffrées, rotation, rétention, alertes de disponibilité
  et journalisation sans contenu financier personnel.

## Paiement et droit

- Faire valider le périmètre par un professionnel compétent : information générale,
  recommandation personnalisée, communication commerciale et simulations futures.
- Publier identité de l’éditeur, CGU/CGV, politique de confidentialité, contact,
  gestion des demandes de suppression et informations sur le risque.
- Configurer le produit et le prix chez le prestataire de paiement, puis tester
  paiement, échec, annulation, remboursement et facture en environnement test.
- Ne pas ouvrir l’abonnement tant que l’accès payé et la résiliation ne sont pas
  vérifiés de bout en bout.

## Recette

1. Exécuter `python -m pytest -q` et `python -m compileall -q app.py core pages scripts`.
2. Construire l’image Docker et contrôler `/_stcore/health`.
3. Suivre `FIRST_USER_TEST.md` sur ordinateur puis téléphone.
4. Tester au moins cinq débutants sans les guider ; consigner les blocages.
5. Vérifier que le laboratoire n’apparaît pas dans l’instance publique.
6. Contrôler les liens officiels, les dates de revue et les avertissements.
7. Sauvegarder la configuration et documenter une procédure de retour arrière.

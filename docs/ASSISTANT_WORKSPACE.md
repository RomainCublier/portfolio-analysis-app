# Espace assistant — version 1

L’accueil réunit les informations enregistrées de la session : projet, nombre de supports de l’allocation fictive, valorisation déclarée et ancienneté en jours. Il ne produit ni recommandation, ni score de risque, ni signal de marché. Aucun service IA ou appel de marché n’est utilisé.

Le journal conserve une date de saisie et une note libre. Une revue peut se conclure sans opération. Les notes importées restent des déclarations utilisateur, pas des faits vérifiés.

## Conservation

Le dossier JSON version 2 contient le projet, la dernière allocation examinée avec succès, le dernier état des positions (date, liquidités et lignes) le journal, les valeurs totales datées et les apports/retraits. Les dossiers version 1 restent importables : leur seul état devient le premier point de suivi, sans flux supposé. Les limites de concentration, historiques de marché, hypothèses et résultats de backtest ne sont pas inclus. L’import remplace ces données après validation complète ; une erreur préserve l’état existant.

Le fichier est en clair et contient des informations financières personnelles. Pas de compte utilisateur, base de données, chiffrement ou sauvegarde automatique. Aucune preuve d’authenticité des données importées n’est revendiquée.

Contrôles : taille maximale de 8 Mo, structure/version, clés dupliquées, ISIN et somme des poids, nombres finis et bornés, dates non futures, comptes PEA/CTO, longueur des notes et des libellés. Les supports absents du catalogue sont préservés et signalés dans la page allocation.

## Limites avant commercialisation

Cette fonctionnalité est un prototype de continuité du parcours. Authentification, stockage durable sécurisé, suppression/export des données, contrats de données, fonctionnement de l’agent et cadre de distribution restent à mettre en place. Pas de notification ni d’action en arrière-plan.

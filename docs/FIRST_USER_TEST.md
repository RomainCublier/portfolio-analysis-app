# Premiere prise en main

Parcours a tester dans la preversion locale :

1. Mon assistant : definir un projet avec un capital initial positif.
2. Comprendre PEA et CTO : demander a l'utilisateur d'expliquer la difference
   avec ses propres mots, sans l'aider.
3. Mon portefeuille fictif : comparer les repartitions et choisir deux supports.
4. Choisir Europe ou Monde couvert EUR avec l'ETF obligataire pour la periode
   de controle 2022, ou WPEA pour la courte periode documentee de 2024.
5. Recuperer les historiques officiels et lancer la comparaison.
6. Verifier la distinction entre argent verse, valeur finale et gain/perte.
7. Garder le portefeuille fictif, puis telecharger le dossier dans Mon dossier.
8. Reprendre le fichier dans une nouvelle session et retrouver la repartition.
9. Saisir deux valorisations et un versement, puis verifier la revue.

Lancer localement : `python -m streamlit run app.py` puis ouvrir
`http://localhost:8501`. Cette adresse n'est pas un hebergement public.

Points encore ouverts avant commercialisation : hebergement persistant,
connexion configuree, droits de donnees, revue du cadre de distribution et
test utilisateur observe. La preversion ne passe aucun ordre. Les positions
reelles restent declarees manuellement. Les historiques importes et resultats
de simulation ne sont pas inclus dans le fichier dossier.

Questions pour le test : l'utilisateur trouve-t-il seul la prochaine etape ?
Distingue-t-il un exemple d'une proposition adaptee ? Comprend-il les montants
et la periode affichee ? Retrouve-t-il son travail sans aide ?

Avec les secrets de test OIDC/Stripe : verifier utilisateur sans abonnement,
paiement reussi, retour sur `/offre`, ouverture de l'assistant, portail client,
annulation puis fermeture de l'acces apres expiration. Utiliser exclusivement
le mode test Stripe ; ne saisir aucune carte reelle pendant la recette.

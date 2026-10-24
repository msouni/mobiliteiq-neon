# MobilitéIQ — PostgreSQL sur Neon, équipe de 5

Ouvrez GUIDE_NEON_3_ETAPES.html pour reproduire le projet de bout en bout.

- Développement : VS Code connecté à WSL, aucun serveur PostgreSQL local nécessaire.
- Base réelle : PostgreSQL sur Neon, base mobiliteiq.
- Collecte automatique : .github/workflows/ingestion-neon.yml, déclenchement horaire à la minute 17 UTC, sans dépendre du PC d'un membre.
- Fréquences : travaux et météo une fois par créneau horaire UTC; RTSS et débit une fois par jour UTC.
- Rapports : Power BI connecté au serveur Neon, actualisation à configurer séparément.
- Tests : PostgreSQL jetable dans la CI; aucun secret Neon transmis aux tests GitHub.

Copiez .env.example en .env et renseignez la connexion DIRECTE Neon avec sslmode=require. Les noms mobiliteiq, mobiliteiq_demo et mobiliteiq_test sont vérifiés. DATABASE_URL_DEMO et DATABASE_URL_TEST sont obligatoires pour leurs bases respectives si vous utilisez le mode cloud. Le mode de connexion mutualisé (-pooler) est refusé car le projet utilise des verrous de session.

Commandes depuis la racine :

```bash
python -m mobiliteiq check-db
python -m mobiliteiq init-db
python -m mobiliteiq run --force
```

Ajoutez ensuite le secret GitHub NEON_DATABASE_URL et lancez Actions → Collecte Neon → Run workflow.

Les données acceptées et leur historique sont dans Neon. Les fichiers bruts de chaque exécution GitHub sont conservés dans ses artifacts pendant 1 jour par défaut, sous réserve des quotas GitHub. Téléchargez-les avant expiration si vous voulez les conserver. Ce stockage temporaire ne constitue pas un lac permanent. Aucun transfert automatique de l'ancienne base locale n'est effectué.

L'entraînement ML et les scores restent des commandes manuelles. Les modèles joblib sont conservés dans models/ sur le poste qui les entraîne : ce dossier doit être sauvegardé pour réutiliser le modèle. Les rapports opérationnels et la collecte fonctionnent sans modèle.

La livraison prépare le code et la procédure. Aucun compte Neon, dépôt GitHub ou rapport Power BI n'a été créé ou configuré pour vous. Voir docs/VALIDATION_NEON.md.

Les anciens guides et fichiers Docker dans docs/version_locale concernent une autre architecture. Utilisez uniquement le nouveau guide pour ce parcours Neon.

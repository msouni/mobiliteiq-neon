# Validation de la version Neon — 22 octobre 2026

## Vérifications réalisées

- 19 tests locaux réussis; 5 tests PostgreSQL ignorés faute de serveur de test configuré.
- Tests spécifiques : connexion directe, exigence TLS, interdiction du mode pooler, sélection stricte des bases et absence de repli vers la production pour les tests.
- Test du calendrier : une collecte de l'heure précédente commencée en retard n'empêche pas celle du créneau courant.
- Les tests d'origine de validation des données et du calendrier sont conservés.

## Vérifications qui nécessitent vos comptes

Aucune connexion réelle Neon, aucune exécution GitHub Actions, aucun accès Power BI n'a été exécuté avec vos identifiants. Les tests d'intégration PostgreSQL devront réussir dans la CI ou votre base dédiée. Les workflows ont été relus et leur structure vérifiée localement; seule une exécution GitHub prouvera leur fonctionnement dans votre dépôt.

Les vérifications HTTP des quatre sources réalisées lors de la livraison précédente étaient positives sur un échantillon par source; elles ne prouvent pas la disponibilité future ou la qualité de chaque lot.

Le projet prépare une nouvelle base cloud. Il ne migre pas automatiquement une ancienne base locale. Les archives GitHub expirent après un jour par défaut et dépendent des quotas. Les modèles ML sont conservés sur le poste d'entraînement et ne sont pas utilisés par le workflow automatique.

## Mise en service attendue

Suivre GUIDE_NEON_3_ETAPES.html : check-db, init-db, collecte manuelle, premier workflow GitHub, collecte planifiée, réconciliation SQL/Power BI, puis test d'actualisation du rapport. Archiver les résultats obtenus avec la date et le commit dans docs/UAT.md.

# Validation de la version automatisée — 22 octobre 2026

- Tests locaux Python : 12 réussis, 5 ignorés (tests PostgreSQL nécessitant une base dédiée).
- Compilation des modules Python : réussie.
- Validation de la configuration Docker Compose : réussie.
- Échantillons HTTP des quatre sources : HTTP 200, GeoJSON FeatureCollection, aucun champ configuré manquant sur le premier objet reçu. Résultats détaillés dans VERIFICATION_SOURCES.json. Cela ne valide pas l'intégralité des lots, la pagination complète ou la fraîcheur des observations météo.
- Docker installé mais moteur Linux arrêté sur le poste : aucun conteneur lancé, aucune ingestion réelle écrite en base, aucune validation PostgreSQL exécutée localement.

Les tests ajoutés couvrent le premier démarrage, les échéances propres aux sources, le délai de reprise après échec et le redémarrage à partir d'une date persistée. Un test PostgreSQL supplémentaire couvre le cycle des quatre sources, une panne isolée, la validation automatique et l'absence de nouvelle collecte avant échéance. Le workflow GitHub existant exécute ces tests avec PostgreSQL; il n'a pas été déclenché depuis cette livraison.

La configuration initiale conserve le territoire de Québec : [-71.6, 46.6, -71.0, 47.1]. Les champs et fréquences sont configurables. Le traitement des lots réels, les vues BI et la reprise après interruption devront être confirmés après démarrage selon GUIDE_AUTOMATISATION.md.

Les fichiers docs/VALIDATION.md et les guides archivés décrivent la version d'origine; ce document décrit uniquement les vérifications de la présente livraison.

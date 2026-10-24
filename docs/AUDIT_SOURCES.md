# Audit des sources — à reprendre sur votre poste

Échantillons et collecte d'audit obtenus lors de la préparation : travaux 61, débit 789,
RTSS 1 075, météo 99. Normalisation sans rejet pour ces réponses. Les volumes évoluent.
Le filtrage WFS et la pagination RTSS ont été exercés sur ces réponses.

| Source | Licence et attribution | Champs et unités | Fréquence publiée | Retard observé | Validation locale |
|---|---|---|---|---|---|
| Travaux MTMD | À relever sur la fiche actuelle | identifiant, routeAutoroute; dates brutes à documenter | À relever | À mesurer | À faire |
| Débit MTMD | À relever sur la fiche actuelle | val_djma_annee_1, année djma_annee_1 | À relever | Ce n'est pas un débit instantané | À faire |
| RTSS MTMD | À relever sur la fiche actuelle | ide_sous_r, num_route, géométrie EPSG:4326 | À relever | À mesurer | À faire |
| Météo ECCC | À relever sur la fiche actuelle | UTC_DATE, TEMP °C, PRECIP_AMOUNT mm, WIND_SPEED km/h | À relever | Comparer UTC_DATE à collecte | À faire |

Fréquences d'acquisition proposées : 30 min / 24 h / 24 h / 60 min.
Périmètre proposé : bbox [-71.6,46.6,-71.0,47.1].

Vérifier l'année DJMA, les flags météo, les dates MTMD et les unités dans les métadonnées.
Les valeurs vides restent manquantes. Les codes spéciaux non documentés doivent être
normalisés explicitement ou rejetés, jamais interprétés comme des mesures réelles.

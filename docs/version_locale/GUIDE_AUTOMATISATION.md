# Démarrer MobilitéIQ en trois étapes

## 1. Préparer

Installez et démarrez Docker Desktop avec les conteneurs Linux. Extrayez le projet dans un nouveau dossier. Ouvrez PowerShell dans ce dossier.

```powershell
Copy-Item .env.example .env
notepad .env
```

Remplacez PGPASSWORD par un mot de passe local. Évitez `$` dans le mot de passe pour éviter l'interpolation Compose. Les paramètres PGHOST de cet exemple servent à l'exécution Python locale; Compose utilise automatiquement le service `db`. Si le port 5432 est déjà occupé, ajoutez `DB_PORT=5433` dans .env; Power BI devra alors utiliser localhost:5433.

## 2. Démarrer les quatre ingestions

```powershell
docker compose up -d --build
docker compose ps
docker compose logs -f --tail 100 ingestion
```

Le premier démarrage télécharge les dépendances et crée une nouvelle base dans un volume Docker. Il ne migre pas votre ancienne base WSL. Les quatre collectes commencent immédiatement, dans l'ordre RTSS, débit, météo, travaux. Elles sont séquentielles pour éviter la surcharge et les conflits de publication. Ctrl+C ferme le suivi des journaux; les services continuent à fonctionner.

| Source | Fréquence après réussite | Après échec |
|---|---|---|
| Travaux | 60 minutes | 5 minutes |
| Météo | 60 minutes | 5 minutes |
| Débit DJMA | 1 jour | 5 minutes |
| Réseau RTSS | 1 jour | 5 minutes |

La boucle vérifie le calendrier toutes les 60 secondes après chaque cycle. Les temps de téléchargement et de traitement peuvent décaler les échéances. Modifiez config/sources.json puis reconstruisez le service pour changer les fréquences.

La validation automatique remplace l'ancien `validated: true` à saisir manuellement : chaque réponse doit être GeoJSON, les champs configurés doivent être présents, les coordonnées et les valeurs doivent être valides. Un taux de rejet supérieur à 10 % bloque la publication; un lot non vide présentant au plus 10 % de rejets peut publier ses lignes valides. Un lot vide est accepté seulement pour les travaux. Aucun champ inconnu n'est deviné : un changement de schéma nécessite de corriger la configuration. Le brut et les rejets sont conservés.

Le calendrier est persistant en base. Après redémarrage, seules les sources arrivées à échéance sont collectées. Les anciens traitements interrompus sont marqués en échec. Un verrou PostgreSQL évite deux traitements simultanés, y compris avec la commande manuelle `run`.

Pour un démarrage après redémarrage du PC, activez le démarrage de Docker Desktop à l'ouverture de session. La politique `unless-stopped` redémarre les services avec Docker, sauf s'ils ont été arrêtés explicitement. Pour du fonctionnement 24 h/24, installez le projet sur un serveur toujours allumé. Les périodes éteintes ne permettent pas de reconstruire les anciens états des travaux.

## 3. Vérifier et consulter

```powershell
docker compose exec db psql -U mobiliteiq -d mobiliteiq -c "SELECT * FROM bi.etat_sources;"
docker compose exec db psql -U mobiliteiq -d mobiliteiq -c "SELECT * FROM bi.ops_alertes;"
```

Chaque source doit finir par avoir une réussite. `derniere_tentative_utc`, `derniere_reussite_utc`, le statut, les rejets et l'erreur distinguent les pannes des données valides. Les indicateurs de fraîcheur sont réévalués à chaque cycle. Le retard réel des observations météo est aussi surveillé. Les alertes sont accessibles en base et dans les journaux; aucun message externe n'est envoyé.

Dans Power BI, connectez PostgreSQL sur `localhost:5432`, base `mobiliteiq`, utilisateur `mobiliteiq`, avec le mot de passe de .env. Consultez `bi.etat_sources`, `bi.observations_courantes`, `bi.fact_entraves` et `bi.fact_secteur_heure`. Cette dernière reste ancrée sur l'instantané travaux; une météo arrivée ensuite ne s'y rattache qu'au prochain instantané travaux.

L'ingestion et les vues PostgreSQL se mettent à jour automatiquement. Un rapport Power BI en mode Import conserve ses données jusqu'à son actualisation : configurez son actualisation planifiée et la passerelle si le service doit joindre votre base locale, ou un mode DirectQuery compatible avec votre rapport. Aucun PBIX ou compte Power BI n'est configuré par ce paquet.

### Maintenance

- Arrêter : `docker compose stop`.
- Reprendre : `docker compose up -d`.
- Mettre à jour le code : `docker compose up -d --build`.
- Surveiller les erreurs : `docker compose logs --tail 200 ingestion`.
- Ne pas utiliser `docker compose down -v` : cette option supprime les volumes de données.
- Le mot de passe de création PostgreSQL n'est appliqué qu'à l'initialisation du volume; changer .env ne modifie pas le compte d'une base déjà créée.
- Les journaux Docker sont limités à trois fichiers de 10 Mo. L'historique SQL et le brut ne sont pas purgés automatiquement; surveillez l'espace et sauvegardez les volumes.

### Sans Docker, avec votre PostgreSQL existant

Installez requirements.txt dans un environnement Python, renseignez .env pour votre serveur, puis lancez `python -m mobiliteiq serve`. Gardez ce processus supervisé par votre gestionnaire de services. Ne lancez plus l'ancienne tâche planifiée en parallèle. La commande `run` reste disponible pour une collecte ponctuelle. Le modèle ML conserve son entraînement manuel; cette évolution automatise les ingestions, les agrégats et les indicateurs.

### Validation de cette livraison

Voir docs/VALIDATION_AUTOMATISATION.md. Une validation locale des tests n'est pas une preuve que les services distants sont disponibles ni que la collecte est déjà déployée chez vous.

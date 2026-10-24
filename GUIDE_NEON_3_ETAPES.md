# MobilitéIQ avec Neon — le projet complet en 3 étapes

**Un guide pour une équipe de cinq personnes, même sans grande expérience technique.**  
Version du 22 octobre 2026 · Travaux et météo chaque heure · Débit et réseau routier chaque jour.

## Avant de commencer : qui fait quoi ?

Votre projet fonctionne comme une chaîne de travail. **Python va chercher les informations, Neon les conserve, Power BI les présente.** GitHub permet aux cinq membres de travailler sur le code et lance les collectes automatiquement.

Vous utiliserez encore WSL et VS Code sur vos ordinateurs pour développer. La base réelle sera sur Internet chez Neon; vous n'installerez pas PostgreSQL comme serveur sur votre ordinateur. Quand GitHub exécutera la collecte, vos PC pourront être éteints.

<!--DIAGRAM-->

| Outil | Explication simple | Emplacement |
|---|---|---|
| WSL Ubuntu | L'environnement dans lequel vous lancez Python | Ordinateur de chaque membre |
| VS Code | L'éditeur pour lire et modifier le projet | Ordinateur de chaque membre, connecté à WSL |
| GitHub | Le dossier de code commun et son historique | Internet |
| GitHub Actions | L'exécutant qui lance Python aux heures prévues | Internet |
| Neon / PostgreSQL | Le classeur central des données | Internet |
| Power BI | Les tableaux, graphiques et cartes | Desktop sur Windows; publication en ligne selon la licence |

**Les trois étapes :** 1. Créer la base sur Neon et connecter le projet. 2. Mettre le code en commun et activer les collectes. 3. Construire et actualiser Power BI, puis valider le travail d'équipe.

Le guide fournit les actions à réaliser. Le code est préparé, mais aucun compte, dépôt GitHub, serveur Neon ou rapport Power BI n'a été créé pour votre équipe par cette livraison. Neon est ici une base PostgreSQL hébergée; ce parcours ne nécessite pas de lac de données.

## Étape 1 — Créer PostgreSQL sur Neon et connecter Python

### 1.1 Choisir le responsable du premier démarrage

Un membre crée l'organisation Neon et le dépôt GitHub. Il invite ensuite les quatre autres. Chacun conserve son propre compte; vous ne partagez pas un mot de passe de connexion au site.

Répartition possible : personne 1, base et accès; personne 2, collectes; personne 3, qualité et tests; personne 4, analyses; personne 5, rapport Power BI et coordination de la démonstration. Les responsabilités peuvent être échangées.

### 1.2 Créer le compte et le projet Neon

1. Ouvrez [neon.com](https://neon.com/) et choisissez **Sign up**.
2. Créez votre compte, par exemple avec votre compte GitHub.
3. Dans la console, créez ou sélectionnez une **organisation** destinée à votre groupe.
4. Dans les paramètres de l'organisation, cherchez **Members / Invitations** et invitez les quatre autres membres.
5. Créez un projet, par exemple `mobiliteiq-equipe5`.
6. Choisissez l'offre gratuite pour commencer. Vérifiez que l'écran ne vous fait pas souscrire une offre payante.
7. Choisissez une région proche de votre équipe et gardez la version PostgreSQL proposée si vous n'avez pas de contrainte particulière.
8. Repérez la branche principale. Selon la création du projet, elle peut s'appeler `main` ou `production`. Dans ce guide, « branche principale Neon » signifie celle qui héberge vos données réelles.

Les libellés de la console peuvent évoluer; les notions à retrouver sont projet, branche, bases, rôles et connexion. Les limites gratuites doivent être surveillées dans **Usage / Billing**. L'offre consultée annonce 1 Go de base par projet, 100 CU-heures mensuelles par projet et des membres illimités. Ce volume n'est pas garanti suffisant pour tout l'historique du projet. [Offre Neon](https://neon.com/pricing).

**Point de contrôle :** chaque membre invité peut accéder au projet avec son compte personnel.

### 1.3 Créer les bases PostgreSQL

Un **projet Neon** est votre espace d'hébergement. Une **base** est le classeur de données situé dans cet espace.

Dans la console Neon :

1. Sélectionnez votre projet et la branche principale.
2. Ouvrez **Databases**, parfois dans **Branches → votre branche → Roles & Databases**.
3. Cliquez **New database / Create database**.
4. Nommez la base exactement `mobiliteiq` et choisissez le rôle propriétaire proposé.
5. Créez aussi `mobiliteiq_demo` pour les données fictives utilisées pour apprendre.
6. Pour les tests manuels sur Neon, créez un **deuxième projet Neon**, par exemple `mobiliteiq-tests`, puis une base `mobiliteiq_test`. Vous éviterez ainsi de perturber le projet réel.

La base `neondb` créée automatiquement peut rester en place; ce programme attend les noms ci-dessus. Vous pouvez commencer seulement avec `mobiliteiq` et ajouter la démo plus tard. Les tests GitHub utiliseront leur propre PostgreSQL temporaire et ne nécessitent pas la base de test Neon.

| Base | Contenu | Utilisateur principal |
|---|---|---|
| mobiliteiq | Collectes réelles, historique, indicateurs | Automatisation et équipe |
| mobiliteiq_demo | Données synthétiques pour préparer les analyses | Équipe |
| mobiliteiq_test, projet séparé | Données jetables de tests | Responsable des tests |

Ne copiez pas la production sur une base de test en conservant des accès d'écriture à la production. Les tests effacent leurs tables dans `mobiliteiq_test`.

### 1.4 Obtenir l'adresse de connexion sécurisée

Dans Neon, cliquez **Connect** :

1. Sélectionnez la branche principale, la base `mobiliteiq` et le rôle propriétaire.
2. **Désactivez Connection pooling.** Le projet utilise un verrou qui nécessite une connexion directe.
3. Copiez l'URL PostgreSQL complète, de la forme suivante :

```text
postgresql://UTILISATEUR:MOT_DE_PASSE@HOTE_NEON/mobiliteiq?sslmode=require
```

L'URL réelle peut aussi contenir `channel_binding=require`; conservez les paramètres fournis. Ne copiez pas l'enveloppe `psql '...'` si elle apparaît : vous voulez seulement l'URL, sans guillemets. Le nom d'hôte direct ne contient pas `-pooler`.

Cette adresse inclut un mot de passe : conservez-la dans un gestionnaire de mots de passe et ne la publiez pas dans le code, une capture ou un message collectif non protégé. La connexion choisie ici sert à l'installation et à la collecte; l'accès Power BI en lecture seule sera créé à l'étape 3.

### 1.5 Ouvrir le projet dans WSL et VS Code

Sous Windows, installez WSL Ubuntu et VS Code avec l'extension **WSL** si ce n'est pas déjà fait. Dans PowerShell Windows, vérifiez :

```powershell
wsl --list --verbose
```

Si aucune distribution n'est installée, utilisez un PowerShell administrateur :

```powershell
wsl --install -d Ubuntu
```

Terminez la création de votre utilisateur Ubuntu. Dans **Ubuntu**, exécutez :

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git unzip
mkdir -p ~/MobiliteIQ-Lab
cd ~/MobiliteIQ-Lab
explorer.exe .
```

Copiez le nouveau ZIP `MobiliteIQ_Neon.zip` dans la fenêtre ouverte. Dans Ubuntu :

```bash
unzip MobiliteIQ_Neon.zip
cd MobiliteIQ_Neon
code .
```

Utilisez un dossier neuf si celui-ci existe déjà. Dans VS Code, vérifiez **WSL: Ubuntu** en bas de la fenêtre. Ouvrez **Terminal → New Terminal**. Toutes les commandes suivantes, sauf indication contraire, sont des commandes Ubuntu à saisir dans ce terminal.

### 1.6 Installer les dépendances et renseigner .env

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
code .env
```

Si vous avez déjà un `.env`, modifiez-le sans le remplacer. Dans ce fichier, remplacez la ligne d'exemple par votre vraie URL :

```ini
DATABASE_URL=postgresql://UTILISATEUR:MOT_DE_PASSE@HOTE_NEON/mobiliteiq?sslmode=require
```

Ne mettez pas de guillemets. Gardez les autres URL commentées jusqu'à la création de leurs bases. Après création, revenez dans **Connect** sur Neon pour sélectionner chaque base et recopiez son URL directe :

```ini
DATABASE_URL_DEMO=postgresql://UTILISATEUR:MOT_DE_PASSE@HOTE_NEON/mobiliteiq_demo?sslmode=require
DATABASE_URL_TEST=postgresql://UTILISATEUR:MOT_DE_PASSE@AUTRE_HOTE_NEON/mobiliteiq_test?sslmode=require
```

Le projet refuse une connexion de test pointant vers la base réelle et refuse de réutiliser automatiquement l'URL réelle quand l'URL de démo ou de test manque. Puis :

```bash
chmod 600 .env
python -m mobiliteiq check-db
```

Résultat attendu : connexion réussie à `mobiliteiq`, chiffrement TLS actif. Aucun serveur PostgreSQL local n'est nécessaire. Le premier réveil de la base peut prendre quelques instants.

### 1.7 Créer automatiquement les tables et vues

Créer une base vide dans Neon ne suffit pas : il faut maintenant créer ses tableaux de rangement.

```bash
python -m mobiliteiq init-db
```

Python lit `sql/schema.sql` et crée les tables `runs`, `observations`, `rejects`, `sector_hour`, ainsi que les tables d'analyse et les vues `bi`. Vous n'avez pas à recopier ce long SQL manuellement.

Dans **SQL Editor** de Neon, sélectionnez bien la base `mobiliteiq` puis exécutez :

```sql
SELECT current_database();
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN ('public', 'bi')
ORDER BY table_schema, table_name;
```

Vous devez voir `mobiliteiq` et les objets créés. Cette commande initialise les objets sans supprimer les données existantes.

### 1.8 Faire la première ingestion réelle

```bash
python -m mobiliteiq audit
code data/audit.json
python -m mobiliteiq run --force
```

L'audit montre les données reçues et les champs disponibles. La collecte `run --force` lit les quatre sources immédiatement. Ne relancez pas l'audit à chaque collecte automatique : le contrôle qualité est déjà intégré au programme.

Dans Neon SQL Editor, base `mobiliteiq` :

```sql
SELECT * FROM bi.etat_sources ORDER BY source;
SELECT source, count(*) AS nombre_elements
FROM bi.observations_courantes
GROUP BY source;
SELECT * FROM bi.ops_alertes;
```

Chaque source doit avoir une dernière tentative et, si elle fonctionne, une dernière réussite. Un lot travaux vide peut être normal dans le territoire choisi. Les autres sources doivent contenir des observations valides. Une alerte météo peut signaler que le producteur publie des observations anciennes malgré une collecte réussie.

**Comment la base est alimentée :** Python télécharge les réponses, vérifie identifiants, champs, dates, valeurs et géométries, puis enregistre un lot. Il conserve l'historique et prépare les regroupements par secteur et heure. Un lot de qualité insuffisante ne remplace pas le dernier lot valide.

**Fin de l'étape 1 :** vous voyez dans Neon des données arrivées depuis votre programme WSL. Si une ancienne version fonctionnait en local, elle n'a pas été migrée par ces commandes : sauvegardez son historique séparément avant d'envisager un transfert.

## Étape 2 — Travailler à cinq et automatiser avec GitHub

### 2.1 Créer le dépôt commun

Sur GitHub, créez un dépôt vide nommé par exemple `mobiliteiq-neon`, sans README initial. Pour le travail d'équipe, utilisez une organisation GitHub ou invitez les quatre autres personnes dans **Settings → Collaborators** du dépôt.

Dans le terminal WSL du premier membre :

```bash
git config --global user.name "Votre nom"
git config --global user.email "Votre adresse GitHub ou adresse privée GitHub"
git init -b main
git add .
git status
git diff --cached --stat
```

Vérifiez que `.env`, les données téléchargées, `.venv`, les modèles et les exports ne figurent pas dans les fichiers ajoutés. `.gitignore` les exclut. `.env.example` doit rester un exemple sans secret réel.

```bash
git commit -m "MobiliteIQ avec PostgreSQL Neon et collecte automatique"
git remote add origin https://github.com/VOTRE_COMPTE_OU_ORGANISATION/mobiliteiq-neon.git
git push -u origin main
```

Remplacez le nom du compte dans l'URL. Authentifiez-vous via une méthode GitHub prise en charge; ne placez pas de jeton dans l'URL. Si le dossier est déjà un dépôt, examinez `git status` et `git remote -v` au lieu de réinitialiser sa configuration.

### 2.2 Connecter les quatre autres membres

Une fois invités au dépôt, ils exécutent dans Ubuntu :

```bash
mkdir -p ~/MobiliteIQ-Lab
cd ~/MobiliteIQ-Lab
git clone https://github.com/VOTRE_COMPTE_OU_ORGANISATION/mobiliteiq-neon.git
cd mobiliteiq-neon
code .
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Chaque membre crée son propre `.env` si son rôle nécessite d'exécuter Python contre une base. L'accès à l'organisation Neon et l'accès SQL à la base sont deux choses différentes. Donnez l'accès d'écriture à la base réelle seulement aux personnes qui en ont besoin. Les autres peuvent travailler sur la démo ou en lecture seule dans Power BI.

Pour modifier le code, créez une branche par tâche, par exemple :

```bash
git switch -c ajout-page-qualite
# Modifier puis tester les fichiers.
git add .
git commit -m "Améliorer le suivi de qualité"
git push -u origin ajout-page-qualite
```

Sur GitHub, ouvrez une **Pull request** vers `main`, faites relire par un autre membre et attendez les tests avant fusion. Le workflow de tests inclus utilise un PostgreSQL temporaire sur GitHub : il ne touche pas à Neon.

### 2.3 Enregistrer la connexion dans GitHub Secrets

Un seul responsable effectue cette opération :

1. Ouvrez le dépôt GitHub.
2. **Settings → Secrets and variables → Actions**.
3. Cliquez **New repository secret**.
4. Nom exact : `NEON_DATABASE_URL`.
5. Valeur : l'URL directe complète de la base réelle `mobiliteiq`.
6. Enregistrez.

GitHub fournit cette valeur au programme au moment de l'exécution. L'URL n'est pas écrite dans le fichier du workflow. N'ajoutez pas `.env` au dépôt. Toute personne autorisée à modifier des workflows peut modifier le code qui reçoit les secrets : réservez les accès au dépôt aux cinq membres de confiance et relisez les changements.

### 2.4 Lancer et vérifier la collecte automatique

Le fichier fourni est `.github/workflows/ingestion-neon.yml`. Il est séparé du workflow de tests.

1. Vérifiez que le fichier est bien présent sur la branche `main` de GitHub.
2. Ouvrez **Actions → Collecte Neon**.
3. Cliquez **Run workflow**.
4. Pour le premier essai, cochez **Recollecter les quatre sources immédiatement**.
5. Lancez et attendez le résultat.
6. Ouvrez l'exécution : les étapes vérifient la connexion, collectent et archivent les fichiers bruts.
7. Revenez dans Neon et consultez `bi.etat_sources` pour confirmer les dates.

Un résultat rouge nécessite de lire l'étape en échec : secret absent, connexion refusée, problème de source ou qualité insuffisante. Les autres sources peuvent tout de même avoir réussi. Les dernières données valides restent disponibles.

### 2.5 Comprendre le calendrier

GitHub déclenche le workflow chaque heure à la minute **17**, selon l'heure UTC. Python décide alors quelles sources sont à actualiser.

| Source | Règle dans cette version |
|---|---|
| Travaux | Une collecte réussie par créneau horaire UTC |
| Météo | Une collecte réussie par créneau horaire UTC |
| Débit | Une collecte réussie par jour UTC |
| RTSS | Une collecte réussie par jour UTC |

Un créneau évite qu'une collecte commencée en retard empêche celle de l'heure suivante. La journée UTC ne correspond pas exactement à la journée locale au Québec. Le workflow ne garantit pas un déclenchement à la seconde; GitHub peut le retarder ou manquer un démarrage. Les données intermédiaires non observées ne sont pas reconstruites.

**Après échec :** les appels HTTP possèdent des reprises courtes intégrées. Si toute la collecte échoue, GitHub réessaiera à sa prochaine exécution horaire; vous pouvez aussi relancer manuellement. Le délai de cinq minutes configuré dans le code n'installe pas un déclenchement GitHub toutes les cinq minutes. Ne lancez pas `serve` en permanence sur GitHub : le workflow utilise `run`, puis se termine.

Les planifications publiques peuvent être désactivées après 60 jours sans activité du dépôt. Contrôlez régulièrement l'onglet Actions. Sur dépôt privé, les minutes disponibles dépendent du forfait; l'installation des bibliothèques et le traitement les consomment. [Planification GitHub](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule), [quotas Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

### 2.6 Où restent les données et fichiers ?

| Élément | Emplacement et durée |
|---|---|
| Données acceptées et historique | PostgreSQL Neon, jusqu'à suppression explicite ou évolution de votre offre |
| Statuts, rejets et indicateurs | PostgreSQL Neon |
| Fichiers bruts des collectes GitHub | Artifacts de chaque exécution, conservation demandée de 1 jour |
| Fichiers bruts des essais WSL | Dossier `data/raw` du poste |
| Code et documentation | GitHub |

Pour télécharger le brut : **Actions → une exécution → Artifacts → brut-…**. La colonne `raw_path` des runs indique le chemin du dossier à retrouver dans l'archive. Les artifacts dépendent des quotas de stockage GitHub; téléchargez et archivez ce qui doit être conservé avant expiration. Ce mécanisme temporaire n'est pas un lac permanent ni une sauvegarde de la base. Pour un stockage brut durable, ajoutez plus tard un stockage objet cloud.

### 2.7 Tester sans toucher aux données réelles

Dans WSL :

```bash
python -m pytest tests/test_core.py tests/test_scheduler.py tests/test_cloud.py -q
```

Pour les tests d'intégration, renseignez `DATABASE_URL_TEST` vers la base `mobiliteiq_test` dans le projet de test, puis :

```bash
RUN_PG_TESTS=1 python -m pytest -q
```

Ils effacent les tables de `mobiliteiq_test`. Le programme vérifie le nom exact de la base et refuse tout repli vers `DATABASE_URL`. Le workflow CI exécute également les tests PostgreSQL dans une base temporaire, sans utiliser les secrets Neon.

**Fin de l'étape 2 :** une exécution manuelle GitHub a réussi, puis une exécution planifiée a ajouté un lot dans Neon. Cela confirme que la collecte fonctionne sans votre PC.

## Étape 3 — Alimenter Power BI, analyser et valider le projet

### 3.1 Créer un accès Power BI en lecture seule

Utilisez un compte SQL distinct pour éviter qu'un outil de consultation ait les droits du propriétaire. Dans le **SQL Editor Neon**, base `mobiliteiq`, sous le propriétaire, exécutez une seule fois :

```sql
CREATE ROLE powerbi_reader LOGIN PASSWORD 'REMPLACER_PAR_UN_MOT_DE_PASSE_DISTINCT';
```

Choisissez un mot de passe fort sans apostrophe pour cet exemple. Saisissez la valeur uniquement dans votre console; ne l'inscrivez pas dans les fichiers partagés. Si le rôle existe déjà, ne relancez pas sa création. Un rôle créé directement dans SQL peut ne pas apparaître comme un rôle géré par l'interface Neon.

Ouvrez `sql/powerbi_reader.sql` dans VS Code, puis copiez et exécutez son contenu dans le même SQL Editor :

```sql
GRANT CONNECT ON DATABASE mobiliteiq TO powerbi_reader;
GRANT USAGE ON SCHEMA bi TO powerbi_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA bi TO powerbi_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA bi
GRANT SELECT ON TABLES TO powerbi_reader;
```

Ce compte lit les vues `bi`; il ne reçoit pas le droit de modifier les observations. Pour des accès individuels, répétez le principe avec un rôle distinct par membre et les mêmes droits de lecture. Conservez le compte propriétaire pour l'installation et la collecte.

### 3.2 Connecter Power BI Desktop à Neon

Dans **Connect** sur Neon, repérez le nom d'hôte direct de votre base. Pour Power BI, il faut les éléments séparés, pas l'URL complète.

| Champ Power BI | Valeur |
|---|---|
| Serveur | `HOTE_NEON:5432`, sans `https://`, chemin ou paramètres |
| Base | `mobiliteiq` |
| Authentification | Database |
| Utilisateur | `powerbi_reader` |
| Mot de passe | Celui créé pour ce rôle |

Dans Power BI Desktop Windows :

1. **Home → Get data → More → Database → PostgreSQL database**.
2. Renseignez serveur et base.
3. Choisissez **Import** pour commencer.
4. Renseignez l'utilisateur et le mot de passe; conservez la connexion chiffrée.
5. Dans **Navigator**, sélectionnez les vues du schéma `bi` listées ci-dessous.
6. Cliquez **Transform Data**, vérifiez les types puis **Close & Apply**.

Si une erreur de certificat ou de chiffrement apparaît, examinez l'hôte et votre version de Power BI; ne désactivez pas la sécurité pour la masquer. [Connecteur PostgreSQL Microsoft](https://learn.microsoft.com/en-us/power-query/connectors/postgresql).

### 3.3 Choisir les vues et construire les relations

| Vue | Ce qu'elle fournit |
|---|---|
| info_projet | Nom de la base et réel/démonstration |
| etat_sources | Dernières tentatives, réussites et erreurs des quatre sources |
| fact_entraves | Dernier état des travaux collectés |
| historique_entraves | Première et dernière présence observées |
| fact_secteur_heure | Nombre d'entraves et contexte par secteur et heure |
| dim_secteur, dim_date | Listes pour les filtres |
| ops_alertes | Indicateurs de fraîcheur ou qualité en alerte |

Les secteurs sont une grille pédagogique, pas des quartiers officiels. Le DJMA est une référence de débit moyen et non le trafic en direct. Les agrégats restent liés à l'instantané travaux; une météo arrivée ensuite se rattache au prochain instantané travaux.

Dans Power Query, vérifiez : identifiants et secteurs en texte; coordonnées et scores en décimal; nombres d'entraves en entier; `anomaly` en vrai/faux; `date_key` en date. Gardez les libellés UTC sur les dates de collecte; `heure_locale` est déjà calculée pour America/Toronto.

Dans **Model view**, reliez la dimension vers chaque table, en **One to many**, filtre à sens unique :

| Depuis | Vers |
|---|---|
| dim_secteur[sector] | fact_entraves[sector] |
| dim_secteur[sector] | historique_entraves[sector] |
| dim_secteur[sector] | fact_secteur_heure[sector] |
| dim_date[date_key] | fact_secteur_heure[date_key] |
| dim_date[date_key] | historique_entraves[date_key] |

Ne reliez pas directement les tables de faits entre elles. Le filtre de date sur l'historique correspond à la première observation; il ne représente pas « tous les travaux présents ce jour-là ». La table des travaux courants n'est pas filtrée par date dans ce modèle.

### 3.4 Ajouter les mesures et trois pages

Ouvrez `powerbi/Measures.dax`. Dans Power BI, choisissez **Modeling → New measure** et copiez une mesure à la fois en conservant les noms des tables. Adaptez les virgules en points-virgules si votre configuration régionale le demande.

| Page | Visuels proposés |
|---|---|
| Situation actuelle | Cartes Entraves présentes et Dernière collecte UTC; liste des travaux; filtre secteur; carte géographique si autorisée |
| Historique et analyses | Courbe par heure locale; tableau des secteurs; filtres date et secteur; anomalies lorsqu'un modèle existe |
| Qualité des données | Tableau etat_sources; carte Alertes de qualité; détail ops_alertes |

Pour la carte, utilisez latitude et longitude de `fact_entraves` et définissez leurs catégories de données. Gardez la liste si la cartographie est désactivée dans votre établissement.

Enregistrez `MobiliteIQ_Neon.pbix`. La livraison ne fournit pas de PBIX préfabriqué. Le fichier est exclu de Git par défaut; un membre coordonne le rapport final pour éviter cinq copies divergentes.

### 3.5 Vérifier que le rapport correspond à Neon

Dans SQL Editor Neon :

```sql
SELECT count(DISTINCT event_id) FROM bi.fact_entraves;
SELECT count(*) FROM bi.ops_alertes;
SELECT max(collecte_utc) FROM bi.fact_entraves;
```

Dans Power BI, retirez les filtres puis cliquez **Home → Refresh**. Comparez les cartes avec les résultats SQL. Si aucun travail n'est présent, la date maximale de cette table peut être vide : utilisez `etat_sources` pour vérifier que la collecte travaux a bien réussi.

### 3.6 Comprendre les deux actualisations

**Première actualisation :** GitHub lance Python et met à jour Neon.  
**Deuxième actualisation :** Power BI relit Neon et met à jour les visuels.

Une base à jour ne rafraîchit pas automatiquement une copie Import déjà ouverte dans Desktop. Dans Desktop, utilisez **Refresh**. Pour automatiser le rapport :

1. Vérifiez avec votre cégep les licences Power BI et l'espace partagé accessibles aux cinq membres.
2. Publiez le rapport dans cet espace depuis Desktop.
3. Dans Power BI Service, configurez une **connexion cloud PostgreSQL** avec l'hôte Neon, la base et le compte de lecture.
4. Dans les paramètres du modèle sémantique, associez cette connexion et vérifiez les identifiants.
5. Lancez **Refresh now**, vérifiez l'historique puis activez l'actualisation planifiée selon les créneaux disponibles.

Le connecteur PostgreSQL prend en charge les connexions cloud. Une passerelle locale n'est normalement pas nécessaire si cette connexion cloud peut atteindre l'hôte public Neon; si votre organisation impose un autre chemin réseau, il faudra adapter la configuration et le tester. Ne supposez pas qu'une connexion Desktop réussie prouve que la connexion Service est prête.

Une actualisation horaire Import dépend de la licence : la documentation consultée indique jusqu'à 8 actualisations planifiées par jour en Pro et jusqu'à 48 pour les offres PPU/Premium/capacités concernées. L'ingestion horaire peut continuer même si le rapport est actualisé moins souvent. [Configuration et limites Power BI](https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-scheduled-refresh).

### 3.7 Préparer la démonstration et le modèle

Si l'historique réel est encore trop court, configurez `DATABASE_URL_DEMO`, puis lancez :

```bash
python -m mobiliteiq --db mobiliteiq_demo init-db
python -m mobiliteiq --db mobiliteiq_demo demo
python -m mobiliteiq --db mobiliteiq_demo eda
python -m mobiliteiq --db mobiliteiq_demo train
python -m mobiliteiq --db mobiliteiq_demo export
```

La démo crée 30 jours synthétiques et refuse de se réinitialiser si elle est déjà remplie. Son rapport doit porter la mention **DONNÉES SYNTHÉTIQUES**. Pour explorer cette base dans Power BI, utilisez un accès propriétaire de démo ou créez un rôle lecteur avec les droits adaptés à `mobiliteiq_demo`; les droits sur la base réelle ne sont pas automatiquement ceux de la démo.

Pour les données réelles, après au moins dix jours et quarante heures distinctes :

```bash
python -m mobiliteiq eda
python -m mobiliteiq train
python -m mobiliteiq score
```

Ces commandes restent manuelles. Le modèle est conservé dans `models/` sur le poste qui l'entraîne; `score` doit retrouver ce fichier au chemin enregistré. Désignez un responsable et sauvegardez ce dossier. Le workflow GitHub fourni ne réentraîne pas et ne recalcule pas automatiquement les scores. La collecte et les indicateurs opérationnels fonctionnent sans modèle. Une anomalie statistique est un signal à examiner, pas une preuve de congestion ou de danger.

### 3.8 Valider et entretenir le projet à cinq

| Vérification finale | Preuve |
|---|---|
| Accès de l'équipe | Cinq comptes personnels invités |
| Base en ligne | Connexion réussie et tables visibles dans Neon |
| Quatre ingestions | Réussites et horodatages dans etat_sources |
| Collecte sans PC | Exécution planifiée GitHub, puis nouvelles données dans Neon |
| Qualité | Erreurs visibles et dernier lot valide conservé |
| Code testé | CI verte sur le dernier commit fusionné |
| Rapport | Valeurs réconciliées avec SQL |
| Actualisation | Historique de refresh Power BI, ou actualisation Desktop démontrée |

Chaque semaine, consultez l'usage Neon et le stockage GitHub. La météo est téléchargée sur une fenêtre glissante de deux jours et historisée par collecte : les répétitions augmentent le volume. Aucune purge automatique n'est activée. Exportez et définissez une politique de conservation avant d'atteindre les quotas. Ne supprimez pas l'historique pour gagner de la place sans accord de l'équipe et sauvegarde.

Pour un export de consultation : `python -m mobiliteiq export`. Ce sont des CSV des vues, pas une sauvegarde complète. Pour une sauvegarde PostgreSQL, utilisez un client `pg_dump` compatible avec la version du serveur et la connexion directe Neon. Les restaurations se testent dans une base distincte. Les données, les fichiers de modèle et les archives brutes demandent des sauvegardes adaptées.

Pour arrêter les collectes : **GitHub → Actions → Collecte Neon → menu → Disable workflow**. Cela conserve la base. Pour appliquer une correction, fusionnez une Pull request testée vers `main` et lancez une collecte manuelle de contrôle.

### Dépannage simple

| Message ou symptôme | Vérification |
|---|---|
| Configurer NEON_DATABASE_URL | Créer le secret dans les paramètres du dépôt |
| Connexion doit cibler mobiliteiq | Dans Neon Connect, choisir la bonne base puis recopier l'URL |
| Utiliser une connexion directe | Désactiver Connection pooling et supprimer l'ancienne URL mutualisée |
| Connexion cloud exige sslmode | Recopier tous les paramètres sécurisés de l'URL Neon |
| DATABASE_URL_DEMO ou TEST manquante | Renseigner l'URL de cette base, jamais celle de la production |
| Workflow rouge | Ouvrir l'étape fautive et consulter les statuts dans Neon |
| Pas de nouvelle exécution | Vérifier main, activation du workflow, calendrier, quotas et activité du dépôt |
| Tables Power BI vides | Vérifier base, rôle, droits, filtres et actualisation |
| Rapport Service ancien | Vérifier connexion cloud et historique de refresh séparément des collectes |

Références officielles : [Créer des bases Neon](https://neon.com/docs/manage/databases), [organisations Neon](https://neon.com/docs/manage/organizations), [connexions mutualisées et limites](https://neon.com/docs/connect/connection-pooling), [offre Neon](https://neon.com/pricing), [GitHub Actions planifié](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule), [PostgreSQL dans Power BI](https://learn.microsoft.com/en-us/power-query/connectors/postgresql).

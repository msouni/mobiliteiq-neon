# MobilitéIQ — reproduire le projet de bout en bout en 3 étapes

**WSL Ubuntu · VS Code · PostgreSQL · GitHub · Power BI**  
Guide du 22 octobre 2026 — version avec quatre ingestions automatiques.

Ce parcours utilise Python et PostgreSQL directement dans WSL. Docker reste une option du projet, mais n'est pas nécessaire pour suivre ce guide. Les commandes Bash se saisissent dans Ubuntu ou le terminal WSL de VS Code; les commandes PowerShell sont signalées. Les instructions décrivent les opérations à effectuer sur votre poste : elles ne signifient pas que la base, GitHub ou Power BI sont déjà configurés.

| Grande étape | Résultat |
|---|---|
| 1. Installer et collecter | Projet ouvert dans VS Code/WSL, PostgreSQL prêt, quatre sources collectées |
| 2. Analyser et visualiser | Analyse, modèle de démonstration et rapport Power BI |
| 3. Tester et automatiser | Tests, dépôt GitHub et service permanent dans WSL |

**Circuit des données :** sources publiques → collecteurs Python → contrôle qualité et archives brutes → PostgreSQL → vues `bi` → Power BI. GitHub conserve le code et teste les modifications.

| Source | Fréquence après réussite | Nouvelle tentative après échec |
|---|---|---|
| Travaux routiers | 60 minutes | 5 minutes |
| Météo | 60 minutes | 5 minutes |
| Débit de circulation | 24 heures | 5 minutes |
| Réseau routier RTSS | 24 heures | 5 minutes |

La boucle Python contrôle les échéances toutes les minutes après chaque cycle. Ce sont des intervalles de collecte, pas une garantie de nouvelles publications chez les producteurs. Le périmètre configuré est la région de Québec.

## Étape 1 — Préparer WSL, ouvrir le projet et collecter

### 1.1 Vérifier Windows et WSL

Dans **PowerShell Windows** :

```powershell
wsl --list --verbose
wsl --version
```

Repérez le nom exact de la distribution, par exemple `Ubuntu`. Elle doit utiliser WSL 2. Si WSL n'est pas installé, ouvrez PowerShell en administrateur et lancez :

```powershell
wsl --install -d Ubuntu
```

Redémarrez si demandé, puis ouvrez Ubuntu et terminez la création de votre utilisateur Linux. Si Ubuntu est déjà installé, conservez cette installation. Installez VS Code sous Windows et son extension **WSL** publiée par Microsoft. Installez également Power BI Desktop sous Windows et préparez votre compte GitHub.

### 1.2 Placer le projet dans le système de fichiers Linux

Téléchargez l'archive `MobiliteIQ_Automatise.zip` jointe à cette livraison. Dans **Ubuntu** :

```bash
mkdir -p ~/MobiliteIQ-Lab
cd ~/MobiliteIQ-Lab
explorer.exe .
```

Copiez le ZIP dans la fenêtre ouverte. Revenez dans Ubuntu :

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-client unzip git
unzip MobiliteIQ_Automatise.zip
cd MobiliteIQ_Automatise
code .
```

Si le dossier existe déjà, extrayez dans un nouveau dossier pour conserver votre travail. Le chemin attendu est `~/MobiliteIQ-Lab/MobiliteIQ_Automatise`. Les commandes suivantes supposent ce chemin.

Dans VS Code, le coin inférieur gauche doit indiquer **WSL: Ubuntu**. Ouvrez **Terminal → New Terminal**, puis :

```bash
pwd
python3 --version
git --version
```

**Point de contrôle :** le terminal affiche un chemin Linux sous `/home/…`, et le dossier contient `mobiliteiq`, `config`, `sql`, `tests` et `.github`.

### 1.3 Activer systemd et PostgreSQL

Dans Ubuntu :

```bash
ps -p 1 -o comm=
```

Si le résultat est `systemd`, poursuivez. Sinon, ouvrez :

```bash
sudo nano /etc/wsl.conf
```

Ajoutez ou adaptez la section suivante en conservant les autres paramètres du fichier :

```ini
[boot]
systemd=true
```

Enregistrez avec Ctrl+O, Entrée, puis Ctrl+X. Fermez votre travail WSL. Dans **PowerShell**, la commande suivante arrête toutes les distributions WSL :

```powershell
wsl --shutdown
```

Rouvrez Ubuntu, puis le projet avec `code .` depuis son dossier. Dans Ubuntu :

```bash
sudo systemctl enable --now postgresql
pg_isready -h localhost -p 5432
sudo -u postgres psql -c '\du'
sudo -u postgres psql -c '\l'
```

Le service doit accepter les connexions. Si systemd reste indisponible, vérifiez la version de WSL et sa configuration avant l'étape 3. La procédure suit la [documentation Microsoft sur systemd dans WSL](https://learn.microsoft.com/en-us/windows/wsl/systemd).

### 1.4 Créer le compte et les trois bases

Exécutez la création uniquement si le compte et les bases ne figurent pas dans les listes précédentes :

```bash
sudo -u postgres createuser --login --pwprompt mobiliteiq
sudo -u postgres createdb --owner=mobiliteiq mobiliteiq
sudo -u postgres createdb --owner=mobiliteiq mobiliteiq_demo
sudo -u postgres createdb --owner=mobiliteiq mobiliteiq_test
```

Choisissez un mot de passe local. La saisie du mot de passe peut rester invisible.

| Base | Usage |
|---|---|
| mobiliteiq | Données réelles et historique |
| mobiliteiq_demo | Données synthétiques pour apprendre et construire le rapport |
| mobiliteiq_test | Base jetable : les tests y effacent leurs tables |

Vérifiez :

```bash
psql -h localhost -U mobiliteiq -d mobiliteiq -W -c 'SELECT current_database(), current_user;'
```

Le résultat doit indiquer `mobiliteiq` pour la base et l'utilisateur.

### 1.5 Installer Python et renseigner la configuration

Dans le terminal WSL de VS Code, à la racine du projet :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
code .env
```

Ne recopiez pas `.env.example` sur un `.env` déjà renseigné. Dans `.env`, utilisez :

```ini
PGHOST=localhost
PGPORT=5432
PGUSER=mobiliteiq
PGPASSWORD=REMPLACER_PAR_VOTRE_MOT_DE_PASSE
PGDATABASE=mobiliteiq
```

Remplacez le mot de passe, sans ajouter de guillemets. Le programme lit ce fichier; il n'est pas nécessaire de l'exécuter comme un script. Puis :

```bash
chmod 600 .env
python -m mobiliteiq init-db
python -m mobiliteiq --db mobiliteiq_demo init-db
python -m mobiliteiq --db mobiliteiq_test init-db
python -m pytest tests/test_core.py tests/test_scheduler.py -q
```

**Point de contrôle :** les tables sont prêtes et les tests unitaires passent. Dans chaque nouveau terminal, revenez dans le projet et réactivez `.venv`.

### 1.6 Examiner les sources et lancer la première collecte

```bash
python -m mobiliteiq audit
code data/audit.json
code config/sources.json
```

L'audit télécharge les données et montre les champs disponibles; il ne remplit pas les tables analytiques. Vérifiez les quatre sections : `travaux`, `debit`, `rtss`, `meteo`. Une erreur de service doit être examinée avant de poursuivre.

La configuration livrée utilise `validation_mode: automatic`. Ne remplacez pas les champs au hasard et ne passez pas les anciens indicateurs `validated` à `true` pour contourner une erreur. Chaque lot est contrôlé au moment de son ingestion. Les dates, coordonnées, identifiants et champs attendus sont vérifiés. Plus de 10 % de rejets bloque la publication; les lots partiellement valides sous ce seuil peuvent publier leurs lignes acceptées. Une source vide n'est acceptée que pour les travaux.

Lancez la collecte réelle :

```bash
python -m mobiliteiq run --force
psql -h localhost -U mobiliteiq -d mobiliteiq -W -c 'SELECT * FROM bi.etat_sources;'
psql -h localhost -U mobiliteiq -d mobiliteiq -W -c 'SELECT source,count(*) FROM bi.observations_courantes GROUP BY source;'
```

Les quatre tentatives doivent être visibles. Cherchez une réussite pour chacune; des travaux absents du territoire peuvent produire un lot réussi vide. Une collecte échouée garde le dernier lot valide. Les archives sont dans `data/raw`, les rejets dans `bi.ops_rejets` et les erreurs dans `bi.ops_ingestions`.

**Fin de l'étape 1 :** votre installation lit les quatre sources et écrit dans PostgreSQL. Conservez une capture de l'état des sources, sans afficher `.env`.

## Étape 2 — Analyser les données et construire Power BI

### 2.1 Comprendre les vues disponibles

| Vue PostgreSQL | Utilité |
|---|---|
| bi.info_projet | Identifier la base et le mode réel ou démo |
| bi.etat_sources | Dernière tentative, dernière réussite et erreurs des quatre sources |
| bi.observations_courantes | Dernier lot valide de chaque source |
| bi.fact_entraves | Travaux présents dans le dernier extrait réussi |
| bi.historique_entraves | Première et dernière présence observées |
| bi.fact_secteur_heure | Agrégats horaires et scores lorsqu'ils existent |
| bi.dim_date / bi.dim_secteur | Dimensions pour les filtres |
| bi.ops_alertes | Indicateurs actuellement en alerte |

Les secteurs sont une grille pédagogique de 0,1 degré, pas des quartiers administratifs. Le débit est un DJMA de référence, pas une mesure de trafic en direct. Les agrégats sont ancrés sur l'instantané travaux : une nouvelle météo ne s'y rattache qu'au prochain instantané travaux.

### 2.2 Préparer une démonstration sans attendre l'historique réel

Dans WSL, environnement Python actif :

```bash
python -m mobiliteiq --db mobiliteiq_demo demo
python -m mobiliteiq --db mobiliteiq_demo eda
python -m mobiliteiq --db mobiliteiq_demo train
python -m mobiliteiq --db mobiliteiq_demo export
```

La commande `demo` crée 30 jours synthétiques et refuse de réinitialiser une démo déjà remplie. Dans ce cas, continuez avec `eda`, `train` ou `export`. N'exécutez jamais `demo` dans la base réelle.

Les résultats sont dans `exports/mobiliteiq_demo` : statistiques, valeurs manquantes, corrélations et exports des vues. Le modèle est enregistré dans `models/mobiliteiq_demo`. L'entraînement calcule aussi les premiers scores.

Pour les vraies données, lorsque suffisamment d'historique existe :

```bash
python -m mobiliteiq eda
python -m mobiliteiq train
python -m mobiliteiq score
```

L'entraînement exige au moins 10 jours d'étendue temporelle et 40 heures distinctes, avec des variables exploitables. Une anomalie Isolation Forest signale une situation inhabituelle; elle ne prouve ni congestion ni danger. Il n'existe pas de précision/rappel terrain sans étiquettes validées.

Les ingestions et agrégats sont automatiques à l'étape 3. L'entraînement et le recalcul des scores restent manuels dans cette version : après de nouvelles collectes, relancez `score` si vous voulez des scores à jour. Les tableaux de bord opérationnels peuvent fonctionner sans modèle.

### 2.3 Vérifier l'accès depuis Windows

Dans **PowerShell Windows** :

```powershell
Test-NetConnection localhost -Port 5432
```

`TcpTestSucceeded` doit être vrai. En cas d'échec, vérifiez d'abord `pg_isready` dans WSL et assurez-vous que le serveur démarre. Si un autre PostgreSQL Windows utilise déjà 5432, identifiez le bon serveur et utilisez un port distinct cohérent dans PostgreSQL, `.env`, Power BI et les commandes. N'ouvrez pas PostgreSQL à Internet pour contourner le problème.

### 2.4 Connecter Power BI Desktop

Dans Power BI Desktop sous Windows :

1. **Home → Get data → More → Database → PostgreSQL database**.
2. Serveur : `localhost:5432`.
3. Base : `mobiliteiq_demo` pour construire la démonstration, ou `mobiliteiq` pour les données réelles.
4. Choisissez **Import** pour commencer.
5. Authentification **Database** : utilisateur `mobiliteiq`, mot de passe de `.env`.
6. Dans **Navigator**, sélectionnez les vues indiquées ci-dessous, puis **Transform Data**.

Chargez `info_projet`, `etat_sources`, `fact_entraves`, `historique_entraves`, `fact_secteur_heure`, `dim_date`, `dim_secteur` et `ops_alertes` du schéma `bi`. Vous pouvez laisser `observations_courantes` en SQL : sa colonne JSON est destinée au détail technique.

Le [connecteur PostgreSQL officiel](https://learn.microsoft.com/power-query/connectors/postgresql) décrit les options et prérequis selon votre version de Power BI.

### 2.5 Vérifier les types et les relations

Dans Power Query :

- `event_id`, `sector`, `axe` : texte.
- `latitude`, `longitude`, `score` et les valeurs météo : nombres décimaux.
- `n_presentes` : entier.
- `anomaly` : vrai/faux.
- `date_key` : date.
- Les heures UTC : date/heure avec fuseau si disponible; conservez des libellés UTC explicites. `heure_locale` est déjà calculée pour America/Toronto.

Cliquez **Close & Apply**. Dans **Model view**, créez les relations suivantes, de la dimension vers la table de faits, cardinalité **One to many**, filtre à sens unique :

| Dimension | Table de faits |
|---|---|
| dim_secteur[sector] | fact_entraves[sector] |
| dim_secteur[sector] | historique_entraves[sector] |
| dim_secteur[sector] | fact_secteur_heure[sector] |
| dim_date[date_key] | fact_secteur_heure[date_key] |
| dim_date[date_key] | historique_entraves[date_key] |

Évitez les relations automatiques supplémentaires entre les tables de faits. Le filtre de date de l'historique correspond à la première observation; il ne signifie pas « présent à toute date sélectionnée ». Les travaux courants ne sont pas filtrés par date avec ce modèle.

### 2.6 Ajouter les mesures et les pages

Ouvrez `powerbi/Measures.dax` dans VS Code. Dans Power BI, utilisez **Modeling → New measure** et copiez une mesure à la fois. Conservez les noms de tables attendus dans le fichier. Si votre configuration utilise des points-virgules, adaptez les séparateurs d'arguments.

Créez trois pages :

| Page | Visuels à ajouter |
|---|---|
| Vue opérationnelle | Cartes Entraves présentes, Dernière collecte UTC et Alertes de qualité; tableau des travaux avec axe et secteur; filtre secteur |
| Historique et anomalies | Courbe par heure locale du nombre d'entraves; tableau secteur, heure, score, anomalie et explication; filtres date et secteur |
| Qualité des sources | Tableau etat_sources avec source, statut, dernière réussite, âge et erreur; tableau ops_alertes |

Pour une carte géographique, définissez les catégories de données latitude et longitude, puis placez les coordonnées de `fact_entraves` dans un visuel cartographique autorisé par votre organisation. Conservez le tableau si les cartes sont désactivées. Sur la démonstration, ajoutez un titre visible **DONNÉES SYNTHÉTIQUES**.

Enregistrez le fichier sous `MobiliteIQ_Demo.pbix` ou `MobiliteIQ_Reel.pbix`. Pour passer de la démo au réel, faites une copie du PBIX et modifiez la base dans **Transform data → Data source settings → Change Source**, puis actualisez. Les scores peuvent rester vides tant que le modèle réel n'est pas entraîné.

### 2.7 Vérifier les chiffres

Dans WSL :

```bash
psql -h localhost -U mobiliteiq -d mobiliteiq_demo -W -c 'SELECT count(DISTINCT event_id) FROM bi.fact_entraves;'
psql -h localhost -U mobiliteiq -d mobiliteiq_demo -W -c 'SELECT count(*) FROM bi.ops_alertes;'
```

Comparez avec les cartes Power BI, filtres retirés, après **Home → Refresh**. Changez la base en `mobiliteiq` pour vérifier le rapport réel. Les alertes d'une démo peuvent refléter ses données statiques : ne les présentez pas comme un état opérationnel réel.

**Fin de l'étape 2 :** le rapport est enregistré, les chiffres correspondent à SQL et la distinction réel/démo est visible.

## Étape 3 — Tester, publier sur GitHub et automatiser

### 3.1 Exécuter les tests complets

Dans WSL, à la racine du projet, `.venv` actif :

```bash
RUN_PG_TESTS=1 python -m pytest -q
python -m compileall -q mobiliteiq
```

Les tests utilisent exclusivement `mobiliteiq_test` et en effacent les tables de travail. `.env` fournit l'accès au serveur. Ne changez pas leur cible pour utiliser votre base réelle. Si des tests PostgreSQL sont ignorés malgré `RUN_PG_TESTS=1`, examinez la configuration avant de considérer la validation complète.

La livraison a été vérifiée localement avec 12 tests réussis et 5 tests PostgreSQL ignorés faute de serveur disponible. Vous devez exécuter ces derniers dans votre installation; ce guide ne prétend pas qu'ils y sont déjà réussis.

### 3.2 Publier le code sur GitHub

Créez sur GitHub un dépôt vide nommé par exemple `mobiliteiq`, sans README initial. Dans WSL, configurez votre identité Git si nécessaire :

```bash
git config --global user.name "Votre nom"
git config --global user.email "Votre adresse GitHub ou adresse privée GitHub"
```

Vérifiez si le dossier est déjà un dépôt avec `git status`. Pour un dossier qui n'en est pas encore un :

```bash
git init -b main
git add .
git diff --cached --stat
git status
```

Vérifiez que `.env`, `.venv`, les données, modèles et exports sont exclus. `.gitignore` exclut également les PBIX; le rapport reste local. Pour partager un PBIX, choisissez explicitement un emplacement adapté après contrôle de son contenu.

```bash
git commit -m "MobiliteIQ : quatre ingestions automatiques et guide complet"
git remote add origin https://github.com/VOTRE_COMPTE/mobiliteiq.git
git push -u origin main
```

Remplacez `VOTRE_COMPTE` avant d'exécuter. Si `origin` existe déjà, vérifiez-le avec `git remote -v` au lieu d'en ajouter un autre. Authentifiez-vous avec une méthode prise en charge par GitHub; ne mettez pas de jeton dans l'URL ou dans les fichiers du projet.

Dans GitHub, ouvrez **Actions**. Le workflow `.github/workflows/ci.yml` installe Python, démarre un PostgreSQL temporaire et exécute les tests. Attendez la réussite sur le commit publié. Ce PostgreSQL de test n'est pas votre base réelle et GitHub n'effectue pas vos ingestions locales.

Pour les modifications suivantes :

```bash
git switch -c dev
# Modifier et tester les fichiers dans VS Code.
git add .
git commit -m "Description de la modification"
git push -u origin dev
```

Sur GitHub, créez une **Pull request** de `dev` vers `main`, attendez les tests puis fusionnez. Revenez ensuite sur `main` et synchronisez avec `git pull --ff-only`.

### 3.3 Essayer le service automatique au premier plan

Dans WSL :

```bash
python -m mobiliteiq serve
```

Le service consulte les dates enregistrées dans PostgreSQL. Si vous venez de lancer `run`, il attend les prochaines échéances; il ne doit pas nécessairement retélécharger immédiatement. Les échecs sont réessayés après cinq minutes. La météo et les travaux reviennent chaque heure, le débit et RTSS chaque jour.

Dans un second terminal, activez l'environnement et consultez :

```bash
psql -h localhost -U mobiliteiq -d mobiliteiq -W -c 'SELECT * FROM bi.etat_sources;'
```

Après vérification, arrêtez le service du premier terminal avec Ctrl+C avant de créer le service permanent. Ne lancez pas simultanément Docker, l'ancienne tâche de collecte et ce service WSL. Le verrou en base protège les écritures, mais une seule méthode d'exploitation simplifie le suivi.

### 3.4 Créer le service systemd permanent

Le nom du service dans ce parcours sera **mobiliteiq.service**. Il lance le même programme Python que le service Docker nommé `ingestion`.

Dans WSL, depuis le dossier du projet :

```bash
project_dir=$(pwd)
linux_user=$(id -un)
sudo tee /etc/systemd/system/mobiliteiq.service > /dev/null <<EOF
[Unit]
Description=MobiliteIQ - quatre ingestions automatiques
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$linux_user
WorkingDirectory=$project_dir
ExecStart=$project_dir/.venv/bin/python -m mobiliteiq serve
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=30
TimeoutStopSec=90

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now mobiliteiq.service
systemctl status mobiliteiq.service --no-pager
sudo journalctl -u mobiliteiq.service -n 80 --no-pager
```

Le chemin Linux choisi à l'étape 1 ne contient pas d'espaces. `.env` est lu par le programme, sous votre utilisateur; aucun mot de passe n'est inscrit dans le fichier de service. `active (running)` confirme que le processus tourne; vérifiez aussi les réussites en base pour confirmer les collectes.

Testez le redémarrage :

```bash
sudo systemctl restart mobiliteiq.service
systemctl is-active mobiliteiq.service
systemctl is-enabled mobiliteiq.service
```

Les deux réponses attendues sont `active` et `enabled`. Les dates conservées en base empêchent de relancer les lots réussis avant leur échéance. Une tentative restée `running` après interruption sera marquée en échec au prochain cycle verrouillé.

### 3.5 Démarrer WSL à l'ouverture de session Windows

Activer systemd ne démarre pas Ubuntu avant que Windows lance WSL. Pour ce laboratoire, configurez une tâche Windows qui lance et maintient une session WSL sous votre compte habituel.

Dans le **Planificateur de tâches Windows → Créer une tâche** :

1. Nom : `MobiliteIQ - maintien WSL`.
2. Choisissez votre utilisateur Windows habituel et **Exécuter uniquement si l'utilisateur est connecté**.
3. Déclencheur : **À l'ouverture de session**, pour cet utilisateur.
4. Action : **Démarrer un programme**.
5. Programme : `C:\Windows\System32\wsl.exe`.
6. Arguments, en adaptant le nom de distribution indiqué par `wsl --list --verbose` :

```text
-d Ubuntu --exec /bin/sleep infinity
```

7. Désactivez la limite d'arrêt après une durée et choisissez de ne pas démarrer une seconde instance si la tâche fonctionne déjà.
8. Selon votre usage, retirez la condition « démarrer uniquement sur secteur » et l'arrêt au passage sur batterie.
9. Lancez la tâche avec **Exécuter**. Le statut peut rester **En cours**, puisque le processus maintient la session WSL.

Cette tâche ne planifie pas les quatre sources : c'est Python qui le fait. Elle maintient WSL disponible. Vérifiez le service et les dates en base après une nouvelle ouverture de session Windows. Adaptez la veille dans les paramètres d'alimentation si vous attendez des collectes en continu. Un PC éteint, en veille ou une session fermée interrompt cette disponibilité; le présent montage n'est pas un serveur 24 h/24.

### 3.6 Surveiller et mettre à jour le projet

```bash
sudo journalctl -u mobiliteiq.service -f
```

Ctrl+C ferme le suivi des journaux sans arrêter le service. Pour examiner la qualité :

```bash
source .venv/bin/activate
python -m mobiliteiq monitor
psql -h localhost -U mobiliteiq -d mobiliteiq -W -c 'SELECT * FROM bi.ops_alertes;'
```

Le code de sortie 2 de `monitor` signifie qu'une alerte est ouverte. Examinez l'âge des collectes, les échecs, les rejets et l'âge réel de la météo. Aucun courriel ni message externe n'est envoyé.

Pour appliquer une modification depuis GitHub, sauvegardez d'abord votre base, puis :

```bash
sudo systemctl stop mobiliteiq.service
git status
git switch main
git pull --ff-only
source .venv/bin/activate
python -m pip install -r requirements.txt
RUN_PG_TESTS=1 python -m pytest -q
python -m mobiliteiq init-db
sudo systemctl start mobiliteiq.service
```

Si une commande échoue, résolvez le problème avant de poursuivre les suivantes. Ne changez pas de branche avec des modifications non enregistrées. Le schéma fourni est additif; une future migration destructive demandera une procédure propre.

Pour sauvegarder :

```bash
mkdir -p ~/MobiliteIQ-Backups
pg_dump -h localhost -U mobiliteiq -d mobiliteiq -W -Fc -f ~/MobiliteIQ-Backups/mobiliteiq_$(date +%Y%m%d_%H%M%S).dump
```

Conservez aussi `data/raw`, les modèles et la configuration dans un emplacement protégé. La base et le brut ne sont pas purgés automatiquement. Pour tester une restauration, créez une base distincte et utilisez `pg_restore`; ne testez pas une restauration sur votre base réelle.

### 3.7 Actualiser le rapport Power BI

Les vues PostgreSQL évoluent après chaque lot réussi. En mode **Import**, le rapport change seulement après son actualisation.

- Dans Desktop : **Home → Refresh**, puis enregistrez le PBIX.
- Pour automatiser dans Power BI Service : publiez dans un espace accessible avec votre licence, installez une passerelle locale sur un Windows disponible et configurez une connexion PostgreSQL avec le même serveur et la même base que le modèle.
- Dans les paramètres du modèle sémantique, associez la passerelle, vérifiez les identifiants et activez l'actualisation planifiée. Testez d'abord **Refresh now**, puis consultez l'historique d'actualisation.

Le serveur `localhost` de la passerelle désigne le Windows où elle est installée : pour ce laboratoire, utilisez le même PC que WSL et vérifiez que la passerelle y atteint PostgreSQL. Ne supposez pas qu'un test réussi dans Desktop garantit l'accès depuis le service de passerelle.

Une actualisation horaire du rapport Import dépend de la licence : la documentation indique jusqu'à 8 actualisations planifiées par jour en Pro et jusqu'à 48 pour PPU/Premium ou les capacités indiquées. Consultez les [limites et réglages officiels](https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-scheduled-refresh). Les ingestions horaires continuent même si le rapport s'actualise moins souvent. DirectQuery peut être étudié séparément selon votre rapport et les contraintes d'accès.

### 3.8 Faire la démonstration finale

| Vérification | Preuve à conserver |
|---|---|
| VS Code connecté à Ubuntu | Coin WSL et terminal Linux |
| Quatre sources collectées | bi.etat_sources avec réussites et dates |
| Automatisation active | État systemd et nouveaux lots aux échéances |
| Contrôle qualité | Tests de panne/rejet et maintien du dernier lot valide |
| Analyses et modèle | CSV statistiques, modèle versionné, limites expliquées |
| Power BI cohérent | Comparaison des cartes avec SQL et mode réel/démo visible |
| GitHub validé | Dernier commit, Pull request et workflow réussi |
| Actualisation du rapport | Date de refresh ou historique Power BI Service |

Demandez à une autre personne de filtrer un secteur, retrouver une entrave et vérifier la fraîcheur des sources. Notez le résultat dans `docs/UAT.md`. Vous avez terminé lorsque le service collecte aux échéances, que les tests passent et que le rapport affiche des chiffres vérifiés. La création du PBIX, la publication GitHub et la configuration du service restent des actions à exécuter sur votre installation.

### Dépannage rapide

| Problème | Action |
|---|---|
| Module Python introuvable | Revenir dans le dossier du projet et activer `.venv` |
| PostgreSQL refuse la connexion | Vérifier le service, le port et `.env` |
| Source en failed_source | Lire l'erreur du run et les journaux; vérifier Internet et le service public |
| Source en failed_quality | Examiner les rejets et les champs configurés; ne pas effacer le dernier lot valide |
| Pas de nouveau lot immédiatement | Vérifier la dernière tentative et le délai normal ou de reprise |
| systemd actif mais données anciennes | Inspecter la base ciblée, les erreurs et la fraîcheur météo |
| Plus de collecte après veille | Réveiller le PC, relancer WSL, vérifier service et tâche Windows |
| Modèle impossible à entraîner | Attendre l'historique requis ou utiliser mobiliteiq_demo |
| Power BI conserve les anciens chiffres | Actualiser et vérifier la base, les filtres et la passerelle |

Références : [VS Code avec WSL](https://code.visualstudio.com/docs/remote/wsl), [systemd dans WSL](https://learn.microsoft.com/en-us/windows/wsl/systemd), [PostgreSQL dans GitHub Actions](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers), [connecteur PostgreSQL Power BI](https://learn.microsoft.com/power-query/connectors/postgresql), [actualisation Power BI](https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-scheduled-refresh).

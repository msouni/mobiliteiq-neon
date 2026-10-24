# MobilitéIQ — guide pratique en 3 étapes

**PostgreSQL · Python dans WSL · VS Code · GitHub · Power BI**  
Version pédagogique du 17 octobre 2026. Explications en français; menus Power BI et VS Code en anglais.

Ce guide reprend le besoin d’affaires du PDF et les trois sprints du Groupe 5. Il remplace les commandes fragmentaires du journal `ProjectVersion, p.txt` par un nouveau socle de code cohérent. Ce journal ne contient pas les fichiers complets de l’ancien projet : ce paquet est une reconstruction pédagogique, pas une récupération de l’ancien dépôt. Ses anciens résultats « 62 tests réussis » ne sont pas des résultats de cette version.

**But :** aider un gestionnaire à repérer des situations routières inhabituelles dans la région de Québec, à voir les facteurs associés et à vérifier la fraîcheur des informations.

| Étape | Ce que vous obtenez | Correspondance avec les sprints |
|---|---|---|
| 1. Préparer et collecter | PostgreSQL, sources contrôlées, collecte réelle, historique, premier commit | Sprint 1, semaines 1–3, US01–06 |
| 2. Analyser et visualiser | Démonstration, KPI, analyse statistique, modèle d’anomalies, rapport Power BI | Sprint 2, semaines 4–6, US07–12; amorce US13–14 |
| 3. Tester et mettre en service | Tests PostgreSQL, CI, promotion d’une version, collecte planifiée, monitoring et démonstration | Sprint 3, semaines 7–9, US13–18 |

Ce sont trois **grandes étapes**, pas trois commandes. Ne passez au bloc suivant qu’après son point de contrôle. L’historique réel se construit avec le temps; une démo synthétique permet de préparer la BI entre-temps.

**Architecture retenue :** les quatre sources publiques alimentent Python. Python archive les réponses brutes, valide les données et écrit les observations dans PostgreSQL. Les agrégats par secteur et par heure alimentent l’analyse et le modèle. Les vues `bi` exposent les données à Power BI. GitHub Actions teste le code; le planificateur Windows lance la collecte WSL.

| Outil | Où il fonctionne | Son rôle |
|---|---|---|
| WSL Ubuntu | Sur votre ordinateur Windows | Exécute Python et le serveur PostgreSQL |
| VS Code | Windows, connecté au dossier WSL | Permet de lire/modifier les fichiers et d’ouvrir le terminal |
| PostgreSQL | Dans Ubuntu | Conserve les observations, les analyses, les scores et les journaux |
| Git / GitHub | Git local dans WSL; dépôt en ligne | Conserve les versions et exécute les tests automatiques |
| Power BI Desktop | Windows | Lit les vues PostgreSQL et affiche le rapport |

Python/pandas convient au périmètre régional retenu. PySpark n’est pas nécessaire pour ce socle; son ajout demanderait une justification par le volume mesuré. Docker, SSIS et Visual Studio ne sont pas nécessaires pour exécuter le laboratoire local. Le conteneur PostgreSQL de la CI est géré par GitHub, sans installation Docker locale.

## Étape 1 — Préparer PostgreSQL et collecter les données

### 1.1 Ouvrir le bon environnement

WSL, VS Code, GitHub et Power BI étant déjà installés, ne les réinstallez pas. Ouvrez **Ubuntu** depuis le menu Démarrer. Toutes les commandes Bash du guide s’exécutent dans Ubuntu ou dans le terminal WSL de VS Code. Les rares commandes PowerShell sont explicitement signalées.

```bash
mkdir -p ~/MobiliteIQ-Lab
cd ~/MobiliteIQ-Lab
explorer.exe .
```

Une fenêtre de l’Explorateur Windows s’ouvre sur ce dossier Linux. Copiez-y l’archive téléchargée `MobiliteIQ_PostgreSQL_3_etapes.zip`. Revenez dans Ubuntu :

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-client unzip git
unzip MobiliteIQ_PostgreSQL_3_etapes.zip
cd mobiliteiq-postgresql
code .
```

Cette commande installe les composants manquants nécessaires au projet. Le ZIP se décompresse dans `mobiliteiq-postgresql`. Si ce dossier existe déjà, utilisez un autre dossier de travail; ne remplacez pas votre ancien projet.

Dans VS Code, vérifiez que le coin inférieur gauche indique **WSL: Ubuntu** ou votre distribution Ubuntu. Puis **Terminal → New Terminal**.

```bash
pwd
python3 --version
git --version
```

**Contrôle :** le chemin se termine par `MobiliteIQ-Lab/mobiliteiq-postgresql`. Python 3.12 est le choix recommandé pour correspondre à la CI. Si votre Ubuntu utilise une autre version, notez-la; ne supprimez pas le Python système pour la remplacer.

### 1.2 Comprendre les fichiers sans tout modifier

| Fichier/dossier | Fonction |
|---|---|
| `mobiliteiq/core.py` | Règles de validation, dates, coordonnées et proximité géographique |
| `mobiliteiq/__main__.py` | Commandes, acquisition, historique, agrégats et monitoring |
| `mobiliteiq/analysis.py` | Statistiques et entraînement/scoring du modèle |
| `mobiliteiq/demo.py` | Génération de données explicitement synthétiques |
| `sql/schema.sql` | Tables PostgreSQL et vues utilisées par Power BI |
| `config/sources.json` | Territoire, champs des sources, fréquences et validation de l’audit |
| `.env.example` | Exemple de configuration locale, sans vrai mot de passe |
| `tests/` | Tests unitaires et tests nécessitant PostgreSQL |
| `.github/workflows/ci.yml` | Tests automatiques et paquet d’une version validée |
| `scripts/` | Exécution planifiée et promotion locale |
| `powerbi/Measures.dax` | Mesures à créer dans Power BI |

Il n’y a pas de fichier `.pbix` préfabriqué. Vous le construirez à l’étape 2 avec les instructions ci-dessous.

### 1.3 Démarrer PostgreSQL et créer trois bases séparées

```bash
sudo service postgresql start
pg_isready -h localhost -p 5432
sudo -u postgres psql -c '\du'
sudo -u postgres psql -c '\l'
```

Les deux dernières commandes montrent les comptes et les bases existants. Si le compte `mobiliteiq` n’existe pas :

```bash
sudo -u postgres createuser --login --pwprompt mobiliteiq
```

Choisissez un mot de passe local et conservez-le. La saisie peut rester invisible dans le terminal, c’est normal. Ce compte n’a pas besoin d’être superutilisateur.

Créez uniquement les bases absentes de la liste :

```bash
sudo -u postgres createdb --owner=mobiliteiq mobiliteiq
sudo -u postgres createdb --owner=mobiliteiq mobiliteiq_demo
sudo -u postgres createdb --owner=mobiliteiq mobiliteiq_test
```

| Base | Usage | Précaution |
|---|---|---|
| `mobiliteiq` | Collecte réelle et résultats réels | Conserver l’historique |
| `mobiliteiq_demo` | Démonstration synthétique | Ne pas présenter ses chiffres comme des observations réelles |
| `mobiliteiq_test` | Tests automatiques | Les tests effacent ses tables de travail; aucune donnée de cours à y conserver |

**Contrôle :**

```bash
psql -h localhost -U mobiliteiq -d mobiliteiq -W -c 'SELECT current_database(), current_user;'
```

Entrez le mot de passe choisi. Résultat attendu : base et utilisateur `mobiliteiq`. Si la connexion est refusée, vérifiez `pg_isready`, puis `sudo service postgresql status`. Si le mot de passe échoue, corrigez-le au lieu de désactiver l’authentification.

### 1.4 Préparer Python et les identifiants locaux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
code .env
```

Remplacez uniquement `REMPLACER_PAR_VOTRE_MOT_DE_PASSE` dans `.env` par votre mot de passe, sans guillemets. Les autres valeurs restent `localhost`, `5432`, `mobiliteiq`, `mobiliteiq`. Le fichier n’est pas envoyé à GitHub grâce à `.gitignore`. Ne publiez pas de capture de son contenu.

```bash
chmod 600 .env
python -m mobiliteiq init-db
python -m mobiliteiq --db mobiliteiq_demo init-db
python -m mobiliteiq --db mobiliteiq_test init-db
python -m pytest tests/test_core.py -q
```

**Contrôle :** « Base et vues prêtes » pour les trois bases et tests unitaires réussis. Dans un nouveau terminal, réactivez l’environnement avec `source .venv/bin/activate`.

### 1.5 Auditer les quatre sources réelles

L’audit vérifie ce que les services renvoient réellement. Il ne remplit pas encore les tables analytiques.

```bash
python -m mobiliteiq audit
code data/audit.json
```

Lisez les sections `travaux`, `debit`, `rtss`, `meteo`. Chaque section doit contenir un nombre de lignes, des noms de champs et jusqu’à deux exemples. Une section `error` doit être corrigée avant validation.

| Source | Champ identifiant configuré | Champs utiles configurés |
|---|---|---|
| Travaux MTMD | `identifiant` | `routeAutoroute` |
| Débit MTMD | `ide_sectn_trafc` | `rtss_debut`, `val_djma_annee_1` |
| RTSS MTMD | `ide_sous_r` | `num_route` |
| GeoMet, `climate-hourly` | `ID` | `UTC_DATE`, `TEMP`, `PRECIP_AMOUNT`, `WIND_SPEED` |

Ces champs ont été examinés sur des réponses des services lors de la préparation. Ils doivent être vérifiés à nouveau si les services changent. Un champ vide de DJMA reste manquant, il ne devient pas zéro. Le DJMA choisi est celui du champ année 1; documentez son année à partir de `djma_annee_1` dans les réponses brutes. Il n’y a pas de reprise silencieuse d’une année antérieure.

**Deux détails techniques déjà traités :** dans le fichier de configuration, le territoire est écrit longitude minimale, latitude minimale, longitude maximale, latitude maximale. Le code inverse ces axes uniquement pour le paramètre BBOX WFS 2.0 EPSG:4326 du MTMD. Les géométries GeoJSON restent longitude/latitude. GeoMet peut renvoyer `UTC_DATE` sans `Z`; ce champ explicitement UTC est traité en UTC.

Le territoire rectangulaire `[-71.6, 46.6, -71.0, 47.1]` couvre une zone autour de Québec, y compris des secteurs voisins. C’est un périmètre de travail proposé, pas la frontière administrative exacte de la Capitale-Nationale. Faites-le valider par l’équipe et l’enseignant.

Dans `config/sources.json`, remplacez `"validated": false` par `"validated": true` **pour chaque source dont vous avez vérifié les champs et les exemples**. Enregistrez. Ne modifiez pas les mots-clés JSON ni les virgules.

Les dates MTMD `debut` et `fin` sont conservées dans le brut mais ne sont pas encore utilisées : leur format et leur fuseau doivent être documentés avant activation. Il serait incorrect d’ajouter arbitrairement `Z` à une heure locale. Le rapport de départ parle donc d’entraves **présentes dans le dernier extrait**, et non d’entraves forcément actives maintenant.

Créez `docs/AUDIT_SOURCES.md` et notez pour chaque source : URL, licence, date de consultation, champs, unités, fréquence publiée, fréquence choisie, couverture, données manquantes et historique disponible. Pour GeoMet, observez le retard entre la collecte et `UTC_DATE` : les observations horaires publiées peuvent arriver tard. Ce décalage apparaîtra dans le monitoring.

### 1.6 Lancer la collecte et comprendre l’ETL

```bash
python -m mobiliteiq run --force
```

**E — Extraire :** Python interroge les services, suit la pagination et archive les réponses compressées dans `data/raw/`. Une empreinte SHA-256 accompagne chaque page pour en vérifier l’intégrité.

**T — Transformer :** les identifiants, dates, nombres et géométries sont contrôlés. Les doublons d’un même lot sont comptés. Les données hors territoire sont distinguées des rejets. Un lot trop invalide est refusé; le dernier lot valide reste disponible.

**L — Charger :** les observations valides sont ajoutées dans PostgreSQL avec leur identifiant de collecte. Les acquisitions successives restent distinctes. Le code calcule ensuite les comptes par secteur et par heure. Chaque lot et chaque rejet laissent une trace.

Les observations ne sont pas supprimées pour remplacer tout l’historique. Un nouvel instantané du même événement est normal. Dans une même heure, l’agrégat conserve le dernier lot valide; les détails des autres lots restent dans les observations.

**Contrôles :**

```bash
psql -h localhost -U mobiliteiq -d mobiliteiq -W -c "SELECT source,status,received,accepted,rejected,filtered,duplicates FROM runs ORDER BY started_at DESC LIMIT 8;"
psql -h localhost -U mobiliteiq -d mobiliteiq -W -c "SELECT count(*) FROM bi.fact_entraves;"
psql -h localhost -U mobiliteiq -d mobiliteiq -W -c "SELECT * FROM bi.ops_alertes;"
```

Attendez le statut `success` pour les quatre sources. Zéro entrave peut être légitime, mais doit être comparé à l’audit et au territoire. Un échec de la météo ne doit pas être interprété comme « pas de pluie ». Les valeurs indisponibles restent manquantes.

Après environ 30 minutes :

```bash
python -m mobiliteiq run
```

Sans `--force`, le programme respecte les intervalles : travaux 30 minutes, météo 60 minutes, débit et RTSS 24 heures. Ces intervalles sont des choix du projet, pas la garantie que les producteurs ont publié de nouvelles données.

**Preuve à conserver :** capture du terminal avec les quatre sources, requête montrant plusieurs collectes datées et premier journal d’erreur ou rejet. N’utilisez pas les nombres d’exemple de l’ancien journal comme valeurs attendues.

### 1.7 Faire un premier commit Git

Le dossier extrait est un nouveau projet. Vérifiez d’abord :

```bash
git status
```

Si Git indique que ce n’est pas un dépôt, initialisez-le :

```bash
git init -b main
git config user.name "Votre nom"
git config user.email "Votre adresse GitHub ou adresse noreply"
git add .gitignore .env.example requirements.txt mobiliteiq sql config scripts tests powerbi docs GUIDE_3_ETAPES.md README.md .github
git diff --cached --stat
git status
```

Vérifiez que `.env`, `data`, `models`, `logs`, `.venv` ne figurent pas parmi les fichiers ajoutés.

```bash
git commit -m "Initialiser MobiliteIQ PostgreSQL et la collecte"
git switch -c dev
```

Un **commit** conserve un état local du code. La branche **dev** sert aux modifications; **main** recevra les versions vérifiées. L’envoi à GitHub arrive à l’étape 3. Si vous travaillez déjà dans un dépôt, inspectez ses branches et son `git remote -v` au lieu de le réinitialiser.

**Fin de l’étape 1 :** vous devez pouvoir expliquer d’où viennent les données, retrouver le brut, voir au moins une collecte réelle réussie et vérifier que Git ignore vos identifiants.

## Étape 2 — Analyser les données et construire Power BI

### 2.1 Préparer une démonstration sans attendre un mois

```bash
python -m mobiliteiq --db mobiliteiq_demo demo
python -m mobiliteiq --db mobiliteiq_demo eda
python -m mobiliteiq --db mobiliteiq_demo train
python -m mobiliteiq --db mobiliteiq_demo export
```

La démo crée 30 jours de valeurs artificielles et un petit état courant de six points. Le module refuse de l’écrire dans la base réelle. S’il indique « Démo déjà initialisée », conservez-la et passez à `eda` ou `train` : il ne faut pas la recréer à chaque utilisation.

**Contrôle :**

```bash
psql -h localhost -U mobiliteiq -d mobiliteiq_demo -W -c "SELECT * FROM bi.info_projet;" -c "SELECT count(*) FROM bi.fact_secteur_heure;" -c "SELECT version,metrics FROM bi.modeles;"
```

Le mode doit être `DEMONSTRATION SYNTHETIQUE`, l’historique non vide et un modèle enregistré. La présence d’un modèle ne constitue pas une validation de sa performance sur le terrain.

### 2.2 Comprendre les tables et leurs limites

| Vue Power BI | Ce que représente une ligne | Usage |
|---|---|---|
| `fact_entraves` | Une entrave présente dans le dernier lot valide | Carte, axe et première observation |
| `historique_entraves` | Une entrave, avec première/dernière observation et durée observée | Durées et historique par événement |
| `fact_secteur_heure` | Un secteur de grille à une heure UTC observée | Évolution, météo associée, scores et anomalies |
| `dim_secteur` | Un code de secteur unique | Filtre partagé entre les deux faits |
| `dim_date` | Une date locale unique | Filtre de l’historique |
| `ops_ingestions` | Une exécution pour une source | Volumes, erreurs et dates |
| `ops_indicateurs` | Un indicateur courant pour une source | Fraîcheur, rejets et échecs |
| `ops_alertes` | Un indicateur actuellement en alerte | Intervention |
| `info_projet` | Le nom de la base et son mode | Bandeau réel/démo |
| `modeles` | Une version entraînée | Seuil, période et métriques |

Les secteurs sont une grille de 0,1 degré, pas des quartiers officiels. Une ligne traversant plusieurs secteurs est affectée au point représentatif de sa partie située dans le territoire : ce choix simplifie le laboratoire, mais peut sous-représenter certains secteurs traversés.

Le rapprochement utilise les géométries en projection métrique EPSG:32187 : RTSS et débit à 250 m maximum, météo à 50 km maximum et au plus 3 h avant le lot. Ces seuils sont des paramètres pédagogiques à valider sur une carte. Une route voisine n’est pas nécessairement la même route. Examinez les rapprochements et améliorez-les avec les identifiants RTSS avant une utilisation opérationnelle.

Le modèle analytique enregistre le contexte disponible au moment de la collecte. Les observations météo arrivant après cette collecte ne sont pas automatiquement réinjectées dans les anciens agrégats; un traitement de rattrapage est une amélioration à prévoir.

### 2.3 Lire les analyses avant de regarder les anomalies

Les fichiers `exports/mobiliteiq_demo/statistiques.csv`, `manquants.csv` et `correlations_spearman.csv` sont produits par `eda`. Ouvrez-les dans VS Code ou Excel.

1. Regardez le taux de valeurs manquantes de chaque variable.
2. Comparez minimum, médiane et maximum du nombre d’entraves présentes.
3. Cherchez les heures ou secteurs qui se distinguent.
4. Examinez les corrélations de Spearman entre variables, sans les présenter comme des causes.
5. Rédigez trois constats et deux limites dans `docs/ANALYSE.md`.

Exemple de formulation à adapter à vos résultats : « Certaines heures présentent davantage d’entraves dans ce secteur. Il faut vérifier la stabilité de ce constat sur un historique plus long. » N’écrivez pas « la pluie cause la congestion » : ces sources ne mesurent pas directement ce phénomène.

### 2.4 Comprendre l’apprentissage machine

Le programme utilise **Isolation Forest**, un algorithme qui repère des combinaisons rares. Les variables candidates sont le nombre d’entraves présentes, le DJMA maximal associé, la température, les précipitations et le vent. Une variable n’est retenue que si elle est suffisamment renseignée et varie pendant l’entraînement.

Le découpage se fait dans l’ordre du temps : environ 80 % des heures pour apprendre, puis 20 % pour examiner de nouvelles heures. Tous les secteurs d’une même heure restent du même côté. Les valeurs manquantes sont remplacées par des médianes apprises uniquement sur l’entraînement.

Le seuil correspond au 97e percentile du score d’entraînement : environ les 3 % de scores les plus élevés servent de référence. Ce seuil n’est ni une vérité métier ni une garantie de 3 % d’alertes futures. La colonne `score` est un indice, pas une probabilité.

Les métriques enregistrées comprennent le taux d’alertes sur la période suivante et une expérience de sensibilité où le nombre d’entraves est artificiellement augmenté. **Ce test artificiel n’est pas une précision, un rappel ni un taux de réussite réel.** Pour évaluer l’utilité métier, faites examiner un échantillon d’alertes et de cas normaux par l’équipe, consignez les décisions et calculez des métriques sur ces étiquettes si elles sont fiables.

L’explication indique la variable qui s’éloigne le plus de la médiane en unités de MAD, une mesure robuste de dispersion. C’est une description du cas, pas une attribution causale du modèle. La variable dominante peut ne pas être celle qui a le plus influencé Isolation Forest.

Sur les vraies données, attendez au moins 10 jours couvrant 40 heures distinctes; 3 à 4 semaines sont préférables pour un premier bilan. Ensuite :

```bash
python -m mobiliteiq eda
python -m mobiliteiq train
python -m mobiliteiq score
```

`train` crée une nouvelle version et calcule les scores. `score` réutilise la dernière version. Le minimum de dix jours évite un entraînement presque vide; il ne garantit pas une couverture statistique suffisante. Le modèle global n’ajuste pas encore une normale par secteur et par heure de semaine : comparer une baseline saisonnière est une amélioration importante.

### 2.5 Connecter Power BI à PostgreSQL

Power BI Desktop reste ouvert sous **Windows**. Le serveur reste dans **WSL**. Commencez avec la démonstration.

1. **Home → Get data → More…**.
2. Cherchez **PostgreSQL database**, puis **Connect**.
3. **Server** : `localhost:5432`.
4. **Database** : `mobiliteiq_demo`.
5. Sélectionnez **Import**, puis **OK**.
6. Choisissez **Database** pour l’authentification; saisissez `mobiliteiq` et le mot de passe local.
7. Dans **Navigator**, sélectionnez les vues `bi` du tableau ci-dessus.
8. Cliquez **Transform Data**; renommez les requêtes avec leur nom court, par exemple `fact_entraves` et `ops_alertes`.
9. Vérifiez les types : dates/heures, nombres décimaux, booléens pour `anomaly` et `ok`. Puis **Close & Apply**.

Le fournisseur PostgreSQL est intégré aux versions modernes de Power BI Desktop; ne commencez pas par installer un pilote ODBC MongoDB. La connexion Windows vers un service WSL utilise normalement `localhost`. Si elle échoue, utilisez les contrôles de dépannage à l’étape 3.

Pour le laboratoire local uniquement, si Power BI propose explicitement de continuer sans chiffrement sur `localhost`, cela concerne cette connexion locale. Une base distante doit utiliser une configuration TLS adaptée.

### 2.6 Créer les relations et les mesures

Dans **Model view → Manage relationships → New**, créez ces relations :

| Côté « 1 » | Côté « * » | Filtrage |
|---|---|---|
| `dim_secteur[sector]` | `fact_entraves[sector]` | Single |
| `dim_secteur[sector]` | `fact_secteur_heure[sector]` | Single |
| `dim_date[date_key]` | `fact_secteur_heure[date_key]` | Single |
| `dim_date[date_key]` | `historique_entraves[date_key]` | Single |
| `dim_secteur[sector]` | `historique_entraves[sector]` | Single |

Ne reliez pas les deux tables de faits directement. Ne créez pas de relation entre `ops_*` et les faits. Dans `historique_entraves`, le filtre de date sélectionne la date de première observation. Le filtre de date concerne l’historique; la carte affiche le dernier état, même si vous sélectionnez une date passée. Ajoutez cette explication dans le rapport.

Créez une table de mesures avec **Home → Enter data**, nommez-la `_Measures`, puis **Load**. Conservez sa colonne provisoire jusqu’à avoir créé une première mesure avec **Modeling → New measure**. Copiez une définition à la fois depuis `powerbi/Measures.dax`. Vous pourrez ensuite masquer la colonne provisoire, plutôt que supprimer toute la table.

Les mesures fournies utilisent des virgules comme séparateurs d’arguments. Si votre installation exige le DAX local français, utilisez des points-virgules pour les arguments. Le langage d’affichage anglais de Power BI n’impose pas à lui seul les séparateurs DAX. Essayez d’abord la mesure simple `Entraves présentes`.

**Contrôle :** comparez sa carte au résultat SQL `SELECT count(*) FROM bi.fact_entraves;` sans filtre actif. Les nombres doivent correspondre.

### 2.7 Construire trois pages de rapport

**Page « Situation actuelle »**

- Une carte **Card** : `Entraves présentes`.
- Une carte : `Nouvelles observées 24 h`.
- Une table : `event_id`, `axe`, `sector`, `collecte_utc`, `premiere_observation_utc`.
- Une carte géographique avec `latitude` et `longitude` de `fact_entraves`; dans **Column tools → Data category**, attribuez **Latitude** et **Longitude**, puis **Don't summarize**.
- Un filtre **Slicer** : `dim_secteur[sector]`; un filtre d’axe à partir de `fact_entraves[axe]`.
- Un bandeau visible à partir de `info_projet[mode]`.

La carte Azure Maps dépend des paramètres de l’organisation et de l’accès réseau. Si elle est désactivée, gardez la table des coordonnées comme solution provisoire, puis faites valider l’activation du visuel cartographique pour la démonstration finale.

La mesure « Nouvelles observées 24 h » ne compte que les entraves encore présentes dans le dernier lot et vues pour la première fois au cours des 24 dernières heures de collecte. Elle ne compte pas toutes celles apparues puis disparues dans cet intervalle. Conservez ce libellé précis ou étendez la vue avec l’ensemble de l’historique avant d’annoncer un KPI exhaustif.

**Page « Historique et anomalies »**

- **Line chart** : `heure_locale` sur l’axe X et moyenne de `n_presentes` sur Y.
- **Slicer** : `dim_date[date_key]` et `dim_secteur[sector]`.
- Table : `heure_locale`, `sector`, `n_presentes`, `djma_max`, `temp_c`, `precip_mm`, `score`, `anomaly`, `explanation`.
- Filtre de table : `phase = evaluation_ou_nouveau` pour exclure les scores d’entraînement de l’évaluation.
- Mise en forme conditionnelle d’`anomaly` pour repérer les lignes à examiner.

Ne sommez pas les nombres d’entraves de toutes les heures pour annoncer un nombre d’événements distincts : le même événement peut apparaître plusieurs fois. En changement d’heure, deux heures locales peuvent porter le même libellé; `hour_utc` reste la clé temporelle non ambiguë.

Ajoutez aussi une table issue de `historique_entraves` : événement, axe, première observation, dernière observation, `duree_observee_h` et `presente_dernier_extrait`. Cette durée est la différence entre deux observations de votre collecte. Elle vaut zéro pour un événement vu une seule fois et constitue une durée observée minimale, pas la durée totale officielle. Une absence n’est pas une preuve de fin exacte.

**Page « Qualité et exploitation »**

- Carte : `Alertes de qualité`.
- Table `ops_indicateurs` : source, nom, valeur, seuil, état `ok`, date de calcul.
- Table `ops_ingestions` : source, statut, reçues, acceptées, rejetées, filtrées, durée et erreur.
- Table des alertes ouvertes.

**Contrôle :** sélectionnez un secteur; la carte et son détail doivent se filtrer. Sélectionnez une date; l’historique doit changer. Vérifiez qu’une alerte n’est pas présentée comme une anomalie routière : une alerte d’exploitation peut simplement signaler une source trop ancienne.

Enregistrez avec **File → Save as**, sous `MobiliteIQ_Demo.pbix` dans votre dossier Windows de travail. La création et la vérification visuelle du PBIX sont à faire dans Power BI; elles ne sont pas simulées dans le ZIP.

### 2.8 Passer aux données réelles

Faites une copie `MobiliteIQ_Reel.pbix`. Dans **Transform data → Data source settings**, modifiez la base vers `mobiliteiq`, conservez les mêmes vues et **Refresh**. Vérifiez le bandeau `DONNEES REELLES`, les dates et les volumes. Ne remplissez jamais une vue réelle avec la démo pour « avoir des chiffres ».

Une actualisation **Import** est nécessaire pour voir les nouveaux lots. **Refresh** dans Desktop n’est pas une actualisation automatique permanente. Une publication dans Power BI Service avec une base locale demande une passerelle, les autorisations et une planification distincte; elle n’est pas déployée par ce paquet.

**Fin de l’étape 2 :** vous devez avoir une carte, des KPI réconciliés avec SQL, des observations statistiques, des scores interprétés avec leurs limites et un rapport qui distingue réel et démonstration.

## Étape 3 — Tester, versionner et mettre en service

### 3.1 Exécuter les tests PostgreSQL localement

Dans le terminal WSL, à la racine du projet, environnement Python activé :

```bash
RUN_PG_TESTS=1 python -m pytest -q
```

Le fichier de configuration de tests charge `.env`; les tests d’intégration utilisent explicitement `mobiliteiq_test`. Ils ne doivent jamais viser la base réelle.

| Type | Vérification |
|---|---|
| Unitaire | Identifiants, coordonnées, champs manquants, nombres, fuseaux, distances, découpage temporel |
| Intégration PostgreSQL | Historisation, doublons, lot invalide et conservation du dernier état valide |
| Échec simulé | Source indisponible, journal et alerte |
| UAT automatisé partiel | Événement visible avec coordonnées et indicateur de fraîcheur |

**Contrôle :** tous les tests passent, sans test PostgreSQL « skipped ». Sans `RUN_PG_TESTS=1`, les tests PostgreSQL sont volontairement sautés; ce n’est pas une preuve de fonctionnement de la base.

Pour montrer le scénario d’échec :

```bash
RUN_PG_TESTS=1 python -m pytest tests/test_postgres.py::test_source_failure_is_visible -q -s
```

La panne est créée dans le test; il n’est pas nécessaire de casser votre vraie connexion.

### 3.2 Publier le dépôt sur GitHub et faire fonctionner la CI

Sur GitHub, créez un nouveau dépôt `MobiliteIQ-PostgreSQL`, sans README ni licence ajoutés automatiquement. Copiez son URL HTTPS. Dans les commandes suivantes, remplacez `VOTRE_COMPTE` par votre compte.

```bash
git status
git add config docs mobiliteiq tests sql scripts powerbi .github requirements.txt
git diff --cached --stat
git commit -m "Valider les sources et préparer analyses et tests"
git remote -v
```

S’il n’existe pas de remote `origin` :

```bash
git remote add origin https://github.com/VOTRE_COMPTE/MobiliteIQ-PostgreSQL.git
```

S’il existe déjà, vérifiez son URL avant tout changement. Utilisez `git remote set-url origin ...` seulement si elle désigne le mauvais dépôt.

```bash
git push -u origin main
git push -u origin dev
```

Authentifiez-vous avec le mécanisme GitHub proposé par votre installation; ne placez pas de jeton dans l’URL ou dans `.env.example`.

Sur GitHub, ouvrez **Actions → MobiliteIQ CI et paquet valide**. Le workflow installe Python 3.12, démarre PostgreSQL 16 dans un service temporaire et exécute les tests. Son mot de passe `test_ci_only` ne concerne que cette base jetable.

Créez ensuite **Pull requests → New pull request**, avec **base: main** et **compare: dev**. Une pull request permet de relire les changements avant fusion. Attendez les tests verts, puis **Merge pull request**. Cette fusion crée un nouvel état de `main`; vérifiez aussi son exécution CI.

```bash
git switch main
git pull --ff-only origin main
```

**Preuves :** captures des tests sur `dev`, de la PR vers `main` et du run correspondant au commit fusionné. Ne confondez pas une ancienne coche verte avec la validation du dernier code.

### 3.3 Promouvoir une version validée — CD à déclenchement manuel

La **CI** vérifie le code. La **CD** promeut une version vérifiée vers l’environnement cible. Ici, le paquet est produit automatiquement après les tests d’un tag; la promotion dans WSL est lancée manuellement. GitHub n’accède pas directement à votre ordinateur.

Avant le tag, assurez-vous que `config/sources.json` contient les quatre validations de sources et que les tests complets réussissent.

```bash
git tag v1.0.0
git push origin v1.0.0
```

Attendez le workflow du tag. Dans le run réussi, téléchargez **Artifacts → mobiliteiq-release**. Extrayez le ZIP téléchargé dans un dossier `release-download` à la racine du projet; vous devez y voir `mobiliteiq-release.tar` et `SHA256SUMS`.

Vérifiez l’intégrité dans ce dossier : le fichier de sommes contient le préfixe `dist/`, conformément au paquet CI. Créez cette disposition avant le contrôle :

```bash
cd ~/MobiliteIQ-Lab/mobiliteiq-postgresql/release-download
mkdir -p dist
cp mobiliteiq-release.tar dist/
sha256sum -c SHA256SUMS
cd ..
```

Le résultat doit être `OK`. Puis :

```bash
bash scripts/deploy.sh release-download/mobiliteiq-release.tar v1.0.0
```

Le script installe la version dans `~/mobiliteiq-releases/v1.0.0`, utilise les dépendances figées par la CI, partage les données locales, rejoue les tests dans `mobiliteiq_test`, initialise les tables manquantes, puis déplace le lien `~/mobiliteiq-current` vers la version. `.env` reste local. Ne lancez pas une collecte simultanée pendant une promotion.

**Contrôle :**

```bash
readlink -f ~/mobiliteiq-current
cat logs/deploy.log
cd ~/mobiliteiq-current
.venv/bin/python -m mobiliteiq run
```

Le lien doit viser la version attendue et le journal contenir sa date de promotion. Conservez les versions précédentes. Pour revenir au code d’une version existante, après avoir interrompu la planification :

```bash
ln -s "$HOME/mobiliteiq-releases/v1.0.0" "$HOME/mobiliteiq-current.rollback"
mv -Tf "$HOME/mobiliteiq-current.rollback" "$HOME/mobiliteiq-current"
```

Cet exemple vise `v1.0.0`; choisissez une version réellement existante. Le retour du code n’annule pas les modifications de données. Avant une future migration destructive du schéma, prévoyez une migration versionnée et une restauration testée. Le schéma fourni ici est une initialisation additive, pas un outil complet de migrations.

### 3.4 Planifier la collecte depuis Windows

Après avoir validé `run` manuellement, préparez le démarrage PostgreSQL. Dans WSL :

```bash
ps -p 1 -o comm=
```

Si la réponse est `systemd` :

```bash
sudo systemctl enable --now postgresql
```

Sinon, démarrez PostgreSQL avec `sudo service postgresql start` à chaque nouvelle session. Pour une exploitation autonome, faites configurer le démarrage du service avant de considérer la collecte comme permanente.

Dans **PowerShell Windows**, vérifiez le nom exact de votre distribution :

```powershell
wsl -l -v
```

Ouvrez **Task Scheduler** (Planificateur de tâches), puis **Create Task** :

1. Nom : `MobiliteIQ - collecte`.
2. **Triggers → New** : quotidien, répétition toutes les **30 minutes**, durée **Indefinitely**.
3. **Actions → New → Start a program**.
4. **Program/script** : `C:\Windows\System32\wsl.exe`.
5. **Add arguments** : la ligne suivante, en remplaçant `Ubuntu` si nécessaire :

```text
-d Ubuntu -- bash -lc "cd ~/mobiliteiq-current && bash scripts/run_once.sh"
```

6. **Settings** : ne pas démarrer une nouvelle instance si la tâche est déjà en cours; exécuter dès que possible si un démarrage planifié a été manqué.
7. Testez avec **Run**, puis examinez `logs/pipeline.log` et le résultat de la tâche.

```bash
cd ~/mobiliteiq-current
tail -n 40 logs/pipeline.log
```

Le code conserve les intervalles propres aux sources : le planificateur se réveille toutes les 30 minutes, mais le débit et RTSS ne sont interrogés qu’une fois par jour. Le verrou PostgreSQL évite deux traitements simultanés du projet dans une même base.

Un ordinateur éteint ou endormi ne collecte pas normalement les instantanés manqués. Un rattrapage météo ne recrée pas les anciens états des travaux. Cette installation est une mise en service de laboratoire; pour du 24/7, utilisez un serveur toujours disponible et validez sauvegardes, accès et supervision.

### 3.5 Surveiller les alertes et protéger l’historique

```bash
.venv/bin/python -m mobiliteiq monitor
```

Un code de sortie 2 signifie qu’il existe une alerte, pas nécessairement que Python est défectueux. Consultez `bi.ops_alertes` et les messages associés dans `runs`.

Les indicateurs suivent la fraîcheur de collecte, les échecs consécutifs, les rejets, ainsi que l’âge réel des observations météo. Le mécanisme de signalement fourni est le message terminal et la vue d’alertes Power BI. Il n’envoie pas d’email ni de message à l’équipe.

La vue d’alertes est un état courant, pas un historique d’acquittement. Les anciens runs et rejets restent consultables. Une prochaine amélioration serait de conserver les ouvertures, résolutions et responsables de chaque alerte.

Pour sauvegarder la base réelle avant une évolution importante :

```bash
mkdir -p ~/mobiliteiq-backups
pg_dump -h localhost -U mobiliteiq -d mobiliteiq -W -Fc -f ~/mobiliteiq-backups/mobiliteiq_$(date +%Y%m%d_%H%M%S).dump
```

Conservez aussi `data/raw`, `models` et la configuration locale dans un emplacement protégé, distinct du dépôt Git. Vérifiez la taille chaque semaine :

```bash
du -sh data models logs
psql -h localhost -U mobiliteiq -d mobiliteiq -W -c "SELECT pg_size_pretty(pg_database_size(current_database()));"
```

Politique proposée pour le cours : garder toutes les données pendant les neuf semaines, puis archiver le brut et la base. Aucune purge automatique n’est activée. La météo récupère une fenêtre glissante de deux jours; ses répétitions sont historisées par collecte et peuvent accroître le volume. Ajustez la rétention après mesure, sans perdre les preuves nécessaires.

Après validation, vous pouvez créer un compte Power BI distinct, en lecture seule, et lui accorder uniquement `USAGE` sur `bi` et `SELECT` sur ses vues. Le compte de développement fourni est le propriétaire des tables : il convient au laboratoire, pas à une séparation complète des rôles de production.

### 3.6 Faire la démonstration finale et le test utilisateur

Le scénario utilisateur est : « Je suis gestionnaire, je cherche une situation à examiner, je vérifie son contexte et je m’assure que les données sont suffisamment récentes. »

| Action à montrer | Preuve attendue | Exigence couverte |
|---|---|---|
| Lancer une acquisition réelle | Nouveau run horodaté et réponse brute conservée | Collecte automatique, traçabilité |
| Relancer après un intervalle | Historique augmenté, pas de reconstruction complète | Incrémentalité et historique |
| Exécuter le test de panne | Run échoué et alerte | Robustesse et monitoring |
| Actualiser Power BI | Chiffres réconciliés avec SQL | KPI et tableau de bord |
| Filtrer un secteur puis une date | Carte, détails et historique cohérents | Exploration |
| Examiner une anomalie | Version, score, seuil, variables et explication | ML interprétable |
| Montrer les résultats d’analyse | Statistiques, valeurs manquantes et limites | Analyse exploratoire/avancée |
| Montrer les tests et le tag validé | CI verte et paquet de la bonne version | Tests et CI |
| Montrer le lien de version et le journal | Version déployée dans WSL | CD reproductible |
| Demander à une autre personne d’utiliser le rapport | Observation, résultat attendu/obtenu, décision | UAT humain |

Dans `docs/UAT.md`, consignez la date, la base utilisée, la version du code et les résultats. L’UAT automatisé ne remplace pas cette vérification du rapport par une personne.

**Livrables à préparer pour le cours :** dépôt GitHub, guide, audit des quatre sources, rapport Power BI, analyse statistique, fiche modèle, captures des tests et CI/CD, journal de démonstration et limites. Le PDF ne donne pas de nom de fichier de remise obligatoire; adaptez les noms aux indications de l’enseignant.

### 3.7 Dépannage ciblé

| Symptôme | Vérification et action |
|---|---|
| `No module named mobiliteiq` | Revenir à la racine contenant le dossier `mobiliteiq`; réactiver `.venv` |
| PostgreSQL « connection refused » | `pg_isready`, puis démarrage du service; vérifier le port |
| Mot de passe refusé | Vérifier `.env` et le compte avec `psql -h localhost ... -W` |
| `validated` / audit non validé | Lire `data/audit.json`, vérifier les champs, passer la source concernée à `true` |
| Réponse XML/HTML au lieu de JSON | Service indisponible ou paramètre WFS refusé; relancer l’audit et consulter le brut |
| Tous les travaux sont hors territoire | Vérifier longitude/latitude et l’ordre BBOX; ne pas inverser toutes les géométries |
| Météo ancienne malgré collecte réussie | Comparer `UTC_DATE` à l’heure de collecte; ne pas masquer l’alerte de retard |
| Modèle impossible à entraîner | Historique trop court ou variables constantes/manquantes; utiliser la démo pour apprendre |
| Power BI ne joint pas `localhost:5432` | Vérifier d’abord la connexion `psql` dans WSL, puis `Test-NetConnection localhost -Port 5432` dans PowerShell |
| Conflit avec un PostgreSQL Windows | Vérifier quel serveur répond; utiliser un port local distinct configuré de manière cohérente |
| Power BI conserve d’anciens identifiants | **File → Options and settings → Data source settings**, choisir la source et modifier les permissions |
| Carte désactivée | Vérifier les paramètres cartographiques de l’organisation; garder la table en attendant |
| CI « skipped » pour PostgreSQL | Vérifier `RUN_PG_TESTS=1` et le service PostgreSQL du workflow |
| La collecte planifiée ne démarre pas | Vérifier distribution WSL, lien `mobiliteiq-current`, service PostgreSQL et journal de tâche |

Si `localhost` ne fonctionne pas malgré un serveur WSL valide, examinez le réseau WSL et les règles de pare-feu ciblées; n’ouvrez pas PostgreSQL à tout Internet. Une exportation CSV avec `python -m mobiliteiq export` permet un travail provisoire dans Power BI (**Get data → Text/CSV**). Les booléens exportés par PostgreSQL peuvent être `t/f` : remplacez-les par `true/false` dans Power Query avant de les typer. Cet export manuel ne remplace pas l’acquisition automatisée.

### 3.8 Ce qui est fourni et ce qui reste à prouver

Le paquet fournit du code, des tests, des commandes, des vues et une procédure. Il ne prouve pas que votre installation, votre rapport Power BI ou votre compte GitHub ont déjà été configurés.

La reconstruction couvre une baseline : collecte des quatre sources, brut, validation, historique, agrégats, rapprochement géographique, EDA, Isolation Forest, scores versionnés, monitoring et promotion locale. Elle demande encore une validation terrain des rapprochements, une définition métier des entraves réellement actives et des durées, un audit de couverture des données et une évaluation métier du modèle. Ces points sont explicitement signalés pour ne pas présenter un prototype comme une solution de production terminée.

Pour compléter les KPI de durée exigés par le sujet : documentez le fuseau des dates MTMD, testez leur conversion avec des cas hiver/été, puis distinguez durée prévue (`fin - debut`), âge depuis première observation et durée observée entre première et dernière présence. Une disparition entre deux collectes situe la fin dans un intervalle; elle ne donne pas une heure exacte. Le calcul de durée réalisée et le statut « actif » doivent tenir compte des horaires d’entrave, pas uniquement des dates du chantier. Faites valider cette définition avant de renommer les cartes.

### Références de travail

Les exigences pédagogiques proviennent du PDF MobilitéIQ et du PowerPoint Groupe 5 fournis. Les choix de seuils et d’implémentation de ce guide sont des propositions, pas des prescriptions de l’enseignant.

- Travaux routiers MTMD : https://www.donneesquebec.ca/recherche/dataset/travaux-routiers
- Débit de circulation : https://www.donneesquebec.ca/recherche/dataset/debit-de-circulation
- Réseau routier RTSS : https://www.donneesquebec.ca/recherche/dataset/reseau-routier-rtss
- GeoMet, observations horaires : https://api.weather.gc.ca/collections/climate-hourly?f=html
- Schéma GeoMet : https://api.weather.gc.ca/collections/climate-hourly/schema?f=html
- Connecteur PostgreSQL Power BI : https://learn.microsoft.com/power-query/connectors/postgresql
- Connexions réseau WSL : https://learn.microsoft.com/en-us/windows/wsl/networking
- PostgreSQL dans GitHub Actions : https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers

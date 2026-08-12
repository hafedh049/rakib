# Rakib — رقيب

Plateforme de gestion intelligente des réclamations pour un opérateur télécom
tunisien. Classification, priorisation, détection de doublons, routage et
assistance à la rédaction — **entièrement en local**, sans service d'inférence
externe.

**Live :** <https://reclamations.activiity.com>

---

## Ce qui rend ce projet différent

Pas d'appel à un LLM au runtime. Pas de clé API. Pas de GPU. L'intelligence est
du TF-IDF calibré, des règles pondérées et de la recherche d'information —
le tout en process, en quelques dizaines de millisecondes.

Trois choses en découlent, et ce sont les trois qu'il faut regarder :

1. **Chaque décision est explicable.** Une réclamation classée P1 affiche les
   règles qui se sont déclenchées, *les termes exacts* qui les ont déclenchées,
   et leur poids. Un superviseur peut discuter avec le système, pas seulement
   lui faire confiance.
2. **L'incertitude est un état conçu, pas une erreur.** Sous le seuil de
   confiance, le système le dit et demande un humain. 70 % des messages
   volontairement inclassables du jeu de test sont correctement renvoyés en
   triage humain.
3. **Le système fonctionne sans modèle.** Supprimez `ml_artifacts/`, redémarrez :
   le routage se fait par mots-clés pondérés par IDF, et `/health/ready`
   l'annonce explicitement.

---

## Démarrage

```bash
cp .env.example .env
docker compose up --build          # api, worker, notifier, mongo, redis, minio
docker compose exec api python -m scripts.seed --force
```

→ <http://localhost:5173> · `admin@rakib.tn` / `Rakib2026!`

### Tests

```bash
docker compose -f docker-compose.test.yml run --rm tests            # pytest
docker compose -f docker-compose.test.yml run --rm tests ruff check app tests scripts
docker compose -f docker-compose.test.yml run --rm tests mypy app
```

---

## Les données — d'où elles viennent réellement

C'est la question qu'on posera en premier, donc voici la réponse complète.

| Source | Volume | Rôle |
|---|---|---|
| **Avis Play Store réels** (My Ooredoo, My TT, Orange Max it Tunisie) | 19 771 collectés → 4 593 tunisiens → **656 étiquetés** | Entraînement + validation sur texte réel |
| **Corpus rédigé** (templates + bruit) | **3 630** | Couvre les 10 catégories que la collecte ne couvre pas |
| **Jeu « gold »** rédigé à la main | **205** (dont 40 inclassables) | Évaluation indépendante |
| **Jeu « wild »** réel, jamais entraîné | **192** | Validation sur texte réel non vu |

**La collecte réelle est app-centrée** : 506 des 656 lignes étiquetées sont
`APPLICATION_MOBILE`. Le réel ne peut donc pas porter l'entraînement ; il porte
une catégorie et la validation. Le corpus rédigé porte les dix autres. C'est
dit ici parce que c'est vrai, pas parce que c'est flatteur.

L'étiquetage faible (`scripts/labeling.py`) n'étiquette que lorsque l'évidence
est non ambiguë et **jette le reste** : 656 gardés sur 4 593. Précision contre
rappel, délibérément.

### Résultats mesurés

| Jeu d'évaluation | macro-F1 | exactitude |
|---|---|---|
| Holdout synthétique | **0,993** | 0,99 |
| **Gold** (rédigé, indépendant, autre registre) | **0,761** | 0,745 |
| **Wild** (avis réels, jamais entraînés) | 0,493 | **0,932** |
| Inclassables → triage humain | — | **70 %** |

L'écart 0,993 → 0,761 **est le résultat**. Il mesure la part du score de
holdout qui n'était que de la mémorisation de templates. Un 0,99 annoncé seul
serait un chiffre sans signification.

*(macro-F1 bas sur « wild » avec 93 % d'exactitude : le jeu est dominé par une
catégorie, donc les classes à 1–2 exemples écrasent la moyenne macro.)*

---

## Architecture

```
api → services → intelligence          intelligence n'importe jamais api/ ni models/
                → models
```

Le pipeline, six étapes, cible < 50 ms :

```
normalize → language → classify → rules/priority → dedup → decide
```

- **normalize** — FR/AR/derja. Signatures et citations retirées, URL/email/
  téléphone masqués, diacritiques et alef normalisés. L'arabizi est translittéré
  **en gardant les deux écritures**, donc « 3andi mochkla » et « ما عنديش »
  atterrissent au même endroit.
- **language** — fastText `lid.176.ftz` (917 Ko, committé), avec repli
  script + mots vides si l'artefact manque. `ar-tn` est notre décision :
  fastText n'a pas d'étiquette pour la derja.
- **classify** — union TF-IDF mots (1,2) + caractères `char_wb` (3,5),
  LinearSVC calibré (sigmoid). Les n-grammes de caractères absorbent fautes,
  écriture arabe et arabizi sans modèle séparé.
- **rules** — stockées en base, éditables depuis l'admin. Six types. Chaque
  déclenchement enregistre **les termes détectés**.
- **dedup** — cosinus + rapidfuzz + shingles. Un doublon inter-réclamant exige
  un score bien plus élevé et devient « lié », pas « doublon » : quarante
  personnes signalant une panne sont un incident collectif.
- **decide** — seuils, routage, SLA. Dans `services/`, pas dans le moteur :
  c'est de la politique, pas de l'inférence.

---

## Performance mesurée

Namespace limité à **2 vCPU / 4 Go**, conformément à la contrainte annoncée.
`POST /complaints` (le seul chemin qu'un réclamant attend ; le triage est
asynchrone) :

| Concurrence | req/s | p50 | p95 | p99 |
|---|---|---|---|---|
| 1 | 15,0 | 47,7 ms | 190,5 ms | 294,4 ms |
| 2 | 17,5 | 74,9 ms | 289,5 ms | 690,9 ms |
| 5 | 42,7 | 84,4 ms | 243,9 ms | 568,8 ms |
| 10 | 63,2 | 135,0 ms | 301,0 ms | 353,4 ms |
| 20 | 51,4 | 229,3 ms | 865,0 ms | 1002,6 ms |

**L'objectif de < 100 ms p95 n'est pas atteint sur cette machine.** Le p50 le
reste jusqu'à une concurrence de 5. Décomposition mesurée, plutôt qu'une
excuse :

| Mesure | p50 |
|---|---|
| `GET /health` (aucune E/S) | 4,6 ms |
| `ping` Mongo depuis le pod API | 3,0 ms |
| `insert` Mongo | 5,2 ms |
| compteur `findAndModify` | 3,7 ms |

Un ping pod-à-pod à 3 ms sur le même nœud est environ quinze fois le coût
attendu. Le conteneur n'est pas étranglé par sa limite CPU (10 périodes
throttled sur 1085) : **l'hôte est partagé** et tourne à une charge de 10 à 13
sur 16 cœurs pour d'autres projets. Le pipeline de triage lui-même reste à
**82 ms de bout en bout** en production, mesuré sur une réclamation réelle.

Ce qui a été optimisé au passage : la publication d'événement et la mise en file
du triage sont passées hors du chemin de requête (elles sont best-effort et leur
résultat est ignoré) — p50 de 51 ms à 34 ms.

---

## Ce qui n'est pas fait

- **Ingestion email entrante.** L'envoi fonctionne (relais SMTP) ; il n'y a pas
  de boîte entrante. Les canaux réels sont `web`, `phone` et `agence`.
- **WhatsApp et push** ont l'interface complète et un corps qui journalise.
  Les activer est une classe à implémenter, pas un refactor.
- **Le mémoire** n'est pas dans ce dépôt : le périmètre demandé était le
  logiciel.

---

## Structure

```
backend/            FastAPI · Mongo/Beanie · arq · scikit-learn
  app/intelligence/ normalize · language · classify · rules · dedup · suggest · training
  app/services/     complaint · triage · assignment · sla · learning · analytics · kb
  scripts/          harvest · labeling · generate_dataset · build_dataset · train · seed
  ml_artifacts/     vectorizer + classifieur + lid.176.ftz (committés, 6,4 Mo)
  data/             train · gold · wild · synthetic · harvested (committés)
frontend/           React 19 · Vite · Tailwind v4 · TanStack Query
deploy/             manifests k3s · deploy.sh · benchmark.py
PRODUCT.md          registre, utilisateurs, principes
DESIGN.md           thème, couleurs, typographie, motion, RTL
```

---

## Déploiement

```bash
sh deploy/deploy.sh          # build, import k3s, apply, rollout, readiness
```

Namespace `reclamations`, entièrement autonome : son propre Mongo, Redis et
MinIO. Le seul élément emprunté au cluster est le identifiant du relais SMTP.
TLS via acme.sh (HTTP-01 routé par l'ingress), DNS chez Infomaniak.

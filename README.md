# Rakib · رقيب

**Plateforme de gestion des réclamations pour une banque tunisienne.**
Dépôt en ligne, catégorisation déterministe, routage vers le service compétent,
affectation par un administrateur, traitement par un agent — le tout exécuté
hors ligne, sans aucun modèle entraîné.

`Python 3.12` · `FastAPI` · `MongoDB` · `Redis` · `React 19` · `Docker`

| | |
|---|---|
| **Dépôt d'une réclamation** | 9 ms médian, 10 ms p95 — mesuré de bout en bout via nginx |
| **Catégorisation** | 0,084 ms médian, 0,111 ms p95 — 2 600 mesures |
| **Moteur** | `lexicon-v1` — 133 termes, **aucun modèle, aucun artefact** |
| **Tests** | 197, tous verts · `ruff` propre · `mypy` sur 65 fichiers |
| **Images** | serveur 469 Mo · interface 74 Mo |

---

## Sommaire

1. [Ce que fait le système](#1-ce-que-fait-le-système) · 2. [Démarrage](#2-démarrage)
· 3. [Comptes de démonstration](#3-comptes-de-démonstration)
· 4. [La catégorisation](#4-la-catégorisation) · 5. [Le routage](#5-le-routage)
· 6. [Taxonomie](#6-taxonomie) · 7. [Architecture](#7-architecture)
· 8. [API](#8-api) · 9. [RBAC](#9-rbac) · 10. [Modèle de données](#10-modèle-de-données)
· 11. [Interface](#11-interface) · 12. [Configuration](#12-configuration)
· 13. [Tests](#13-tests) · 14. [Déploiement](#14-déploiement)
· 15. [Limites connues](#15-limites-connues)

---

## 1. Ce que fait le système

Une banque reçoit des réclamations. Quelqu'un doit les lire, décider de quoi
elles parlent, les envoyer au bon service, les confier à un agent, et répondre
au client. Rakib prend en charge cette chaîne, et **s'arrête net avant la
décision** : il propose une catégorie, il ne répond jamais à personne.

Le périmètre est volontairement fermé. Sept fonctionnalités, pas une de plus :

| # | Fonctionnalité | Où |
|---|---|---|
| 1 | Inscription et connexion | `/register` · `/login` |
| 2 | Recherche et filtrage des réclamations | `/inbox` |
| 3 | Prédiction de la catégorie de réclamation | à la création, puis affichée dans le détail |
| 4 | Dépôt **sans compte** et suivi par lien personnel | `/portal` · `/portal/suivi` |
| 5 | L'administrateur affecte la réclamation à un agent | `/inbox/:id` |
| 6 | L'agent change l'état du ticket (résolu, clôturé…) | `/inbox/:id` |
| 7 | L'administrateur et l'agent écrivent au réclamant | `/inbox/:id` |

> **Aucune intelligence artificielle.** La prédiction de catégorie est un
> lexique pondéré : une liste de termes, un score, un seuil. Aucun modèle n'est
> entraîné, chargé ni appelé — ni localement, ni à distance. La décision est
> reproductible et se justifie mot par mot (§4).

> **Le système ne répond jamais au réclamant de lui-même.** Il enregistre,
> classe, route et notifie. C'est un agent qui écrit. Dans un domaine où une
> réponse engage la banque, l'automatisation s'arrête à la porte de la décision.

---

## 2. Démarrage

**Prérequis :** Docker et Docker Compose. Rien d'autre — Python, Node, MongoDB
et Redis sont fournis par les images.

```bash
git clone https://github.com/hafedh049/rakib.git && cd rakib
cp .env.example .env

docker compose up --build
# mongo · redis · api · worker · notifier · web
```

### Peupler la base

```bash
docker compose exec api python -m scripts.seed --force --count 40
```

Crée 8 services, 13 comptes et 40 réclamations bancaires rédigées en français,
en arabe et en derja, puis exécute la catégorisation sur chacune. L'âge d'une
réclamation suit son statut : le tableau ouvre sur un mélange réaliste et non
sur quarante lignes identiques.

### Accéder

| Surface | URL locale | Accès |
|---|---|---|
| Portail public | `localhost:5173/portal` | Anonyme |
| Console | `localhost:5173/login` | `admin@rakib.tn` / `Rakib2026!` |
| API (via nginx) | `localhost:5173/api/v1` | JWT |
| API (directe) | `localhost:8000/api/v1` | JWT |
| OpenAPI | `localhost:8000/docs` | Ouvert hors production |
| Santé | `localhost:8000/health/ready` | Ouvert |

L'interface et l'API partagent une seule origine : nginx sert le bundle et
relaie `/api/`. Aucune configuration CORS n'est donc nécessaire.

---

## 3. Comptes de démonstration

Mot de passe unique pour tous : **`Rakib2026!`**

| Compte | Rôle | Service |
|---|---|---|
| `admin@rakib.tn` | admin | — |
| `superviseur1@rakib.tn` · `superviseur2@rakib.tn` | superviseur | — |
| `agent.mon1@rakib.tn` · `agent.mon2@rakib.tn` | agent | MONETIQUE |
| `agent.ope1@rakib.tn` · `agent.ope2@rakib.tn` | agent | OPERATIONS |
| `agent.cre1@rakib.tn` | agent | CREDITS |
| `agent.rc1@rakib.tn` · `agent.rc2@rakib.tn` | agent | RELATION_CLIENT |
| `agent.dig1@rakib.tn` | agent | DIGITAL |
| `agent.int1@rakib.tn` | agent | INTERNATIONAL |
| `agent.frd1@rakib.tn` | agent | CONFORMITE_FRAUDE |

**La démonstration qui compte :** connectez-vous en `agent.mon1@rakib.tn`, puis
en `agent.ope1@rakib.tn`. Les deux ouvrent le même écran `/inbox`, aucun des
deux ne voit les réclamations de l'autre. Le cloisonnement n'est pas un filtre
d'affichage : il est injecté dans la requête Mongo (§9).

---

## 4. La catégorisation

### Le principe

Chaque catégorie possède une liste de termes qui la nomment sans ambiguïté —
« chéquier », « allocation touristique », « opération non autorisée ». Le texte
de la réclamation est normalisé, les termes sont cherchés dedans, chaque
correspondance rapporte un poids, et la catégorie qui totalise le plus l'emporte
— **à condition de franchir trois seuils**. Sinon le système s'abstient et la
réclamation part en tri humain.

```
texte brut
  │
  ├─ 1. normalisation   minuscules, signatures retirées, téléphones et courriels
  │                     masqués, arabizi translittéré, accents latins repliés
  ├─ 2. langue          fr · ar · ar-tn (derja) · en
  ├─ 3. classification  lexique pondéré, remise IDF, abstention explicite
  └─ 4. routage         catégorie → service, ou mots-clés → service
```

### Les seuils, et pourquoi ils existent

| Seuil | Valeur | Motif d'abstention si non atteint |
|---|---|---|
| Score brut minimal | 2.0 | `insufficient_evidence` |
| Part de preuve du gagnant | 40 % | `evidence_too_spread` |
| Avance sur la deuxième | ×1.3 | `margin_too_narrow` |
| Aucun terme reconnu | — | `no_signal` |

Un terme réclamé par plusieurs catégories pèse moins qu'un terme discriminant
(fréquence inverse de catégorie). Sans cette remise, un mot banal partagé par
quatre catégories noie le mot utile qui n'en désigne qu'une.

> **« Confiance » n'est pas une probabilité.** Le pourcentage affiché est une
> *part de preuve* : la fraction du poids total détenue par la catégorie
> gagnante. Il n'est pas calibré et ne prétend pas l'être. De toute façon,
> l'écran montre à côté **les termes exacts qui ont décidé** — une information
> plus utile qu'un pourcentage, et sur laquelle un agent peut argumenter.

### Ce que ça vaut réellement

Mesuré contre un jeu de référence de 130 cas écrits à la main, indépendamment du
lexique, et incluant volontairement 16 textes qui n'ont pas de bonne réponse :

```
$ docker compose -f docker-compose.test.yml run --rm tests python -m scripts.evaluate

lexicon: 133 terms across 12 categories

=== GOLD (authored, independent)  (n=114) ===
macro-F1 0.495   accuracy 0.368
abstained on 63/114 (55%)
when it committed: 42/51 correct (82%)

=== unclassifiable  (n=16) ===
correctly routed to human triage: 94%
```

Ces chiffres sont donnés tels quels, sans mise en scène :

- **Il s'abstient plus d'une fois sur deux.** C'est le comportement voulu, pas
  une panne. Un texte formulé hors du vocabulaire marque zéro et part chez un
  agent — qui l'aurait lu de toute façon.
- **Quand il tranche, il a raison 4 fois sur 5.** C'est le seul chiffre qui
  compte en exploitation : une mauvaise catégorie affichée avec assurance coûte
  plus de temps à un agent que pas de catégorie du tout.
- **94 % des textes inclassables sont correctement envoyés en tri humain.**
- L'exactitude globale de 0,368 est basse *parce que* l'abstention y est comptée
  comme une erreur. Un modèle entraîné ferait mieux sur cette métrique. Il ne
  serait pas explicable terme par terme, et le cahier des charges l'interdit.

### Le repli des accents

`text` conserve ses accents — il est lu par des humains. `indexable` les replie,
parce que tous les termes du lexique sont écrits sans accent.

Sans ce repli, « chèque » ne correspondait jamais à « cheque » : **une
réclamation rédigée en français correct échouait à se catégoriser, alors que la
même phrase tapée négligemment fonctionnait.** Le repli est restreint aux
marques combinantes latines — les points-voyelles arabes sont traités séparément
et ne doivent pas être touchés ici.

### Enrichir le vocabulaire

Ajouter une tournure au lexique, c'est ajouter une chaîne de caractères dans
[`terms.py`](backend/app/intelligence/lexicon/terms.py) et redémarrer. Pas de
réentraînement, pas de jeu de données, pas d'artefact à versionner. C'est le
principal avantage pratique de cette approche, et la raison pour laquelle la
liste entière se lit en une minute.

---

## 5. Le routage

Une réclamation catégorisée va au service qui possède cette catégorie. Une
réclamation **non** catégorisée n'est pas abandonnée : les mots-clés de chaque
service sont cherchés dans le texte, avec la même remise IDF, et le meilleur
score l'emporte. Si rien ne ressort, elle atterrit dans `GENERAL`.

La réclamation arrive donc toujours dans une file de service, **jamais
directement chez un agent**. Le passage de la file à une personne est une
décision humaine : c'est la fonctionnalité 5, et c'est délibérément le seul
chemin.

---

## 6. Taxonomie

12 catégories, 8 services. La correspondance est dérivée, jamais saisie deux
fois : [`taxonomy.py`](backend/app/domain/taxonomy.py) lève une erreur à
l'import si une catégorie n'appartient à aucun service.

| Catégorie | Libellé | Service |
|---|---|---|
| `CARTE_BANCAIRE` | Carte bancaire | MONETIQUE |
| `DAB_GAB` | Distributeur (DAB/GAB) | MONETIQUE |
| `PAIEMENT_TPE_ECOMMERCE` | Paiement TPE et e-commerce | MONETIQUE |
| `VIREMENT_PRELEVEMENT` | Virement et prélèvement | OPERATIONS |
| `CHEQUE_EFFET` | Chèque et effet | OPERATIONS |
| `CREDIT_FINANCEMENT` | Crédit et financement | CREDITS |
| `COMPTE_GESTION` | Gestion du compte | RELATION_CLIENT |
| `FRAIS_COMMISSIONS` | Frais et commissions | RELATION_CLIENT |
| `AGENCE_QUALITE_SERVICE` | Agence et qualité de service | RELATION_CLIENT |
| `BANQUE_DIGITALE` | Banque digitale | DIGITAL |
| `OPERATIONS_INTERNATIONALES` | Opérations internationales | INTERNATIONAL |
| `FRAUDE_OPERATION_NON_AUTORISEE` | Fraude / opération non autorisée | CONFORMITE_FRAUDE |

Le huitième service, `GENERAL`, ne possède aucune catégorie : c'est la file de
secours.

**Il n'y a pas de catégorie « Autre ».** Une classe fourre-tout absorbe tous les
cas difficiles et détruit sa propre précision ; une réclamation inclassable
passe par l'abstention, où une personne décide.

### Statuts et canaux

`new` → `triaged` → `assigned` → `in_progress` → `pending_claimant` →
`resolved` · `closed` · `rejected`

Canaux : `web` · `email` · `agence` · `phone` · `courrier`. Seul `web` est
public ; les autres décrivent une réclamation saisie par un agent.

---

## 7. Architecture

```
backend/
  app/
    domain/            connaissance métier pure, sans dépendance technique
      taxonomy.py        12 catégories, 8 services, la correspondance
    intelligence/      analyse — n'importe ni api/ ni models/
      text/              normalisation, repli des accents, langue, recherche de termes
      lexicon/           termes pondérés + classifieur déterministe
      engines/           lexicon.py
      ports.py           l'interface TriageEngine
    models/            documents Beanie
    services/          orchestration métier
    api/v1/            routes HTTP
    events/            bus Redis Streams + abonnements des notificateurs
    notifiers/         courriel · SSE
    workers/           arq : la tâche de catégorisation
  scripts/             seed · seed_data · gold · evaluate
  tests/               8 fichiers de test, 197 cas
frontend/
  src/routes/          écrans
  src/components/      AppShell · PortalLayout · Brandmark · Toasts · ui
  src/i18n/            fr.ts · ar.ts
  src/lib/             api · auth · sse · types
deploy/
  k8s/rakib.yaml       manifestes
  deploy.sh            build, import, applique, vérifie
  visual_check.mjs     captures + erreurs console (Playwright)
```

> **La règle de dépendance** — `intelligence/` n'importe ni `api/` ni `models/` :
> seules des structures de données simples franchissent la frontière, définies
> dans [`ports.py`](backend/app/intelligence/ports.py). C'est cette séparation
> qui a permis de changer de secteur, puis de moteur, sans toucher au reste.

### Pourquoi un worker

`POST /complaints` répond en 9 ms parce qu'il n'attend pas la catégorisation :
il pousse un travail dans une file arq et rend la main. Le worker analyse et
écrit le résultat. Le client, lui, a déjà sa référence et son lien de suivi.

Les écritures du worker sont ciblées (`$set` / `$push`), jamais un `save()` de
document entier : le worker et un agent peuvent écrire sur la même réclamation à
la même seconde, et un enregistrement complet depuis une copie périmée effaçait
les messages ajoutés entre-temps.

---

## 8. API

Toutes les routes sont préfixées par `/api/v1`.

### Authentification

| Méthode | Route | Accès |
|---|---|---|
| `POST` | `/auth/register` | public — crée un compte réclamant |
| `POST` | `/auth/login` | public — rend un couple de jetons |
| `POST` | `/auth/refresh` | public — renouvelle l'accès, fait tourner le jeton |
| `POST` | `/auth/logout` | authentifié — révoque le rafraîchissement |
| `GET` | `/auth/me` | authentifié |

### Réclamations

| Méthode | Route | Rôle minimal |
|---|---|---|
| `POST` | `/complaints` | **public** — dépôt, avec ou sans compte |
| `GET` | `/complaints/track?token=` | **public** — suivi par lien signé |
| `GET` | `/complaints` | authentifié — liste filtrée, paginée par curseur |
| `GET` | `/complaints/{id}` | authentifié — détail, cloisonné par rôle |
| `PATCH` | `/complaints/{id}` | agent — statut, catégorie, service, agent, VIP |
| `POST` | `/complaints/{id}/messages` | authentifié — message ou note interne |
| `POST` | `/complaints/{id}/resolve` | agent — clôt avec une résolution |
| `POST` | `/complaints/{id}/retriage` | superviseur — relance l'analyse |
| `GET` | `/complaints/{id}/analysis` | agent — catégorie, termes, alternatives |

Filtres de `GET /complaints` : `status` (répétable), `category`, `department`,
`agent_id`, `q` (recherche plein texte), `date_from`, `date_to`,
`needs_human_triage`, `unassigned`, `cursor`, `limit`.

> `GET /complaints/track` prend un jeton signé, **pas** une référence. La
> référence est séquentielle : un suivi par référence laisserait n'importe qui
> énumérer toutes les réclamations de la banque.

### Administration

| Méthode | Route | Rôle minimal |
|---|---|---|
| `GET` | `/users/me` | authentifié |
| `GET` | `/users` | superviseur |
| `POST` | `/users` | admin — crée un membre du personnel |
| `PATCH` | `/users/{id}` | admin — rôle, service, activation |
| `GET` | `/departments` | agent |
| `POST` · `PATCH` · `DELETE` | `/departments`… | admin |

### Temps réel et santé

| Méthode | Route | Rôle minimal |
|---|---|---|
| `GET` | `/events/stream` | agent — SSE, filtré par rôle |
| `GET` | `/health` · `/health/ready` | public |

Le flux est consommé en `fetch` + lecteur de flux, et non en `EventSource` :
celui-ci ne permet pas d'envoyer un en-tête `Authorization`.

Événements diffusés : `complaint.created`, `complaint.triaged`,
`complaint.assigned`, `complaint.updated`, `complaint.replied`,
`complaint.resolved`, et `triage.corrected` — ce dernier réservé aux
superviseurs.

---

## 9. RBAC

Quatre rôles, ordonnés : `claimant` < `agent` < `supervisor` < `admin`.
`require_role(agent)` admet donc aussi les superviseurs et les administrateurs.

| Rôle | Lecture des réclamations | Écriture |
|---|---|---|
| `claimant` | les siennes | déposer, répondre sur les siennes |
| `agent` | celles de **son** service, plus celles qui lui sont affectées | statut, catégorie, messages, résolution |
| `supervisor` | toutes | + affecter un agent, relancer l'analyse |
| `admin` | toutes | + comptes et services |

**Le cloisonnement est un filtre Mongo, jamais un tri après lecture.**
`department_scope(user)` rend un filtre fusionné dans la requête elle-même :

```python
# agent rattaché à un service
{"$or": [{"assignment.department_id": user.department_id},
         {"assignment.agent_id": user.id}]}
```

Un agent ne peut donc pas paginer jusqu'aux réclamations d'un autre service :
elles ne sont jamais lues. Et une réclamation hors périmètre rend **404, pas
403** — un 403 confirmerait qu'elle existe.

---

## 10. Modèle de données

Trois collections principales — `complaints`, `users`, `departments` — plus
`counters` pour les références et `refresh_tokens` pour les sessions.

```
Complaint
  ref                REC-2026-00042, séquentiel et unique
  channel            web · email · agence · phone · courrier
  claimant           nom, courriel, téléphone, référence client, VIP
  subject, body      le texte tel qu'écrit
  normalized_text    la forme canonique, ce sur quoi porte la recherche
  analysis           catégorie, part de preuve, alternatives, langue,
                     mots-clés, termes déclenchés, motif d'abstention,
                     moteur, version, latence
  assignment         service, agent, date, méthode
  status             new → … → resolved · closed · rejected
  triage_state       pending · done · failed · manual
  messages[]         auteur, corps, interne ou non
  timeline[]         qui a fait quoi, quand — humain ou moteur
  corrected          un humain a changé la catégorie ou le service
```

Index notables : `ref` unique ; `(agent, statut)` et `(service, statut)` pour les
files ; `(created_at, _id)` pour la pagination par curseur — il doit correspondre
exactement au tri ; et un index texte sur `subject`, `body` et `normalized_text`
avec `default_language="none"`, parce qu'un radicaliseur français est inutile sur
de l'arabe et que Mongo n'autorise **qu'un seul** index texte par collection.

---

## 11. Interface

Deux registres sur un seul système de tokens.

**Le portail** (`/portal`) est public, clair, bilingue français / arabe avec un
vrai RTL — pas un `dir="rtl"` posé sur une mise en page pensée pour la gauche.
Il vise un téléphone sur une connexion médiocre : la console est chargée à la
demande, un réclamant ne télécharge jamais l'écran des agents.

**La console** (`/inbox`) est dense et en français : c'est un outil de travail.

| Écran | Route | Accès |
|---|---|---|
| Dépôt | `/portal` | anonyme |
| Suivi par lien | `/portal/suivi?token=` | anonyme |
| Mes réclamations | `/portal/mes-reclamations` | réclamant connecté |
| Connexion · inscription | `/login` · `/register` | public |
| File de travail | `/inbox` | agent |
| Détail | `/inbox/:id` | agent |
| Comptes | `/admin/users` | admin |
| Services | `/admin/departments` | admin |

Le thème suit trois états : `:root` pour le clair, `prefers-color-scheme` pour
le réglage système, `[data-theme]` pour un choix explicite. Les couleurs sont
définies en OKLCH.

---

## 12. Configuration

Tout est dans `.env`, copié depuis `.env.example`.

| Variable | Défaut | Rôle |
|---|---|---|
| `APP_NAME` | `Rakib` | Nom affiché |
| `ENVIRONMENT` | `development` | `development` · `staging` · `production` · `test` |
| `LOG_LEVEL` | `INFO` | Journalisation structurée (structlog) |
| `MONGO_URI` | `mongodb://mongo:27017/reclamations` | Base |
| `REDIS_URL` | `redis://redis:6379/0` | File de travaux et flux d'événements |
| `JWT_SECRET` | `change-me-in-production` | **À changer.** Signature des sessions |
| `JWT_ACCESS_TTL_MIN` | `15` | Durée du jeton d'accès |
| `JWT_REFRESH_TTL_DAYS` | `7` | Durée du jeton de rafraîchissement |
| `TRACKING_TOKEN_SECRET` | `change-me-too` | **À changer.** Signature des liens de suivi |
| `TRACKING_TOKEN_TTL_DAYS` | `365` | Validité d'un lien de suivi |
| `SMTP_HOST` … `SMTP_FROM` | vide | Relais sortant ; vide = aucun envoi |
| `FRONTEND_URL` · `PUBLIC_URL` | `localhost:5173` | Base des liens envoyés par courriel |

> Ces deux secrets ne doivent **pas** être régénérés à chaque déploiement :
> changer `JWT_SECRET` déconnecte tout le monde, et changer
> `TRACKING_TOKEN_SECRET` invalide tous les liens déjà remis à des clients. Le
> script de déploiement les génère une fois, puis les laisse tranquilles.

Le jeton de suivi est signé avec un secret **différent** de celui des sessions :
un lien de suivi qui fuite ne doit jamais pouvoir devenir une session.

---

## 13. Tests

```bash
docker compose -f docker-compose.test.yml run --rm tests            # 197 tests
docker compose -f docker-compose.test.yml run --rm tests \
  sh -c "ruff check app tests scripts && mypy app"                  # lint + types
```

| Fichier | Ce qu'il verrouille |
|---|---|
| `test_auth.py` | Inscription, connexion, rotation du rafraîchissement, révocation |
| `test_complaints.py` | Cycle de vie, dépôt anonyme, affectation, messages, résolution |
| `test_rbac.py` | Le filtre de cloisonnement, rôle par rôle |
| `test_security.py` | Jetons de suivi : falsification, portée, expiration |
| `test_normalize.py` | Normalisation, arabizi, repli des accents |
| `test_language_and_engine.py` | Détection de langue, sortie du moteur |
| `test_triage_pipeline.py` | Chaîne complète, abstention, explicabilité |
| `test_events.py` | Bus, abonnements, filtrage SSE par rôle, courriels |

Les tests tournent contre un vrai MongoDB et un vrai Redis, pas des doublures :
les bogues qui ont réellement coûté du temps sur ce projet — une course à
l'insertion, une écriture perdue, un index texte en double — sont tous
invisibles sans base réelle.

Vérifier la catégorisation contre le jeu de référence :

```bash
docker compose -f docker-compose.test.yml run --rm tests python -m scripts.evaluate
```

---

## 14. Déploiement

L'environnement reproductible est `docker-compose.yml` — six conteneurs, aucun
accès réseau au-delà du téléchargement des images de base.

L'image serveur est construite en plusieurs étapes, n'installe que des roues
précompilées (`PIP_ONLY_BINARY=:all:`) et tourne sous un utilisateur non
privilégié. `deploy/k8s/rakib.yaml` décrit le même système sur k3s, derrière
Traefik et cert-manager ; `deploy/deploy.sh` construit, importe, applique et
vérifie.

L'API est plafonnée à 2 vCPU / 4 Go dans les deux environnements : la contrainte
matérielle annoncée est appliquée, pas seulement affirmée.

---

## 15. Limites connues

Ce que le système ne fait pas, et qu'il ne faut pas lui prêter :

- **Il s'abstient sur 55 % des cas du jeu de référence.** Le vocabulaire compte
  133 termes ; une tournure inhabituelle ne déclenche rien. C'est assumé (§4),
  pas contourné.
- **Aucune notification n'est envoyée sans SMTP.** `SMTP_HOST` vide fait tourner
  le système normalement, sans courriel — pratique en démonstration, à ne pas
  confondre avec un envoi réussi.
- **Pas de pièces jointes.** Un réclamant décrit son problème en texte.
- **Pas de délais réglementaires ni d'échéancier.** Les statuts changent parce
  qu'une personne les change.
- **Pas de tableau de bord ni de statistiques.** La file, ses filtres et la
  recherche plein texte sont les seuls outils de lecture.
- **Pas de détection de doublons.** Deux réclamations identiques du même client
  sont deux réclamations.
- **401 au premier appel après un rechargement de page.** Le jeton d'accès n'est
  gardé qu'en mémoire, par choix de sécurité ; seul le jeton de rafraîchissement
  survit. La session se rétablit toute seule, mais le 401 reste visible dans la
  console du navigateur.
- **La marque officielle n'est pas versionnée.** `Brandmark` charge
  `public/brand/uib.svg` dès que le fichier y est déposé, et se rabat sur un
  monogramme sinon.
- **Un seul exemplaire de chaque service.** Le dimensionnement n'a pas été
  éprouvé au-delà de l'enveloppe 2 vCPU / 4 Go.

---

## Licence et mentions

Projet de fin d'études. **Plateforme de démonstration, sans affiliation
officielle avec l'établissement dont l'identité visuelle est utilisée.** Aucune
réclamation déposée ici n'est traitée par une banque ; les noms, comptes et
réclamations de démonstration sont fictifs, et les identifiants n'ont cours que
sur cet environnement.

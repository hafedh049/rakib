# Rakib · رقيب

**Plateforme de gestion des réclamations pour une banque tunisienne.**
Tri déterministe, délais conformes à la circulaire BCT n°2022-08, exécution
intégralement hors ligne.

`Python 3.12` · `FastAPI` · `MongoDB` · `Redis` · `React 19` · `k3s`

| | |
|---|---|
| **p95 de bout en bout** | 58 ms (cible 100) |
| **Analyse complète** | 4 ms, six étapes |
| **Image conteneur** | 469 Mo (cible 800) |
| **Couverture du cœur métier** | 88 % |
| **Moteur** | `lexicon-v1` — 397 termes, aucun modèle entraîné |

---

## Sommaire

1. [Aperçu](#1-aperçu) · 2. [Démarrage](#2-démarrage) · 3. [Configuration](#3-configuration)
· 4. [Structure](#4-structure-du-dépôt) · 5. [Pipeline](#5-le-pipeline)
· 6. [Lexique](#6-le-lexique) · 7. [Règles](#7-les-27-règles)
· 8. [Taxonomie](#8-taxonomie) · 9. [Délais](#9-délais-et-calendrier)
· 10. [Conformité BCT](#10-conformité-bct) · 11. [Données](#11-modèle-de-données)
· 12. [API](#12-référence-api) · 13. [RBAC](#13-rbac) · 14. [Interface](#14-interface)
· 15. [Comptes](#15-comptes-de-démonstration) · 16. [Tests](#16-tests)
· 17. [Déploiement](#17-déploiement) · 18. [Exploitation](#18-exploitation)
· 19. [Problèmes connus](#19-problèmes-connus)

---

## 1. Aperçu

Une banque reçoit des réclamations par formulaire, courriel, téléphone, courrier
et guichet. Un agent lit chacune et tranche quatre questions : **de quoi
s'agit-il, quelle urgence, quel service est compétent, et l'avons-nous déjà
reçue ?** C'est lent, incohérent d'un agent à l'autre, et des réclamations
dépassent leur délai *légal* pendant qu'elles attendent d'être lues.

Rakib prend ces quatre décisions en quelques millisecondes, sur la machine
locale, sans aucun appel réseau. Puis l'humain reprend la main.

> **Principe non négociable** — le système ne répond **jamais** au réclamant de
> lui-même. Il prépare, propose et alerte ; c'est un agent qui envoie. Dans un
> domaine où une réponse engage la banque, l'automatisation s'arrête à la porte
> de la décision.

### Contraintes structurantes

| Contrainte | Conséquence |
|---|---|
| Hors ligne intégral | Aucun appel réseau à l'inférence, aucune police servie par CDN, aucune dépendance tierce |
| Aucun modèle entraîné | Catégorisation par lexique pondéré ; déterminisme et traçabilité complets |
| Matériel modeste | Bi-cœur, 4 Go, sans carte graphique |
| Conformité BCT 2022-08 | Délais en jours ouvrables, registre annexe 1, déclaration ROGS760 |
| Bilingue FR/AR + derja | RTL réel côté portail, détection de la derja latine |
| Jamais de réponse automatique | L'automatisation s'arrête à la décision |

### Pile technique

| Couche | Technologies |
|---|---|
| Serveur | Python 3.12 · FastAPI 0.115 · Uvicorn 0.32 · Pydantic 2.9 |
| Données | MongoDB 7 · Beanie 1.27 · Motor 3.6 |
| Tâches | Redis 7 · arq 0.26 (files, cron, Streams) |
| Recherche | rank-bm25 0.2 · RapidFuzz 3.10 |
| Sécurité | PyJWT 2.9 · argon2-cffi 23.1 |
| Stockage | MinIO (S3) via aioboto3 13.2 |
| Interface | React 19 · TypeScript 5.7 · Vite 6 · Tailwind 4 · TanStack Query 5 |
| Déploiement | Docker multi-étapes · k3s · Traefik · cert-manager |

---

## 2. Démarrage

**Prérequis :** Docker et Docker Compose. Rien d'autre — Python, Node, MongoDB
et Redis sont fournis par les images.

```bash
git clone https://github.com/hafedh049/rakib.git && cd rakib
cp .env.example .env

docker compose up --build
# web · api · worker · notifier · mongo · redis · minio
```

### Peupler

```bash
docker compose exec api python -m scripts.seed --force --count 60
```

Crée 8 services, 13 comptes et 60 réclamations bancaires en français, arabe et
derja, puis exécute le pipeline sur chacune. L'âge d'une réclamation suit son
statut, de sorte que le tableau de bord ouvre sur un mélange réaliste et non sur
soixante lignes rouges.

### Accéder

| Surface | URL locale | Accès |
|---|---|---|
| Portail public | `localhost:5173/portal` | Anonyme |
| Console agents | `localhost:5173/login` | `admin@rakib.tn` / `Rakib2026!` |
| API (via nginx) | `localhost:5173/api/v1` | JWT |
| API (directe) | `localhost:8000/api/v1` | JWT |
| OpenAPI | `localhost:8000/docs` | Ouvert hors production |
| Santé | `localhost:8000/health/ready` | Ouvert |

---

## 3. Configuration

### Application

| Variable | Défaut | Rôle |
|---|---|---|
| `APP_NAME` | `Rakib` | Nom affiché |
| `ENVIRONMENT` | `development` | `development` · `staging` · `production` · `test` |
| `LOG_LEVEL` | `INFO` | Journalisation structurée (structlog) |
| `API_PREFIX` | `/api/v1` | Préfixe des routes |
| `FRONTEND_URL` | `localhost:5173` | Liens dans les courriels |
| `PUBLIC_URL` | `localhost:5173` | Base des liens de suivi |

### Infrastructure

| Variable | Défaut |
|---|---|
| `MONGO_URI` | `mongodb://localhost:27017/reclamations` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `S3_ENDPOINT` | `http://localhost:9000` |
| `S3_BUCKET` | `reclamations` |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | `rakib` / `rakib-dev-secret` |
| `MAX_ATTACHMENT_MB` | `10` |

### À changer impérativement en production

| Variable | Défaut | Pourquoi |
|---|---|---|
| `JWT_SECRET` | `change-me-in-production` | Signature des jetons de session |
| `TRACKING_TOKEN_SECRET` | `change-me-too` | Signature des liens de suivi remis aux réclamants |
| `S3_SECRET_KEY` | `rakib-dev-secret` | Accès aux pièces jointes |

> Ces deux secrets ne doivent **pas** être tournés à chaque déploiement :
> changer `JWT_SECRET` déconnecte tout le monde, et changer
> `TRACKING_TOKEN_SECRET` invalide tous les liens de suivi déjà remis à des
> clients. Le script de déploiement les génère une fois puis les laisse
> tranquilles.

### Authentification

| Variable | Défaut | Rôle |
|---|---|---|
| `JWT_ALGORITHM` | `HS256` | Algorithme de signature |
| `JWT_ACCESS_TTL_MIN` | `15` | Durée du jeton d'accès (minutes) |
| `JWT_REFRESH_TTL_DAYS` | `7` | Durée du jeton de rafraîchissement (jours) |
| `TRACKING_TOKEN_TTL_DAYS` | `365` | Validité d'un lien de suivi anonyme |

### Moteur et seuils

| Variable | Défaut | Rôle |
|---|---|---|
| `TRIAGE_BACKEND` | `lexicon` | `lexicon` ou `rules` (routage seul) |
| `CATEGORY_CONFIDENCE_THRESHOLD` | `0.55` | Seuil de renvoi en triage humain |
| `AMBIGUITY_MARGIN` | `0.15` | Écart minimal avec la deuxième catégorie |
| `DEDUP_AUTO_THRESHOLD` | `0.82` | Liaison automatique d'un doublon |
| `DEDUP_SUGGEST_THRESHOLD` | `0.65` | Simple suggestion à l'agent |
| `DEDUP_CROSS_CLAIMANT_THRESHOLD` | `0.90` | Seuil relevé entre réclamants différents |

### Délais et courriel

| Variable | Défaut | Rôle |
|---|---|---|
| `SLA_HOURS_P1` … `P4` | `4` / `24` / `72` / `168` | Objectifs internes par priorité (heures) |
| `SLA_BUSINESS_HOURS` | `false` | Horloge ouvrée pour l'objectif interne |
| `SLA_TIMEZONE` | `Africa/Tunis` | Fuseau du calendrier ouvré |
| `SMTP_HOST` / `SMTP_PORT` | — / `587` | Relais sortant ; vide = pas d'envoi |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | — | Identifiants du relais |
| `SMTP_FROM` | — | Expéditeur |
| `SMTP_STARTTLS` | `true` | Chiffrement de la session |

Le plafond légal de l'article 8 **ne dépend d'aucune variable**. Il est en dur
dans `app/domain/bct.py`, avec l'article qui le justifie : une obligation
réglementaire n'est pas un réglage.

---

## 4. Structure du dépôt

```
backend/
  app/
    domain/            connaissance métier pure, sans dépendance technique
      taxonomy.py        12 catégories, 8 services, la correspondance
      bct.py             circulaire 2022-08 : délais, annexes, objets
      calendar_tn.py     jours ouvrables tunisiens, Ramadan, fêtes lunaires
      kb_seed.py         18 articles de base de connaissances FR/AR
    intelligence/      analyse — n'importe ni api/ ni models/
      text/              normalisation, repli des accents, langue
      lexicon/           termes pondérés + classifieur déterministe
      rules/             moteur de règles, sous-catégories, périmètre art. 2
      dedup/             BM25 + correspondance approximative
      engines/           lexicon.py (défaut) · rules_only.py
      ports.py           l'interface TriageEngine
      pipeline.py        l'enchaînement des six étapes
    models/            documents Beanie
    services/          orchestration métier
    api/v1/            routes HTTP
    workers/           arq : tâches de fond et cron
  scripts/             seed · seed_data · gold · evaluate
  tests/               15 fichiers
frontend/
  src/routes/          écrans
  src/components/      AppShell · PortalLayout · Brandmark · Toasts · ui
  src/i18n/            fr.ts · ar.ts
  src/lib/             api · auth · sse · types
deploy/
  k8s/rakib.yaml       manifestes
  deploy.sh            build, import k3s, applique, vérifie
  benchmark.py         charge, avec nettoyage
  visual_check.mjs     captures + erreurs console (Playwright)
```

> **La règle de dépendance** — `intelligence/` n'importe ni `api/` ni `models/` :
> seules des structures de données simples franchissent la frontière, définies
> dans `ports.py`. C'est cette séparation qui a permis de changer de secteur puis
> de moteur sans toucher au reste, et elle mérite d'être préservée.

---

## 5. Le pipeline

Six étapes, dans cet ordre, chacune consommant la précédente.

| # | Étape | Ce qu'elle fait | Durée |
|---|---|---|---|
| 1 | `normalize` | Retire signatures et historiques cités ; masque téléphones, courriels et références en jetons ; replie les accents latins et les variantes arabes ; translittère l'arabizi en conservant les deux graphies | 0,42 ms |
| 2 | `language` | `fr` · `ar` · `ar-tn` · `en`. L'arabe par ratio de script, la derja par motifs arabizi et marqueurs, le reste par mots outils | 0,14 ms |
| 3 | `classify` | Lexique pondéré, 397 termes ; abstention explicite en dessous des seuils | 0,67 ms |
| 4 | `rules` | 27 règles pondérées → score → P1/P2/P3 ; chaque déclenchement conserve les mots exacts | 0,93 ms |
| 5 | `dedup` | BM25 et correspondance approximative sur les réclamations récentes ; seuil relevé entre réclamants différents | 2,0 ms |
| 6 | `decide` | Routage vers le service, objectif interne, plafond légal, affectation | < 0,1 ms |

### Le repli des accents, et pourquoi il compte

`text` conserve ses accents — il est lu par des humains. `indexable` les replie,
parce que tous les lexiques et termes de règles sont écrits sans accent.

Sans ce repli, « chèque » ne correspondait jamais à « cheque » : **une
réclamation rédigée en français correct échouait à se catégoriser, alors que la
même phrase tapée négligemment fonctionnait.** Le repli est restreint aux
marques combinantes latines — les points-voyelles arabes sont traités séparément
et ne doivent pas être retouchés ici.

---

## 6. Le lexique

397 termes répartis sur 12 catégories, en deux niveaux :

- **Décisif** (poids 3,0) — nomme le produit ou l'incident : « chéquier »,
  « allocation touristique ».
- **Appui** (poids 1,0) — vocabulaire de sous-catégorie, bien plus partagé :
  « deux fois » sert aux cartes, aux distributeurs, aux paiements et au crédit.

Chaque terme est ensuite pondéré par une **fréquence inverse de catégorie** : un
terme réclamé par plusieurs catégories pèse moins qu'un terme discriminant —
même principe que le routage par service, et même raison, sinon le terme banal
noie le terme utile.

### Conditions pour qu'une catégorie soit retenue

| Seuil | Valeur | Motif d'abstention si non atteint |
|---|---|---|
| Score brut minimal | 2.0 | `insufficient_evidence` |
| Part de preuve du gagnant | 40 % | `evidence_too_spread` |
| Avance sur le suivant | ×1.3 | `margin_too_narrow` |
| Aucun terme reconnu | — | `no_signal` |

> **La « confiance » n'est pas une probabilité.** Le chiffre affiché est une
> *part de preuve* : la fraction du poids total détenue par la catégorie
> gagnante. Il n'est pas calibré et ne prétend pas l'être. La sortie du moteur
> porte de toute façon les termes exacts qui ont décidé — information plus utile
> qu'un pourcentage.

---

## 7. Les 27 règles

Toutes modifiables depuis `/admin/rules`, sans redéploiement. Un poids négatif
abaisse la priorité.

| Code | Type | Poids | Déclencheur |
|---|---|---:|---|
| `FRAUDE_SUSPECTEE_FR` | lexique | +55 | Opération non autorisée, compte piraté |
| `FRAUDE_SUSPECTEE_AR` | lexique | +55 | Idem, écriture arabe |
| `FRAUDE_SUSPECTEE_TN` | lexique | +55 | Idem, derja |
| `MEDIATEUR_BANCAIRE_FR` | lexique | +35 | Le client évoque le médiateur |
| `MEDIATEUR_BANCAIRE_AR` | lexique | +35 | Idem, écriture arabe |
| `LEGAL_LEXICON_FR` | lexique | +30 | Avocat, plainte, tribunal |
| `LEGAL_LEXICON_AR` | lexique | +30 | Idem, écriture arabe |
| `VIP_CLAIMANT` | champ | +25 | Compte entreprise ou client signalé |
| `CHURN_LEXICON_FR` | lexique | +20 | Menace de clôture ou de départ |
| `CHURN_LEXICON_AR` | lexique | +20 | Idem, arabe et derja |
| `INCIDENT_COLLECTIF` | lexique | +20 | Plusieurs clients touchés, agence entière |
| `REPEAT_CLAIMANT_30D` | historique | +20 | Réclamations répétées sur 30 jours |
| `URGENCY_LEXICON_FR` | lexique | +15 | Vocabulaire d'urgence |
| `URGENCY_LEXICON_AR` | lexique | +15 | Idem, écriture arabe |
| `URGENCY_LEXICON_TN` | lexique | +15 | Idem, derja |
| `MONTANT_ELEVE` | regex | +12 | Montant à quatre chiffres ou plus |
| `DURATION_WEEKS` | regex | +12 | Problème persistant en semaines ou mois |
| `PROFANITY` | lexique | +10 | Propos agressifs |
| `MULTIPLE_OPEN` | historique | +10 | Plusieurs dossiers ouverts |
| `AMOUNT_IN_DINARS` | regex | +8 | Montant contesté explicite |
| `SHOUTING` | champ | +8 | Message en majuscules |
| `OPERATION_REFERENCE` | regex | +5 | Référence d'opération citée |
| `HAS_ATTACHMENT` | champ | +5 | Pièce justificative fournie |
| `DETAILED_REPORT` | longueur | +5 | Description circonstanciée |
| `EXCLAMATION_STORM` | champ | +5 | Ponctuation excessive |
| `CATEGORY_WEIGHTS` | catégorie | ×1 | Socle propre à chaque catégorie |
| `VERY_SHORT` | longueur | −8 | Message trop court pour être actionnable |

La fraude domine volontairement le barème : c'est la seule catégorie où le
préjudice *continue de croître* tant que personne n'agit. Le médiateur vient
juste après, parce qu'un client qui l'évoque est déjà au bord d'une procédure
formelle.

---

## 8. Taxonomie

12 catégories, 8 services. Changer de secteur d'activité, c'est remplacer
`taxonomy.py` — rien au-dessus ne code en dur la banque.

| Catégorie | Libellé | العربية | Service | Délai |
|---|---|---|---|---:|
| `FRAUDE_OPERATION_NON_AUTORISEE` | Fraude / opération non autorisée | عملية غير مصرح بها | Conformité et Fraude | 2 j.o. |
| `CARTE_BANCAIRE` | Carte bancaire | البطاقة البنكية | Monétique et Cartes | 5 j.o. |
| `DAB_GAB` | Distributeur (DAB/GAB) | الموزع الآلي | Monétique et Cartes | 5 j.o. |
| `VIREMENT_PRELEVEMENT` | Virement et prélèvement | التحويل والاقتطاع | Opérations Bancaires | 5 j.o. |
| `BANQUE_DIGITALE` | Banque digitale | البنك الرقمي | Banque Digitale | 5 j.o. |
| `PAIEMENT_TPE_ECOMMERCE` | Paiement TPE et e-commerce | الدفع الإلكتروني | Monétique et Cartes | 7 j.o. |
| `CHEQUE_EFFET` | Chèque et effet | الشيك والكمبيالة | Opérations Bancaires | 7 j.o. |
| `COMPTE_GESTION` | Gestion du compte | التصرف في الحساب | Relation Clientèle | 7 j.o. |
| `FRAIS_COMMISSIONS` | Frais et commissions | المصاريف والعمولات | Relation Clientèle | 7 j.o. |
| `CREDIT_FINANCEMENT` | Crédit et financement | القرض والتمويل | Crédits et Financement | 10 j.o. |
| `OPERATIONS_INTERNATIONALES` | Opérations internationales | العمليات الدولية | Opérations Internationales | 10 j.o. |
| `AGENCE_QUALITE_SERVICE` | Agence et qualité de service | الوكالة وجودة الخدمة | Relation Clientèle | 10 j.o. |

Un huitième service, `GENERAL` (Service Général), ne porte aucune catégorie :
c'est la file de secours pour tout ce qui n'est pas routable automatiquement.

> **Il n'existe volontairement aucune catégorie « AUTRE ».** Une classe
> fourre-tout absorbe tous les cas difficiles et détruit sa propre précision.
> Une réclamation inclassable passe sous le seuil et devient
> `needs_human_triage`.

### Statuts et canaux

```
statuts   new · triaged · assigned · in_progress · pending_claimant
          resolved · closed · rejected
canaux    web · email · agence · phone · courrier
```

`resolved`, `closed` et `rejected` sont terminaux : l'horloge SLA s'arrête et
aucun routage ne se produit plus. Une réanalyse ne peut pas rouvrir une
réclamation terminée.

---

## 9. Délais et calendrier

Deux horloges, et **la plus courte gouverne**.

| | Objectif interne | Plafond légal |
|---|---|---|
| Unité | Heures | **Jours ouvrables** |
| Départ | Création | Accusé de réception |
| Barème | P1 4 h · P2 24 h · P3 72 h · P4 168 h | 2 à 15 j.o. selon la catégorie |
| Source | Configuration | `bct.py`, en dur |
| Dépassement | Indicateur de qualité | **Événement déclarable** |

Un objectif interne qui dépasserait le plafond est ramené dessus : une banque
peut être plus rapide que la réglementation, jamais plus lente. Les deux
dépassements sont suivis séparément.

### Le calendrier ouvré tunisien

- **Week-end** et jours fériés fixes
- **Fêtes du calendrier lunaire** par table (Aïd, Mouled)
- **Séance unique d'été** : clôture à 13h30
- **Horaires de Ramadan**, distincts
- Horaire ordinaire le reste de l'année : clôture à 17h00

> **Un exemple qui vaut une démonstration** — quinze jours ouvrables depuis le
> 13 août tombent le **4 septembre**, soit 22 jours calendaires, et l'heure de
> clôture passe de 13h30 (séance unique d'été) à 17h00 en septembre. Une
> implémentation en jours calendaires déclarerait le dépassement une semaine
> trop tôt et alerterait pour rien.

Un balayage s'exécute **toutes les cinq minutes** : avertissement à 80 % du
budget consommé, puis dépassement, puis escalade.

---

## 10. Conformité BCT

Circulaire **n°2022-08 du 20 octobre 2022**, « Politiques et mesures de
traitement des réclamations de la clientèle ».

| Article | Exigence | Implémentation |
|---|---|---|
| Art. 2 | Six exclusions du périmètre | `rules/perimetre.py` — le message reste traité, il sort des totaux |
| Art. 6 | Canaux de réception minimaux | 5 canaux → 4 buckets du régulateur |
| Art. 7 | Informer des délais et de la médiation | La voie de médiation est dans chaque modèle de réponse |
| Art. 8 | Accusé daté et référencé | Émis à la création, démarre l'horloge légale |
| Art. 8 | Réponse ≤ 15 jours ouvrables | Plafond calculé au calendrier tunisien |
| Art. 8 | Rejet motivé | `POST /reject` refuse une motivation trop courte |
| Art. 9 | Base, accusés, alerte, indicateurs | MongoDB · accusé automatique · balayage 5 min · tableau de bord |
| Art. 12 | Audit interne tous les 3 ans | Constante définie ; compte à rebours non affiché *(partiel)* |
| Annexe 1 | 10 informations minimales | Bloc `reglementaire` sur chaque réclamation |
| Annexe 2 | Déclaration ROGS760, annuelle, XML, DR+45j | `GET /analytics/declaration/{year}/xml` |
| Annexe 3 | Quatre tableaux de la déclaration | Nature · genre et âge · canal · objet et délais |

### Les huit objets de l'annexe 3-IV

Nos 12 catégories se projettent sur les 8 objets que compte le régulateur :
Financement · Paiement hors monétique · Monétique · Fonctionnement des comptes ·
Opérations bancaires internationales · Tarification · Services bancaires à
distance · Autres services.

> **Une limite du formulaire, pas de l'implémentation** — la liste du régulateur
> n'a **aucune entrée pour la fraude**. Une opération carte non autorisée est
> monétique, un virement non autorisé est paiement hors monétique, et ni l'un ni
> l'autre ne dit à la BCT que de l'argent est parti sans consentement. La
> correspondance retient `MONETIQUE`, origine dominante, et la catégorie interne
> reste intacte — mais la déclaration ne sait littéralement pas exprimer le cas.

---

## 11. Modèle de données

```
Complaint
  ref                 REC-2026-00042      référence affichée, séquentielle
  channel             web | email | agence | phone | courrier
  status              new … rejected
  triage_state        pending | done | failed | manual
  subject, body       texte d'origine, accents conservés
  normalized_text     texte replié, ce sur quoi on recherche
  corrected           un humain a changé la catégorie ou le service

  claimant            nom, courriel, téléphone, référence client, VIP
                      + annexe 3 : nature, genre, tranche d'âge, RNE

  analysis            category, category_confidence (part de preuve)
                      category_alternatives, subcategory
                      priority, priority_score, rule_hits[]
                      sentiment, language, keywords
                      duplicate_of, duplicate_score, related_ids
                      needs_human_triage, triage_reason
                      engine, engine_version, latency_ms

  assignment          service, agent, date, méthode (auto|manual|queue)

  sla                 due_at, hours, breached, warned, escalation_level
                      legal_due_at, legal_days, legal_breached

  reglementaire       accuse_reception_at      art. 8, départ de l'horloge
                      investigations_menees    annexe 1
                      demarches_entreprises    annexe 1
                      motivation               art. 8, rejet motivé
                      hors_perimetre           art. 2
                      objet_bct                annexe 3-IV

  attachments[]       fichier, type, taille, clé S3, déposant
  messages[]          échanges, avec notes internes
  timeline[]          journal d'audit horodaté
  satisfaction        note 1-5 et commentaire
```

> **Écritures ciblées, jamais `save()`** — les services écrivent avec `$push` et
> `$set` sur les seuls champs qu'ils possèdent. Un `save()` complet réécrit tout
> le document depuis une copie en mémoire potentiellement périmée : c'est ainsi
> qu'une pièce jointe déposée pendant l'analyse disparaissait silencieusement.
> Ce défaut est apparu **trois fois** dans ce projet — pièces jointes,
> résolution, messages — et la règle est donc générale.

### Index

| Index | Sert à |
|---|---|
| `ref` (unique) | Suivi par référence |
| `status` + `sla.due_at` | Balayage SLA |
| `assignment.agent_id` + `status` | File d'un agent |
| `assignment.department_id` + `status` | File d'un service |
| `analysis.category` + `created_at` | Statistiques |
| `created_at` + `_id` | Pagination par curseur |
| texte (`subject`, `body`, `normalized_text`) | Recherche ; `default_language="none"` |

L'index texte est déclaré sans langue de radicalisation : la radicalisation
française est inutile sur de l'arabe et de l'arabizi, et MongoDB n'autorise
qu'un seul index texte par collection. `normalized_text` y figure pour que
l'arabe et la derja restent trouvables.

---

## 12. Référence API

Base `/api/v1`. Jeton d'accès en `Authorization: Bearer`, rafraîchissement par
cookie httpOnly.

### Authentification

| Méthode | Route | Rôle | Accès |
|---|---|---|---|
| `POST` | `/auth/register` | Créer un compte réclamant | Public |
| `POST` | `/auth/login` | Ouvrir une session | Public |
| `POST` | `/auth/refresh` | Renouveler le jeton d'accès | Cookie |
| `POST` | `/auth/logout` | Fermer la session | Authentifié |
| `GET` | `/auth/me` | Profil courant | Authentifié |

### Réclamations

| Méthode | Route | Rôle | Accès |
|---|---|---|---|
| `POST` | `/complaints` | Déposer ; renvoie référence et lien de suivi | Public |
| `GET` | `/complaints/track` | Suivi par référence et contact | Public |
| `POST` | `/complaints/satisfaction` | Noter après clôture | Jeton de suivi |
| `GET` | `/complaints` | Liste paginée par curseur, filtres | Agent |
| `GET` | `/complaints/{id}` | Détail complet | Agent |
| `PATCH` | `/complaints/{id}` | Catégorie, service, statut, VIP ; `agent_id` réservé au superviseur | Agent |
| `POST` | `/complaints/{id}/messages` | Répondre ou noter en interne | Agent |
| `POST` | `/complaints/{id}/resolve` | Résoudre avec message au client | Agent |
| `POST` | `/complaints/{id}/reject` | **Rejeter ; motivation obligatoire (art. 8)** | Agent |
| `POST` | `/complaints/{id}/retriage` | Relancer le pipeline | Superviseur |
| `GET` | `/complaints/{id}/analysis` | Trace complète des six étapes | Agent |
| `GET` | `/complaints/{id}/suggest` | Articles de base de connaissances | Agent |
| `POST` | `/complaints/{id}/suggest/used` | Marquer une suggestion utilisée | Agent |
| `POST` | `/complaints/{id}/attachments` | Déposer une pièce | Agent ou jeton |
| `GET` | `/complaints/{id}/attachments/{aid}` | Télécharger | Agent ou jeton |

### Statistiques et déclaration

| Méthode | Route | Rôle | Accès |
|---|---|---|---|
| `GET` | `/analytics/overview` | Volumes, SLA, satisfaction | Agent |
| `GET` | `/analytics/by-category` | Répartition et part de preuve moyenne | Agent |
| `GET` | `/analytics/volume` | Série par jour | Agent |
| `GET` | `/analytics/supervision` | Tableau de supervision | Agent |
| `GET` | `/analytics/agents` | Charge par agent | Superviseur |
| `GET` | `/analytics/engine` | État du moteur, taux de correction | Superviseur |
| `GET` | `/analytics/rules` | Déclenchements par règle | Superviseur |
| `GET` | `/analytics/kb` | Usage des articles | Superviseur |
| `GET` | `/analytics/declaration/{year}` | **ROGS760 en JSON** | Superviseur |
| `GET` | `/analytics/declaration/{year}/xml` | **ROGS760 en XML (annexe 2)** | Superviseur |

### Administration

| Méthode | Route | Rôle | Accès |
|---|---|---|---|
| `GET` | `/rules` | Catalogue des 27 règles | Superviseur |
| `PATCH` | `/rules/{id}` | Poids, activation, configuration | Admin |
| `POST` | `/rules/simulate` | Essai à blanc ; n'enregistre rien | Superviseur |
| `GET` | `/kb` | Articles | Agent |
| `POST` | `/kb` | Créer | Admin |
| `PATCH` | `/kb/{id}` | Modifier | Admin |
| `DELETE` | `/kb/{id}` | Supprimer | Admin |
| `POST` | `/kb/reindex` | Reconstruire l'index BM25 | Admin |
| `GET` | `/departments` | Services | Agent |
| `POST` | `/departments` | Créer | Admin |
| `PATCH` | `/departments/{id}` | Modifier | Admin |
| `DELETE` | `/departments/{id}` | Supprimer | Admin |
| `GET` | `/users` | Personnel | Superviseur |
| `POST` | `/users` | Créer | Admin |
| `PATCH` | `/users/{id}` | Modifier | Admin |

### Temps réel et santé

| Méthode | Route | Rôle |
|---|---|---|
| `GET` | `/events/stream` | Flux SSE ; requiert un en-tête, donc `fetch` et non `EventSource` |
| `GET` | `/health` | Vivacité |
| `GET` | `/health/ready` | Mongo, Redis, moteur, abonnés SSE |

### Événements diffusés

```
complaint.created · complaint.triaged · complaint.assigned · complaint.updated
complaint.replied · complaint.resolved · complaint.escalated
sla.warning · sla.breached · triage.corrected
```

Trois seulement déclenchent une notification visuelle : `sla.warning`,
`sla.breached` et `complaint.escalated`. La file se rafraîchit déjà seule ; un
avis par arrivée serait du bruit.

---

## 13. RBAC

Quatre rôles. Le cloisonnement est un filtre **injecté dans la requête**, jamais
appliqué après lecture.

| Rôle | Filtre injecté |
|---|---|
| **Admin** | `{}` — aucune restriction |
| **Superviseur** | `{}` — aucune restriction |
| **Agent** avec service | son service OU ses affectations |
| **Agent** sans service | ses affectations uniquement |
| **Réclamant** | ses propres réclamations |

| Action | Réclamant | Agent | Superviseur | Admin |
|---|:---:|:---:|:---:|:---:|
| Déposer, suivre ses réclamations | ✅ | ✅ | ✅ | ✅ |
| Voir la file et l'analyse | ❌ | périmètre | ✅ | ✅ |
| Corriger une catégorie, changer un statut | ❌ | ✅ | ✅ | ✅ |
| Répondre, résoudre, rejeter | ❌ | ✅ | ✅ | ✅ |
| Statistiques générales | ❌ | ✅ | ✅ | ✅ |
| **Réaffecter à un agent** | ❌ | ❌ | ✅ | ✅ |
| Relancer l'analyse | ❌ | ❌ | ✅ | ✅ |
| Charge par agent, supervision | ❌ | ❌ | ✅ | ✅ |
| Lire les règles, simuler | ❌ | ❌ | ✅ | ✅ |
| **Déclaration ROGS760** | ❌ | ❌ | ✅ | ✅ |
| **Modifier un poids de règle** | ❌ | ❌ | ❌ | ✅ |
| Gérer base de connaissances, utilisateurs, services | ❌ | ❌ | ❌ | ✅ |

> **Deux gardes, et la différence compte** — `require_role` respecte la
> hiérarchie : un admin passe partout où un agent passe. `require_exact_roles`
> ne la respecte pas : **un admin n'est pas implicitement un agent**. Un test
> vérifie explicitement cette distinction, et un autre garantit qu'un filtre
> vide — qui signifierait « tout lire » — ne peut jamais être produit pour un
> rôle inférieur.

---

## 14. Interface

| Route | Écran | Accès |
|---|---|---|
| `/portal` | Dépôt d'une réclamation | Public |
| `/portal/suivi` | Suivi par référence | Public |
| `/portal/satisfaction` | Évaluation après clôture | Public |
| `/portal/mes-reclamations` | Espace du réclamant | Réclamant |
| `/portal/reclamation/:id` | Détail côté réclamant | Réclamant |
| `/login` · `/register` | Session | Public |
| `/inbox` | File de traitement, filtres, curseur | Agent |
| `/inbox/:id` | Détail, analyse, réponse, réaffectation | Agent |
| `/supervision` | Tableau de supervision | Superviseur |
| `/analytics` | Statistiques et graphiques | Agent |
| `/admin/rules` | Règles et simulateur | Superviseur / Admin |
| `/admin/kb` | Base de connaissances | Superviseur / Admin |
| `/admin/users` | Personnel | Admin |
| `/admin/departments` | Services | Admin |

### Le système de couleurs

L'identité est noire et rouge, ce qui crée le seul conflit qu'un système de
réclamations ne peut pas se permettre : **le rouge est déjà la couleur du
danger**. La résolution sépare les deux par le rôle et la position, pas
seulement par la teinte.

| Jeton | Emploi | Interdit |
|---|---|---|
| `--primary` | Graphite : boutons, focus, états actifs | — |
| `--brand` | Rouge : marque, filet du bandeau, navigation active | **Jamais sur une donnée ni un état** |
| `--danger` | Oxblood : dépassement, P1, action destructive | Jamais sur du chrome |
| `--amber` | Réservé au SLA et au triage humain | Partout ailleurs |

En mode sombre, `--primary` s'inverse en quasi-blanc : un bouton rouge se
battrait avec les badges de dépassement voisins dans la file.

### Internationalisation

Le portail est bilingue français et arabe avec un RTL réel — mise en page
miroir, pas seulement le texte — et les numéros de téléphone restent isolés en
LTR à l'intérieur du texte arabe. La console est en français, langue de travail
du personnel bancaire tunisien.

Aucune police n'est embarquée : l'exécution hors ligne exclut un CDN, et les
fontes système rendent correctement l'arabe sur toutes les plateformes visées.

### La marque

L'artwork officiel est **une marque déposée et n'est délibérément pas
versionné**. `Brandmark` charge `frontend/public/brand/uib.svg` dès qu'il est
déposé, et retombe sinon sur une composition typographique.

---

## 15. Comptes de démonstration

Créés par le script de peuplement. Mot de passe commun : `Rakib2026!`

| Adresse | Nom | Rôle | Service |
|---|---|---|---|
| `admin@rakib.tn` | Sonia Trabelsi | Admin | — |
| `superviseur1@rakib.tn` | Mehdi Gharbi | Superviseur | tous |
| `superviseur2@rakib.tn` | Ines Bouzid | Superviseur | tous |
| `agent.mon1@rakib.tn` | Karim Jelassi | Agent | Monétique et Cartes |
| `agent.mon2@rakib.tn` | Rania Ayari | Agent | Monétique et Cartes |
| `agent.ope1@rakib.tn` | Yassine Chaouch | Agent | Opérations Bancaires |
| `agent.ope2@rakib.tn` | Nadia Belhaj | Agent | Opérations Bancaires |
| `agent.cre1@rakib.tn` | Walid Mansouri | Agent | Crédits et Financement |
| `agent.rc1@rakib.tn` | Olfa Hamdi | Agent | Relation Clientèle |
| `agent.rc2@rakib.tn` | Bilel Khemiri | Agent | Relation Clientèle |
| `agent.dig1@rakib.tn` | Amel Zouari | Agent | Banque Digitale |
| `agent.int1@rakib.tn` | Hamza Ben Romdhane | Agent | Opérations Internationales |
| `agent.frd1@rakib.tn` | Sofiene Kacem | Agent | Conformité et Fraude |

> Identifiants de **démonstration** uniquement. Le rôle *Réclamant* n'est pas
> pré-créé : il se crée depuis `/register`, ou implicitement lorsqu'un dépôt
> anonyme est rattaché à une adresse connue.

---

## 16. Tests

```bash
docker compose -f docker-compose.test.yml run --rm tests
ruff check .
mypy app/
```

Quinze fichiers. Couverture mesurée sur `services/` et `intelligence/`
seulement — le cœur métier.

| Fichier | Couvre |
|---|---|
| `test_normalize.py` | Nettoyage, masquage, repli des accents latins et arabes, arabizi |
| `test_language_and_engine.py` | Identification de langue, derja, moteur de secours |
| `test_rules_engine.py` | Les 27 règles, pondérations, seuils de priorité |
| `test_triage_pipeline.py` | Enchaînement des six étapes, dédoublonnage, affectation |
| `test_rules_api.py` | Lecture, édition, validation, simulateur |
| `test_complaints.py` | Dépôt, cycle de vie, pagination par curseur |
| `test_attachments.py` | Dépôt authentifié et anonyme, écriture atomique |
| `test_auth.py` | Inscription, session, rafraîchissement, jetons de suivi |
| `test_rbac.py` | Hiérarchie, gardes de routes, filtre de périmètre |
| `test_security.py` | argon2, signature JWT, expiration |
| `test_sla.py` | Calendrier ouvré, plafond de l'article 8, alertes, escalade |
| `test_events.py` | Redis Streams, groupes de consommateurs, SSE |
| `test_kb.py` | BM25, suggestions, comptage d'usage |
| `test_analytics.py` | Agrégations et leur cloisonnement |
| `conftest.py` | Fixtures : une boucle d'événements pour toute la session |

### Évaluer la catégorisation

```bash
python -m scripts.evaluate
```

Mesure le lexique contre `scripts/gold.py`, écrit à la main et indépendamment du
vocabulaire : **0,600 de macro-F1, 37 % d'abstention, 88 % des inclassables
correctement renvoyés**.

Il n'y a pas de jeu de contrôle : un lexique ne peut rien mémoriser, donc
l'écart contrôle/réel qui domine tant de rapports n'existe pas ici.

---

## 17. Déploiement

k3s, espace de noms `reclamations`, TLS automatique.

```bash
export VPS_HOST=root@votre-serveur
export VPS_KEY=~/.ssh/votre-cle
export SMTP_SECRET_NS=... SMTP_SECRET_NAME=...

sh deploy/deploy.sh              # build, import k3s, applique, vérifie
sh deploy/deploy.sh --skip-build # manifestes seulement
```

| Service | Rôle |
|---|---|
| `api` | FastAPI et flux SSE |
| `worker` | Analyse de fond, balayage SLA (5 min) |
| `notifier` | Consommateur du flux, envoi des courriels |
| `web` | React servi par nginx |
| `mongo` · `redis` · `minio` | Données, files, pièces jointes |

### L'image

Build multi-étapes : le toolchain d'installation n'atteint jamais l'image
finale. **469 Mo**, contre 800 visés. `PIP_ONLY_BINARY=:all:` fait échouer le
build au grand jour si une dépendance cessait de publier une wheel, plutôt que
de réintroduire un compilateur en silence. Le conteneur tourne sous un
utilisateur non privilégié.

---

## 18. Exploitation

### Peuplement

```bash
python -m scripts.seed --force --count 60
python -m scripts.seed --no-triage      # sans exécuter le pipeline
```

### Charge

```bash
python3 deploy/benchmark.py [requêtes] [concurrence]
python3 deploy/benchmark.py 300 1 --keep   # conserve les lignes créées
```

> **Le benchmark écrit dans la vraie base.** Ses requêtes créent de *vraies*
> réclamations : catégorisées, comptées, et intégrées à la déclaration destinée
> au régulateur. Elles portent une adresse dédiée et sont supprimées par défaut
> en fin de mesure. `--keep` existe, mais il faut le demander : le mode d'échec
> est silencieux et ne se manifeste que comme un chiffre faux dans un rapport
> réglementaire.

### Vérification visuelle

```bash
node deploy/visual_check.mjs      # 11 captures + erreurs console
```

Playwright parcourt portail, RTL arabe, file, détail, simulateur, statistiques
et mobile. Plusieurs des défauts les plus sérieux du projet n'ont été trouvés
que par ce script — aucun outil statique ne les voyait.

### Santé

```bash
curl https://votre-instance/health/ready
```

```json
{"status":"ready",
 "checks":{"mongo":true,"redis":true},
 "sse_clients":0,
 "engine":{"active_engine":"lexicon",
           "engine_version":"lexicon-v1",
           "degraded":false}}
```

---

## 19. Problèmes connus

| Sujet | Détail |
|---|---|
| **Performance sous concurrence** | 58 ms p95 à un client (cible tenue), 196 ms à cinq, 501 ms à vingt. L'hôte partagé explique une part de l'écart ; le débit plafonne vers 60 req/s, ce qui désigne une contention interne. La cause exacte demande un profilage. |
| **Généralisation nulle hors vocabulaire** | 37 % d'abstention sur le jeu de référence. Corrigeable par un administrateur qui élargit le lexique, pas par le système lui-même. |
| **La déclaration ne sait pas dire « fraude »** | Aucune entrée correspondante dans la nomenclature du régulateur. |
| **Marque officielle non fournie** | `Brandmark` charge `public/brand/uib.svg` dès qu'il est déposé. |
| **Audit interne non outillé** | L'intervalle de trois ans de l'article 12 est défini mais aucun compte à rebours n'est affiché. |
| **401 au rechargement** | Le jeton d'accès n'existe qu'en mémoire, par choix de sécurité ; le premier appel après rechargement échoue avant la reprise automatique. Sans effet fonctionnel, mais visible en console. |
| **Console peu visible depuis le portail** | Un visiteur arrivant sur le portail ne devine pas qu'une console existe : l'entrée est un simple lien « Connexion » sans identifiants de démonstration. |

---

## Licence et mentions

Projet de fin d'études. **Projet académique, sans affiliation officielle avec
l'établissement dont l'identité visuelle est utilisée.** L'artwork de marque
n'est pas versionné. Les identifiants de démonstration n'ont cours que sur
l'environnement de démonstration.

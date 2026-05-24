# Architecture — Console de supervision Dialeo (Diallo-sup)

> Ce document fige les décisions techniques actées lors du cadrage produit du
> **23 mai 2026**. Il fait foi pour tous les chantiers à venir. Toute évolution
> de ces choix doit être consignée ici.
>
> Nom fonctionnel produit : **Console de supervision Dialeo**.
> Nom technique du repo : **Diallo-sup**.

---

## 1. Contexte

Dialeo est un assistant IA souverain pour écoles primaires et collèges, déployé
sur des Mac mini en établissement (un Mac mini = un établissement). La **Console
de supervision Dialeo** est une application séparée, hébergée sur un Mac mini
dédié (« DialSup »), qui supervise une flotte de Mac mini clients Dialeo.

Elle se décline en deux niveaux :

- **N1 — lecture seule** : observabilité de la flotte (santé, sessions,
  incidents, reports, inventaire).
- **N2 — pilotage actif** : actions de configuration poussées à distance vers
  les Mac mini clients, sous garde-fous stricts.

Multi-établissements **dès la conception** : v1 cible 1 à 3 sites, l'architecture
doit tenir à 50+ sites sans refonte.

---

## 2. Périmètre fonctionnel cible

> Cible produit. **Rien de ce qui suit n'est implémenté au chantier de fondation** ;
> ces fonctionnalités arrivent ensuite, écran par écran puis action par action
> (cf [ROADMAP.md](./ROADMAP.md)).

### 2.1 Console N1 (lecture seule)

**10 données remontées** depuis chaque Mac mini client :

1. Santé du Mac mini
2. Statut Ollama
3. Statut Dialeo
4. Sessions temps réel
5. Sessions historiques
6. Incidents de modération
7. Reports anonymisés
8. Logs critiques
9. Stats hardware
10. Inventaire

**6 écrans** :

1. Dashboard global (page d'accueil par défaut)
2. Vue établissement
3. Reports
4. Déploiements N2
5. Inventaire / licences
6. Réglages console

### 2.2 Console N2 (pilotage actif)

**4 actions** poussées vers les Mac mini clients :

1. Push blacklist
2. Push system prompts
3. Push config Ollama
4. Redémarrage de services à distance

**5 garde-fous non négociables** pour toute action N2 :

1. **Signature cryptographique** des ordres
2. **Validation préalable** avant exécution
3. **Canary** : 12 h sur un établissement pilote, puis 24-48 h post-pilote
4. **Rollback automatique** en cas d'anomalie
5. **Audit trail complet** (cf §7)

---

## 3. Stack technique

| Couche | Choix | Statut |
|---|---|---|
| Backend console | **FastAPI + SQLite**, Python 3.11+ (cohérent avec le Dialeo principal) | Fondation posée |
| ORM / accès données | **SQLAlchemy 2.0** (déclaratif), migrations **Alembic** à venir | Fondation posée |
| Frontend console | **React + TypeScript + Vite + TailwindCSS** (SPA) | Scaffolding au chantier N1 |
| Communication client → console | **REST** (push des Mac mini) | À venir |
| Communication console → UI | **SSE** (rafraîchissement live navigateur) | Chantier séparé |
| Authentification console | **Cloudflare Access (Email OTP)** | Infra Cloudflare pas encore connectée |
| Authentification client → console | **API key statique 256 bits par Mac mini** | À venir |

L'environnement de fondation tourne sur **Python 3.13** (installé via Homebrew
sur le Mac mini DialSup) ; le projet cible `requires-python >= 3.11` pour rester
aligné avec le Dialeo principal.

---

## 4. Architecture de déploiement

**Décision : FastAPI sert directement le build statique du SPA. Pas de Caddy.**

La console est exposée derrière **Cloudflare Tunnel + Cloudflare Access**.
Conséquences :

- Cloudflare termine le TLS et constitue l'unique point d'entrée public ;
  `cloudflared` se connecte à une **origine locale en clair** (`127.0.0.1`).
- Un reverse proxy local (Caddy) n'apporterait que de la redondance : le TLS est
  déjà géré en amont, il n'y a qu'un seul backend, pas de routage multi-service.

L'application FastAPI :

- expose l'API sous `/api/*` ;
- monte le build statique du SPA (`StaticFiles` + fallback SPA) sur le reste des
  routes — **un seul process, un seul port, une seule unité `launchd`**.

> **Réversibilité** : si plusieurs services locaux apparaissent (ex. daemon de
> métriques distinct), Caddy pourra être réintroduit comme reverse proxy local
> sans toucher au code applicatif. Choix volontairement minimal pour réduire la
> surface d'exploitation sur un Mac mini qui supervise déjà une flotte.

---

## 5. Collecteur Mac mini client (hors de ce repo)

> Le collecteur **ne vit pas dans Diallo-sup** : il sera implémenté dans le repo
> Dialeo principal (`educdialeo/dialeo`). Documenté ici pour la cohérence d'ensemble.

Modèle **hybride** :

- **Push** depuis Dialeo (l'application cliente envoie ses données vers
  `/api/ingest` de la console) ;
- **Pull** depuis un **daemon léger autonome** géré par `launchd` sur le Mac mini
  client (collecte indépendante de l'état de Dialeo, ex. santé matérielle même si
  Dialeo est tombé).

### Fréquences de synchronisation

| Donnée | Fréquence |
|---|---|
| Critique (santé, statuts) | 30 s |
| Hardware | 2 min |
| Stats | 5 min |
| Reports & logs | à l'événement |
| Agrégé | 1 h |
| Inventaire | 1 j |

---

## 6. Stockage & rétention

- **SQLite**, stockage **exhaustif** des données remontées.
- **Rétention 90 jours**, avec **purge nocturne** des données expirées (chantier séparé).
- Tables créées via `Base.metadata.create_all` au démarrage. **Alembic** sera
  introduit quand le schéma N1 se fige (cf dette technique, ROADMAP).

### Stockage de l'ingestion — hybride (phase 3.2)

- **`raw_pushes`** : log **brut universel** — *tout* push y est consigné
  intégralement (`payload` JSON), quel que soit son type. Sert l'audit et le replay.
- **Tables dédiées** pour les données fréquemment requêtées : `heartbeats`
  (compat 3.1), `sessions` (live + historiques via colonne `kind`), `incidents`
  (compteurs de modération), `reports` (anonymisés).
- Les autres types (`sante_systeme`, `ollama_status`, `dialeo_status`,
  `logs_critiques`, `inventaire`, `daemon_uvicorn_health`) restent dans `raw_pushes`
  uniquement — requêtables en JSON SQLite, promus en table dédiée plus tard si nécessaire.
- Dispatch par le champ `type` (union discriminée Pydantic), dans
  `app/services/ingest.py`.

> Dette : `heartbeats` est en **double écriture** avec `raw_pushes` (compat 3.1) ;
> fusion possible plus tard (cf ROADMAP).

### Table `etablissements` (posée au chantier de fondation)

| Colonne | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | auto-incrément |
| `name` | TEXT | unique, non nul, indexé |
| `api_key_hash` | TEXT | **hash SHA-256** de l'API key 256 bits (jamais la clé en clair) |
| `status` | TEXT | défaut `active` |
| `created_at` | TIMESTAMP | UTC |

---

## 7. Sécurité & accès

### 7.1 Authentification console (utilisateurs)

- **Cloudflare Access — Email OTP**. Aucune auth applicative maison.
- v1 **mono-utilisateur** (Geoffroy), mais le modèle de données et les routes
  sont pensés **multi-utilisateurs dès la conception** (pas de raccourci bloquant
  une montée ultérieure).

> ⚠️ **Dette technique connue (phase 3.1)** : `POST /api/establishments` (création
> d'établissement + génération de l'API key) est un endpoint **admin/console**,
> aujourd'hui **non protégé** en local. Il **doit** être placé derrière Cloudflare
> Access **avant toute exposition externe**. Tant que la console n'est pas exposée
> (pas de tunnel connecté), le risque reste contenu au LAN.

### 7.2 Authentification Mac mini client → console

- **API key statique 256 bits par Mac mini**, générée par la console à la
  création d'un établissement, **copiée manuellement** dans le `.env` du Mac mini
  client.
- La console ne stocke que le **hash SHA-256** de la clé (`api_key_hash`).

**Implémentation (phase 3.1)** :

- Génération : `secrets.token_urlsafe(32)` (256 bits d'entropie, ~43 caractères
  URL-safe). Hash : `hashlib.sha256(...).hexdigest()`. Voir `app/core/security.py`.
- La clé en clair est renvoyée **une seule fois** (réponse 201 de
  `POST /api/establishments`) ; elle n'est ni stockée, ni reloggée.
- Vérification : dépendance FastAPI `get_current_etablissement`
  (`app/api/deps.py`) — schéma `HTTPBearer`, hash de la clé reçue puis lookup sur
  `api_key_hash` (colonne indexée), exige `status == "active"`, sinon **401**.
- Cloisonnement : un établissement ne peut relire que **ses propres** données
  (sinon **403**) — cf `GET /api/establishments/{id}/heartbeats`.

### 7.3 Audit trail

Cinq familles d'événements à tracer :

| Code | Événement |
|---|---|
| **A1** | Toutes les actions N2 (push, redémarrage…) |
| **A2** | Connexions à la console |
| **A3** | Requêtes API entrantes (push des Mac mini clients) |
| **A4** | Anomalies |
| **A5** | Exports |

**Stratégie de stockage & rétention retenue** :

- Table unique **`audit_log`**, **append-only** (jamais de mise à jour ni
  suppression hors purge).
- Rétention **alignée sur la rétention générale (90 jours)** + purge nocturne,
  **sauf A1 (actions N2) conservées plus longtemps** (traçabilité des
  changements de configuration de la flotte — durée à figer au chantier N2,
  proposition : 1 an).
- **A3 en format compact** quand le volume est élevé : on enregistre
  `timestamp, méthode, route, etab_id, status_code` **sans le corps de la
  requête**. Les autres familles peuvent porter un contexte structuré (JSON).

> Non implémenté au chantier de fondation : seule la stratégie est figée ici.

### 7.4 Anonymisation des reports (RGPD by design — phase 3.2)

L'anonymisation est faite **à la source** (côté Mac mini client, phase 3.3). Côté
console, on **garantit qu'aucune donnée identifiante ne peut entrer** :

- **Champs autorisés (seuls)** : `date_jour` (jour près, jamais l'heure),
  `question`, `reponse`, `mode_pedagogique`, `niveau_scolaire` (liste 1+ valeurs
  parmi CP→3e), `note_enseignant`.
- **Champs interdits** (prénom, nom enseignant, ID/code session, ID connexion,
  ID classe, nom établissement, e-mail, IP…) : le schéma `ReportItem` est en
  `extra="forbid"` → tout champ non déclaré est **rejeté avec un HTTP 400
  explicite** (`app/api/errors.py`). Rien d'identifiant n'atteint la base.
- La table `reports` ne **possède pas de colonne** pour ces champs interdits.

---

## 8. UX / UI (cadrage, hors implémentation)

- **Identité visuelle** : dashboard neutre + touches Dialeo. Header avec wordmark
  **DiALEO**, accent **bleu craie `#7DB8E8`**, police **Inter**. Couleurs
  fonctionnelles : **vert sauge** (ok), **orange chaleureux** (alerte), **rouge
  brique** (critique).
- **Navigation** : sidebar verticale fixe + breadcrumb contextuel.
- **Page d'accueil** : Dashboard global.
- **Temps réel** : tous les écrans en **SSE auto** + **toggle Pause** utilisateur.
- **Notifications visuelles** : badge sidebar + toast popup pour les critiques.
- **Notifications externes** : **email** pour les événements critiques
  **uniquement** (pas de SMS, pas d'intégrations tierces en v1).

---

## 9. Périmètre explicitement exclu du chantier de fondation

- Les **écrans** (arrivent feature par feature).
- Le **collecteur Mac mini client** (vit dans le repo Dialeo principal).
- **Cloudflare Tunnel / Access** (à connecter quand l'infra sera prête).
- Génération de **PAT, clés cryptographiques, certificats** (chantier signature N2).
- **Auth utilisateur** applicative (rôle dévolu à Cloudflare Access).
- **Signature cryptographique N2** (chantier séparé).
- **SSE temps réel** (chantier séparé).

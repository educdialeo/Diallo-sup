# Console de supervision Dialeo — `Diallo-sup`

> **🛑 Projet clôturé le 2026-07-19 (`v1.0.0-final-cloture`). Plus aucun
> développement.** Le produit [Dialeo](https://github.com/educdialeo/dialeo) est
> arrêté ; sa console de supervision n'a plus d'objet. Ce dépôt est figé et
> conçu pour être **auto-explicatif**. État final et raison de l'arrêt :
> [`docs/JOURNAL.md`](docs/JOURNAL.md) (entrée 2026-07-19). Décisions et points
> laissés ouverts : [`docs/DECISIONS.md`](docs/DECISIONS.md).

---

## Ce qu'est DialSup

**DialSup** (nom technique du repo : `Diallo-sup`, volontaire) est la **console de
supervision multi-établissements** du produit Dialeo.

[Dialeo](https://github.com/educdialeo/dialeo) est un assistant IA **souverain** pour
écoles primaires et collèges, déployé **localement sur un Mac mini par établissement**
(les « M4 »). DialSup observe cette flotte depuis un point central : un backend FastAPI
tournant sur un Mac mini dédié (« DialSup »), qui reçoit les push des M4 et sert une
console web de supervision.

### Console **vendeur** — agrégats anonymisés uniquement

DialSup est un outil **côté vendeur**, pas un outil pédagogique. Principe non négociable,
gravé dans le code :

- **Jamais de données élève nominatives.** Aucun prénom, nom, identifiant de session,
  de classe ou de connexion ne transite ni n'est stocké.
- Seuls des **agrégats et métadonnées anonymisés** sont manipulés (santé machine,
  compteurs d'incidents, volumétrie de sessions, reports **sans contenu**).
- Sur `POST /api/ingest`, tout champ identifiant dans un `reports` est **refusé par un
  `400` explicite**. Côté lecture, les colonnes de contenu (`question`, `reponse`,
  `note_enseignant`) **ne sont jamais chargées** par la page Rapports (SELECT explicite
  des seules colonnes sûres + test de non-régression dédié).

Voir [`docs/DECISIONS.md`](docs/DECISIONS.md) (D4) et [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §7.4.

---

## État atteint (figé à la clôture)

- **Phase N1 — console lecture seule : livrée ET déployée en prod.** 7 écrans,
  alimentés par les push des M4. **Runtime en production : `v0.13.0`.**
- **Authentification admin (chantier 4) : DÉPLOYÉE, pas seulement mergée.**
  - Phase A — mot de passe (`v0.7.0`) : déployée.
  - Phases B (MFA TOTP, `v0.8.0`) + C (frontend d'auth, `v0.9.0`) : **déployées ensemble
    le 2026-06-06**, MFA admin `gmd@dialeo.com` enrôlé, console verrouillée en runtime.
  - N1 (`v0.10.0`→`v0.13.0`) a été empilée **par-dessus** cette base déjà déployée.

> **⚠️ Anti-contresens pour un repreneur** : il n'existe **aucune phase « mergée mais
> jamais déployée »**. Tout ce qui est sur `main` **tourne en prod**. L'auth MFA est
> active depuis le 2026-06-06, pas du code dormant. Ne cherchez pas un déploiement
> d'auth « à finir » : il n'y en a pas.

**Non construit** (resté ouvert, `NON POURSUIVI`) : phase N2 (pilotage actif), SSE temps
réel, table d'audit `audit_log`, connexion Cloudflare Tunnel + Access. Cf
[`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## Architecture & stack

- **Backend** : Python 3.11+ (réf. 3.13) · **FastAPI** · **SQLAlchemy 2.0** ·
  **Pydantic v2** (+ pydantic-settings) · **SQLite** (rétention 90 j, purge nocturne).
- **Frontend** : **React 19** · **TypeScript** · **Vite 7** · **Tailwind v4** ·
  **React Router 7**. Police Inter bundlée (`@fontsource`, pas de CDN).
- **Service du SPA** : pas de Caddy — `app/main.py` sert `frontend/dist/` en statique
  (StaticFiles + fallback SPA). En dev, Vite :5173 proxifie `/api` et `/health` vers
  uvicorn :8000.
- **Exécution en prod** : uvicorn sous **launchd** (LaunchAgent `com.diallosup.uvicorn`,
  uid 501, port 8000) — démarrage au boot, redémarrage auto au crash.
- **Exposition cible (jamais connectée)** : Cloudflare Tunnel + Access (Email OTP),
  origine locale en clair sur `127.0.0.1`.
- **Communication** : REST (push des M4 vers `/api/ingest`).

Détails et justifications : [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) ·
[`docs/DECISIONS.md`](docs/DECISIONS.md) · résilience et exploitation :
[`docs/RESILIENCE.md`](docs/RESILIENCE.md).

---

## Les 7 écrans (N1, lecture seule)

Toutes les pages sont derrière `<RequireAuth>` (login mot de passe → MFA TOTP).

| Écran | Route | Contenu |
|---|---|---|
| **Dashboard fleet** | `/dashboard` | Grille de tuiles par établissement : santé live, sessions live, usage agrégé, sparkline 14 j, badges incident/dormant |
| **Établissement** (+ drill-down) | `/etablissement` · `/etablissement/:id` | Détail par établissement : panneaux Machine / Dialeo / Daemon / Ollama / Historique 30 j / Incidents 30 j, chacun marquant sa fraîcheur |
| **Rapports** | `/reports` | KPI 7 j/30 j, ventilations par niveau et par mode, top 10 émetteurs, **50 derniers reports anonymisés** (sans contenu) + bandeau RGPD |
| **Modération** | `/moderation` | Agrégation flotte des incidents : KPI par catégorie (blacklist / llamaguard / systemprompt), tendance 30 j, top 10, 50 derniers — **compteurs uniquement** |
| **Déploiements** | `/deploiements` | Vue **préparatoire** N2 (placeholder ; le pilotage actif n'a pas été construit) |
| **Inventaire** | `/inventaire` | 1 ligne / établissement (modèle Mac mini, macOS, sièges, formule) + agrégats |
| **Réglages** | `/reglages` | Config runtime **lecture seule** ; secrets exposés en booléens (`*_configured`) uniquement, aucune valeur |

> Note d'état : au moment de la clôture, les tables `incidents` et `reports` sont
> **vides** (jamais alimentées par les M4). Les écrans correspondants sont réels et
> fonctionnels mais s'affichent sans données.

---

## Comment relancer (sans mémoire préalable)

Tout ce qu'il faut pour remettre la main sur le service, sans rien connaître d'avance.

### La prod tourne déjà (cas nominal)

Le service redémarre **seul au boot**. Pour vérifier / piloter :

```bash
# État + PID du service
launchctl print gui/501/com.diallosup.uvicorn

# Logs
tail -f ~/Library/Logs/diallosup-uvicorn.log

# Redémarrer proprement (relit le code disque + la dist buildée)
launchctl kickstart -k gui/501/com.diallosup.uvicorn
```

Vérifications de bonne santé (attendus entre parenthèses) :

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/health          # 200
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8000/api/ingest  # 401 (auth active)
curl -s http://127.0.0.1:8000/openapi.json | python3 -c "import sys,json;print(json.load(sys.stdin)['info']['version'])"  # 0.13.0
```

### ⚠️ Après tout changement de frontend : REBUILD obligatoire

uvicorn sert `frontend/dist/` **statique**. Un simple `kickstart` **ne rebuilde pas**
le SPA — sinon l'UI servie reste périmée (leçon 2026-06-07, cf `DECISIONS.md` D11) :

```bash
cd ~/Projects/Diallo-sup/frontend && npm install && npm run build
launchctl kickstart -k gui/501/com.diallosup.uvicorn
```

### Repartir de zéro (nouvelle machine)

```bash
git clone https://github.com/educdialeo/Diallo-sup.git && cd Diallo-sup
make install                      # crée .venv + installe backend ([dev])
cp .env.example .env              # puis adapter
.venv/bin/python -m app.scripts.init_secrets   # génère JWT_SECRET + TOTP_AT_REST_KEY (idempotent)
.venv/bin/python -m app.scripts.create_admin   # crée l'admin (interactif, min 12 car.)
cd frontend && npm install && npm run build && cd ..
make dev                          # http://127.0.0.1:8000 sert le SPA + l'API
```

Au 1er login, l'admin non enrôlé passe par le **flux d'enrôlement MFA** (QR TOTP +
10 codes de récupération affichés une seule fois). Installation launchd, bascule et
rollback : [`docs/RESILIENCE.md`](docs/RESILIENCE.md).

### Développement (2 process, HMR)

```bash
make dev            # terminal 1 : backend uvicorn :8000
make front-dev      # terminal 2 : Vite :5173 (proxy /api,/health -> :8000)
```

### Tests

```bash
make test           # backend  (pytest)
make front-test     # frontend (vitest)
```

---

## API — référence

Auth des M4 clients : **API key 256 bits par établissement**, en
`Authorization: Bearer <clé>`. La console ne stocke que le **hash SHA-256** ; la clé en
clair n'est renvoyée **qu'une seule fois**, à la création de l'établissement.

| Méthode & route | Auth | Description |
|---|---|---|
| `GET /health` | — | Sonde de liveness → `{"status":"ok","service":"Diallo-sup console"}` |
| `POST /api/auth/login` | — | Étape 1/2 (mdp) → cookie **pre_auth** (5 min) ; `401` générique sinon ; `423` si verrouillé (5 échecs / 15 min) |
| `POST /api/auth/totp/enroll` | pre_auth / session | Secret TOTP provisoire (chiffré at-rest) → URI otpauth ; `409` si déjà enrôlé |
| `POST /api/auth/totp/confirm` | pre_auth / session | Valide le code → cookie **session** (12 h) + 10 codes de récupération (1×) |
| `POST /api/auth/verify-totp` | pre_auth | Étape 2/2 (code TOTP **ou** code de récupération à usage unique) → cookie session |
| `POST /api/auth/logout` | session | Efface le cookie (caveat JWT stateless, cf `RESILIENCE.md`) → 204 |
| `GET /api/auth/me` | session | Profil de l'admin connecté → 200 |
| `POST /api/establishments` | admin (`require_admin`) | Crée un établissement, renvoie l'API key en clair (1×) → 201 |
| `POST /api/ingest` | Bearer | Reçoit un push (11 types) et le persiste → 202 |
| `GET /api/establishments/{id}/heartbeats` | Bearer¹ | Relit les N derniers heartbeats (`?limit=`, défaut 50, max 1000), tri desc → 200 |
| `GET /api/fleet` · `/api/fleet/{id}` | admin | Données Dashboard / détail établissement |
| `GET /api/incidents/overview` | admin | Agrégation flotte des incidents (compteurs) |
| `GET /api/inventory/overview` · `/api/reports/overview` · `/api/settings/overview` | admin | Écrans Inventaire / Rapports / Réglages |

¹ Un établissement ne peut relire que **ses propres** heartbeats (sinon 403).

### Types d'ingestion (`POST /api/ingest`)

Endpoint unique, dispatch sur le champ `type` (union discriminée, validation Pydantic
stricte `extra="forbid"`). Tout push est consigné dans `raw_pushes` ; certains types
alimentent en plus une table dédiée.

| `type` | Table dédiée | Contenu |
|---|---|---|
| `heartbeat` | `heartbeats` | `status` |
| `sante_systeme` | — (raw) | santé Mac mini + stats hardware |
| `ollama_status` | — (raw) | modèles chargés, latence, RAM |
| `dialeo_status` | — (raw) | version, statut uvicorn, modes actifs |
| `sessions_live` | `sessions` (`kind=live`) | classes/élèves connectés (compteurs), modes en cours |
| `sessions_historiques` | `sessions` (`kind=historique`) | agrégats jour/semaine/mois |
| `incidents_moderation` | `incidents` | compteurs de refus (blacklist / llamaguard / system prompt) |
| `reports` | `reports` | reports **anonymisés** (champ identifiant → `400`) |
| `logs_critiques` | — (raw) | logs `ERROR` / `CRITICAL` |
| `inventaire` | — (raw) | modèle Mac mini, macOS, sièges, formule |
| `daemon_uvicorn_health` | — (raw) | signal du daemon de surveillance M4 (ping uvicorn) |

---

## Structure du projet

```
Diallo-sup/
├── app/
│   ├── main.py        # app factory FastAPI + lifespan (init DB) + service du SPA
│   ├── api/           # routers (auth, health, establishments, ingest, fleet,
│   │                  #   incidents, inventory, reports, settings) + deps (auth)
│   ├── core/          # config + base SQLAlchemy + security (API keys, JWT)
│   ├── models/        # modèles ORM (etablissements, users, heartbeats, sessions,
│   │                  #   incidents, reports, raw_pushes)
│   ├── schemas/       # schémas Pydantic v2 (I/O API, dont UtcDatetime)
│   ├── services/      # logique métier (fleet, incidents, inventory, reports,
│   │                  #   settings, ingest)
│   └── scripts/       # init_secrets, create_admin, migrate_phase_b
├── frontend/          # SPA React 19 + TS + Vite 7 + Tailwind v4
│   └── src/           # main, App (routes), components, pages (7 écrans), hooks, lib
├── tests/             # pytest (backend)
├── ops/               # com.diallosup.uvicorn.plist (LaunchAgent)
├── docs/              # ARCHITECTURE · ROADMAP · JOURNAL · DECISIONS · RESILIENCE
├── CLAUDE.md          # fiche d'identité projet
├── pyproject.toml
└── Makefile
```

---

## Documentation

- [`docs/JOURNAL.md`](docs/JOURNAL.md) — journal daté des chantiers (le plus récent en tête ; clôture 2026-07-19).
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — décisions structurantes + points laissés ouverts.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — phasage (archivé, chantiers ouverts marqués `NON POURSUIVI`).
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — décisions d'architecture détaillées.
- [`docs/RESILIENCE.md`](docs/RESILIENCE.md) — exploitation, déploiement, rollback, caveats.

---

*Console de supervision Dialeo — repo `educdialeo/Diallo-sup`. Logiciel propriétaire. Projet clôturé.*

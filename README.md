# Console de supervision Dialeo

> Repo technique : **Diallo-sup** — Backend FastAPI de la console de supervision
> multi-établissements de la flotte Dialeo.

---

## Pitch

[Dialeo](https://github.com/educdialeo/dialeo) est un assistant IA **souverain**
pour écoles primaires et collèges, déployé localement sur un Mac mini par
établissement. La **Console de supervision Dialeo** observe et pilote cette flotte
de Mac mini depuis un point central, selon trois principes :

- **Souverain** — tout reste sur du matériel maîtrisé ; pas de dépendance à un
  cloud tiers pour les données pédagogiques. La console est exposée via Cloudflare
  Tunnel + Access, sans ouverture de port entrant.
- **Conforme** — audit trail complet, données de reports anonymisées, rétention
  bornée à 90 jours avec purge automatique.
- **Pédagogique** — la supervision sert la continuité du service en classe :
  détecter une panne, un incident de modération ou une dérive avant qu'ils ne
  perturbent les usages.

---

## Fonctionnalités cibles

> Aucune fonctionnalité n'est encore livrée : ce repo en est au **chantier de
> fondation**. Voir [docs/ROADMAP.md](docs/ROADMAP.md).

### Console N1 — lecture seule (cible : mi-juin 2026)

Supervision multi-établissements : **6 écrans** (Dashboard global, Vue
établissement, Reports, Déploiements N2, Inventaire/licences, Réglages) alimentés
par **10 données** remontées des Mac mini clients (santé, statut Ollama, statut
Dialeo, sessions temps réel & historiques, incidents de modération, reports
anonymisés, logs critiques, stats hardware, inventaire).

### Console N2 — pilotage actif (cible : fin juin → début juillet 2026)

**4 actions** poussées à distance, livrées une par une, sous **5 garde-fous**
(signature cryptographique, validation préalable, canary 12 h/24-48 h, rollback
automatique, audit trail) :

1. Push blacklist
2. Push system prompts
3. Push config Ollama
4. Redémarrage de services à distance

---

## Stack technique

- **Backend** : Python 3.11+ · FastAPI · SQLAlchemy 2.0 · SQLite
- **Frontend** : React + TypeScript + Vite + TailwindCSS *(scaffoldé au chantier N1)*
- **Communication** : REST (push des Mac mini clients) · SSE (rafraîchissement
  live de l'UI)
- **Déploiement** : FastAPI sert le build statique du SPA, derrière Cloudflare
  Tunnel + Cloudflare Access (Email OTP)

Détails et justifications : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Prérequis

- **Python 3.11+** (l'environnement de référence tourne sous Python 3.13,
  installé via `brew install python@3.13`)
- **Git**

---

## Installation locale

```bash
git clone https://github.com/educdialeo/Diallo-sup.git
cd Diallo-sup

# Crée le venv (.venv) et installe les dépendances (+ outils de dev)
make install
```

Équivalent manuel sans `make` :

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Configuration :

```bash
cp .env.example .env   # puis adapter si besoin
```

---

## Démarrage

```bash
make dev
```

Équivalent manuel :

```bash
.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Vérification :

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok","service":"Diallo-sup console"}
```

- Documentation interactive de l'API : <http://127.0.0.1:8000/docs>
- Endpoints d'ingestion (auth par API key) : voir la section [API](#api) ci-dessous.

---

## Frontend (SPA)

Ossature React + TypeScript + Vite + TailwindCSS posée au chantier 2 (layout,
navigation, charte Dialeo — écrans réels au chantier N1). Détails :
[frontend/README.md](frontend/README.md).

**Dev — 2 process** (HMR côté front, vraie API côté back) :

```bash
make dev            # terminal 1 : backend uvicorn :8000
make front-install  # 1re fois seulement
make front-dev      # terminal 2 : Vite :5173 (proxy /api,/health -> :8000)
```

**Prod — FastAPI sert le build** :

```bash
make front-build    # génère frontend/dist/
make dev            # http://127.0.0.1:8000 sert le SPA + l'API
```

---

## Tests

```bash
make test         # backend  (pytest)
make front-test   # frontend (vitest)
```

---

## API

Authentification des Mac mini clients : **API key 256 bits par établissement**,
transmise en `Authorization: Bearer <clé>`. La console ne stocke que le hash
SHA-256 de la clé ; la clé en clair n'est renvoyée **qu'une seule fois**, à la
création de l'établissement.

| Méthode & route | Auth | Description |
|---|---|---|
| `GET /health` | — | Sonde de liveness |
| `POST /api/establishments` | ⚠️ admin¹ | Crée un établissement, renvoie l'API key en clair (1×) → 201 |
| `POST /api/ingest` | Bearer | Reçoit un heartbeat et le persiste → 202 |
| `GET /api/establishments/{id}/heartbeats` | Bearer² | Relit les N derniers heartbeats (`?limit=`, défaut 50, max 1000), tri `received_at` desc → 200 |

¹ Non protégé en local pour l'instant — **doit passer derrière Cloudflare Access
avant toute exposition externe** (cf [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §7.1).
² Un établissement ne peut relire que **ses propres** heartbeats (sinon 403).

### Exemple cURL end-to-end

```bash
# 1) Créer un établissement (note l'api_key : non récupérable ensuite)
curl -s -X POST http://127.0.0.1:8000/api/establishments \
  -H "Content-Type: application/json" -d '{"name": "École Saint-Pierre"}'
# → {"id":1,"name":"École Saint-Pierre","api_key":"<CLÉ_EN_CLAIR>","created_at":"..."}

KEY="<CLÉ_EN_CLAIR>"

# 2) Pousser un heartbeat
curl -s -X POST http://127.0.0.1:8000/api/ingest \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"type":"heartbeat","timestamp":"2026-05-23T14:30:00Z","status":"ok"}'
# → 202  {"received_at":"..."}

# 3) Relire ses heartbeats
curl -s -H "Authorization: Bearer $KEY" \
  "http://127.0.0.1:8000/api/establishments/1/heartbeats?limit=50"
# → 200  [{"id":1,"timestamp":"...","status":"ok","received_at":"..."}]
```

---

## Structure du projet

```
Diallo-sup/
├── app/
│   ├── main.py            # app factory FastAPI + lifespan (init DB) + service du SPA
│   ├── api/               # routers (health, establishments, ingest) + deps (auth)
│   ├── core/              # config + base SQLAlchemy + security (API keys)
│   ├── models/            # modèles ORM (etablissements, heartbeats)
│   ├── schemas/           # schémas Pydantic (I/O API)
│   └── services/          # logique métier (à venir)
├── frontend/              # SPA React + TS + Vite + Tailwind (ossature)
│   └── src/               # main, App (routes), components, pages, hooks, lib
├── tests/                 # pytest (backend)
├── docs/                  # ARCHITECTURE.md, ROADMAP.md
├── CLAUDE.md              # fiche d'identité projet pour Claude Code
├── pyproject.toml
└── Makefile
```

---

## Contribution

- Branche par défaut : **`main`**.
- Messages de commit : **Conventional Commits** (`feat:`, `fix:`, `chore:`,
  `docs:`…).
- Avant de pousser : `make test` + `make lint` (backend) et `make front-test` +
  `make front-lint` (frontend) doivent passer.
- Le périmètre et le phasage sont cadrés dans [docs/ROADMAP.md](docs/ROADMAP.md) ;
  les décisions d'architecture dans [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

*Console de supervision Dialeo — repo `educdialeo/Diallo-sup`. Logiciel propriétaire.*

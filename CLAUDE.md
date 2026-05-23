# CLAUDE.md — Diallo-sup

Fiche d'identité projet, lue automatiquement à chaque session Claude Code sur ce
repo. À tenir à jour quand les invariants changent.

## Ce qu'est ce projet

**Console de supervision Dialeo** (nom fonctionnel produit) — backend FastAPI de
supervision multi-établissements de la flotte Dialeo.

- **Nom technique du repo : `Diallo-sup`.** C'est le nom officiel dans le code,
  les chemins et la doc technique. Ne pas le « corriger » en `dialeo-supervision`,
  ne pas le renommer : c'est volontaire et ferme.
- **Nom fonctionnel produit, dans la doc client-facing : « Console de supervision
  Dialeo ».**
- Repo : `educdialeo/Diallo-sup` (privé). Branche par défaut : `main`.
- Tourne sur un Mac mini dédié nommé « DialSup ». Distinct du repo Dialeo
  principal `educdialeo/dialeo` (l'assistant IA déployé en établissement).

## Stack & conventions

- **Backend** : Python 3.11+ (réf 3.13 via Homebrew, venv `.venv/`). FastAPI +
  SQLAlchemy 2.0 + SQLite. Pydantic v2 / pydantic-settings. Lint ruff, tests pytest.
- **Frontend** : React 19 + TS + Vite 7 + Tailwind v4 + React Router 7, dans
  `frontend/`. Tests Vitest, lint ESLint. Inter bundlé (`@fontsource`), pas de CDN.
- **Conventional Commits** (`feat:`, `fix:`, `chore:`, `docs:`…).
- Raccourcis : `make install|dev|test|lint` (backend) · `make front-install|front-dev|front-build|front-test|front-lint` (frontend).
- Avant de pousser : `make test` + `make lint` **et** `make front-test` + `make front-lint` doivent passer.

## Architecture en bref

- **Déploiement** : FastAPI sert le build statique du SPA (pas de Caddy), derrière
  **Cloudflare Tunnel + Access (Email OTP)**. Origine locale en clair sur
  `127.0.0.1`.
- **Frontend** : ossature React + TS + Vite + Tailwind posée (layout, sidebar,
  6 routes placeholder, charte Dialeo). En dev : Vite :5173 proxifie `/api`,`/health`
  vers uvicorn :8000. En prod : `app/main.py` sert `frontend/dist/` (StaticFiles +
  fallback SPA) si le build existe — inerte en dev/CI/tests.
- **Communication** : REST (push des Mac mini clients vers `/api/ingest`) + SSE
  (UI live).
- **Auth client → console** : API key 256 bits/Mac mini (`secrets.token_urlsafe(32)`),
  console stocke le **hash SHA-256** (`app/core/security.py`). Vérif via dépendance
  `get_current_etablissement` (`app/api/deps.py`, schéma Bearer → 401). Cloisonnement
  par établissement → 403. ⚠️ `POST /api/establishments` est admin et **non protégé**
  pour l'instant (à mettre derrière Cloudflare Access — cf ARCHITECTURE §7.1).
- **Stockage** : SQLite, rétention 90 j, purge nocturne. Tables créées via
  `create_all` pour l'instant ; **Alembic** à introduire quand le schéma N1 se fige
  (caveat : `create_all` n'altère pas une table existante).
- **Audit** : familles A1-A5 (cf `docs/ARCHITECTURE.md` §7.3) — non implémenté.

> Toutes les décisions actées sont dans **`docs/ARCHITECTURE.md`** ; le phasage
> dans **`docs/ROADMAP.md`**. Les lire avant de proposer un changement structurel.

## État actuel

**Chantier de fondation (23 mai 2026, `v0.1.0-scaffold`)** :
- `/health` → `{"status": "ok", "service": "Diallo-sup console"}`
- `POST /api/ingest` → **501** (stub, futur point d'entrée des push clients)
- Table `etablissements` (id, name, api_key_hash, status, created_at) · 3 tests pytest verts

**Chantier 2 — scaffolding frontend (`v0.2.0-frontend-scaffold`)** :
- Ossature SPA : Layout (sidebar fixe + breadcrumb), 6 routes placeholder
  (défaut → `/dashboard`), charte Dialeo, `HealthIndicator` (sonde `/health`)
- FastAPI sert le build en prod · 1 test Vitest vert · backend toujours 3 verts

**Chantier 3 phase 3.1 — ingest API (`v0.3.0-ingest-api`)** :
- `POST /api/establishments` (201, renvoie l'API key en clair 1×) · auth Bearer
- `GET /api/establishments/{id}/heartbeats` (200, `?limit` 50/max 1000, tri desc, 403 cross-étab)

**Chantier 3 phase 3.2 — payload N1 exhaustif (`v0.4.0-payload-n1`)** :
- `POST /api/ingest` accepte **10 types** (union discriminée sur `type`, validation
  stricte `extra="forbid"`) : heartbeat, sante_systeme, ollama_status, dialeo_status,
  sessions_live, sessions_historiques, incidents_moderation, reports, logs_critiques, inventaire
- Stockage **hybride** : `raw_pushes` (log brut de TOUS les push) + tables dédiées
  `heartbeats`, `sessions` (kind live/historique), `incidents`, `reports`. Les autres
  types restent en raw_pushes seul. Dispatch dans `app/services/ingest.py`.
- **Reports anonymisés** : champ identifiant → **400** (`app/api/errors.py`, cf ARCHITECTURE §7.4).
  `niveau_scolaire` = liste 1+ parmi CP→3e (enum `NiveauScolaire`).
- 28 tests pytest verts. Phases suivantes : 3.3 client M4 · 3.4 daemon launchd (repo Dialeo principal)

## Ce qui n'est PAS encore là (et ne doit pas être inventé)

- Les **vrais écrans** (Dashboard, Reports, etc.) → arrivent feature par feature au
  chantier N1. L'ossature de navigation existe, mais les pages sont des placeholders.
- **Payload N1 exhaustif** (10 données) → phase 3.2. Phase 3.1 ne gère que le type
  `heartbeat` minimal (le corps complet est déjà conservé en JSON dans `heartbeats.payload`).
- Le **client Python M4** (phase 3.3) et le **daemon launchd** (phase 3.4) → repo
  **Dialeo principal**, pas ici. Ne pas toucher au repo `educdialeo/dialeo`.
- Cloudflare Tunnel/Access, signature crypto N2, SSE temps réel, auth utilisateur
  applicative → chantiers séparés (cf ROADMAP).

## Garde-fous de travail

- Ne pas générer de PAT, clés cryptographiques ni certificats sans demande explicite.
- Ne pas committer de secret : `.env` est git-ignoré (seul `.env.example` est suivi).
- Les fichiers SQLite (`*.db`, `data/`) sont git-ignorés.

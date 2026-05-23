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

- **Python 3.11+** (env de référence : 3.13 via Homebrew). venv dans `.venv/`.
- **FastAPI + SQLAlchemy 2.0 + SQLite.** Pydantic v2 / pydantic-settings.
- **Conventional Commits** (`feat:`, `fix:`, `chore:`, `docs:`…).
- **Lint : ruff** (`make lint`). **Tests : pytest** (`make test`).
- Raccourcis : `make install` / `make dev` / `make test` / `make lint`.
- Avant de pousser : `make test` **et** `make lint` doivent passer.

## Architecture en bref

- **Déploiement** : FastAPI sert le build statique du SPA (pas de Caddy), derrière
  **Cloudflare Tunnel + Access (Email OTP)**. Origine locale en clair sur
  `127.0.0.1`.
- **Frontend** : React + TS + Vite + Tailwind — **pas encore scaffoldé** (chantier N1).
- **Communication** : REST (push des Mac mini clients vers `/api/ingest`) + SSE
  (UI live).
- **Auth client → console** : API key statique 256 bits par Mac mini ; la console
  ne stocke que le **hash SHA-256** (`api_key_hash`).
- **Stockage** : SQLite, rétention 90 j, purge nocturne. Tables créées via
  `create_all` pour l'instant ; **Alembic** à introduire au chantier N1.
- **Audit** : familles A1-A5 (cf `docs/ARCHITECTURE.md` §7.3) — non implémenté.

> Toutes les décisions actées sont dans **`docs/ARCHITECTURE.md`** ; le phasage
> dans **`docs/ROADMAP.md`**. Les lire avant de proposer un changement structurel.

## État actuel

**Chantier de fondation (23 mai 2026).** Posé :

- `/health` → `{"status": "ok", "service": "Diallo-sup console"}`
- `POST /api/ingest` → **501** (stub, futur point d'entrée des push clients)
- Table `etablissements` (id, name, api_key_hash, status, created_at)
- 3 tests pytest verts
- Tag `v0.1.0-scaffold`

## Ce qui n'est PAS encore là (et ne doit pas être inventé)

- Les écrans / le frontend (arrivent feature par feature au chantier N1).
- Le collecteur Mac mini client → vit dans le repo **Dialeo principal**, pas ici.
- Cloudflare Tunnel/Access, signature crypto N2, SSE temps réel, auth utilisateur
  applicative → chantiers séparés (cf ROADMAP).

## Garde-fous de travail

- Ne pas générer de PAT, clés cryptographiques ni certificats sans demande explicite.
- Ne pas committer de secret : `.env` est git-ignoré (seul `.env.example` est suivi).
- Les fichiers SQLite (`*.db`, `data/`) sont git-ignorés.

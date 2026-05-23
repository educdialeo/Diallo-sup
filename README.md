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
- `POST /api/ingest` répond **501 Not Implemented** (stub : futur point d'entrée
  des push des Mac mini clients).

---

## Tests

```bash
make test
# ou : .venv/bin/python -m pytest
```

---

## Structure du projet

```
Diallo-sup/
├── app/
│   ├── main.py            # app factory FastAPI + lifespan (init DB)
│   ├── api/               # routers (health, ingest)
│   ├── core/              # config + base SQLAlchemy
│   ├── models/            # modèles ORM (etablissements)
│   └── services/          # logique métier (à venir)
├── frontend/              # SPA — scaffoldé au chantier N1
├── tests/                 # pytest
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
- Avant de pousser : `make test` et `make lint` (ruff) doivent passer.
- Le périmètre et le phasage sont cadrés dans [docs/ROADMAP.md](docs/ROADMAP.md) ;
  les décisions d'architecture dans [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

*Console de supervision Dialeo — repo `educdialeo/Diallo-sup`. Logiciel propriétaire.*

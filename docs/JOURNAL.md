# Journal des chantiers — Diallo-sup

Index horodaté des chantiers livrés sur ce repo, du plus récent au plus ancien.
Référence : tags annotés sur `main`. Détails techniques dans le commit / les diffs.

---

## 2026-06-06 — Chantier N1 étape 2 : Drill-down établissement (`v0.11.0-establishment-detail`)

Page détail atteinte en cliquant une tuile du Dashboard. Réutilise l'infra
posée à l'étape 1 (`compute_health`, `usePolling`, `StatusDot`, `Sparkline`,
charte chalkboard, seed) ; pas un gros build neuf.

**Backend** :
- `GET /api/fleet/{etablissement_id}` (sous `require_admin`) renvoie un
  `EstablishmentDetail` typé. 401 sans cookie / pre_auth seul, **404** si étab
  inexistant.
- Helpers extraits/ajoutés dans `app/services/fleet.py` : `_last_raw_push`
  (générique), `_machine_health`, `_ollama_snapshot`, `_dialeo_snapshot`,
  `_daemon_snapshot` (chacun lit le dernier `raw_push` du type voulu et
  expose `last_seen_at`), `_incidents_list` (LISTE des incidents 30 j vs la
  somme de la tuile), `_usage_history` (30 entrées/jour avec zéros remplis,
  `duree_moyenne_min` pondérée par `nb_sessions` intra-jour),
  `build_establishment_detail`.
- 8 nouveaux tests pytest : 401 sans/avec pre_auth, 404 inexistant, structure
  complète, parsing machine depuis `sante_systeme`, parsing `dialeo`, liste
  incidents avec ventilation + fenêtre 30 j, et **test dédié à la dette
  consignée** (un `sante_systeme.status_global="degraded"` ne fait PAS
  basculer le `health` top-level).

**Découverte (faite avant code)** : le `heartbeats.payload` réel en prod ne
porte PAS la télémétrie machine (juste `{type, timestamp, status}` minimal).
Les vraies données viennent de 4 types distincts loggés dans `raw_pushes` :
`sante_systeme` (CPU/RAM/disque/uptime), `dialeo_status`
(version/uvicorn_status/modes_active), `daemon_uvicorn_health`
(uvicorn_status/consecutive_failures), `ollama_status`. C'est ce que parse
la page détail.

**Frontend** :
- Route `/etablissement/:id` sous `<RequireAuth>`, page
  `EstablishmentDetail.tsx`. Tuile `EstablishmentTile` rendue **cliquable**
  (`<Link>` + hover sobre).
- Cartes : en-tête, Sessions live, Machine, Dialeo, Daemon de surveillance,
  Ollama, Historique d'usage 30 j (Sparkline 30 valeurs, **pas** de grosse
  lib de charts), Incidents modération 30 j (tableau compteurs ventilés).
  Lien retour « ← Dashboard ».
- **Helper `lib/staleness.ts`** : seuil 10 min (généreux pour absorber les
  collectes 30 s / 2 min de l'archi). Chaque panneau affiche son
  `last_seen_at` lisible (« mis à jour il y a X ») et un **badge « périmé »
  ambré** si dépassement, pour qu'un CPU% d'il y a 5 jours ne passe pas pour
  du temps réel. `last_seen_at: null` → « Non rapporté ».
- 8 nouveaux tests Vitest (4 page détail : nom + CPU + Dialeo + incident,
  badge périmé, « Non rapporté » Ollama, 404 ; 4 staleness purs).
- Sentence case partout, charte chalkboard réutilisée (badge périmé en
  `ambre-500`, jamais rouge — comme le badge dormant).

**Seed étendu** : `app/scripts/seed_fleet.py` ajoute désormais, pour les
établissements pertinents, un `sante_systeme` + `dialeo_status` +
`daemon_uvicorn_health` réalistes (raw_pushes), et **3 incidents ventilés**
sur Collège Renoir + daemon en alerte (`uvicorn_status="ko"`,
`consecutive_failures=3`) pour démontrer le panneau. Garde-fou anti-prod
préservé. Recette de démo identique à celle de l'étape 1.

**Dette technique consignée** (NE PAS retoucher l'étape 1) : `compute_health`
ne pondère que la **fraîcheur + le `status` du heartbeat** (toujours « ok »
en prod). Conséquence : un établissement peut afficher 🟢 alors qu'un service
est tombé (`sante_systeme.status_global="degraded"`,
`dialeo_status.uvicorn_status="down"`, `daemon.consecutive_failures` élevé).
À ce stade les **panneaux fins** de la page détail exposent ces signaux et
l'admin peut juger ; à enrichir `compute_health` plus tard avec ces sources,
probablement quand le fix du collecteur M4 ramènera de la donnée fraîche.
Cf ROADMAP § Dette technique.

**Hypothèse ouverte** (re-confirmée 2026-06-06) : `ollama_status` n'a
**jamais** été observé en prod (0 ligne `raw_pushes`). Le snapshot Ollama est
exposé pour ne pas avoir à re-coder quand M4 commencera à l'émettre ; en
attendant l'UI affiche « Non rapporté » dans le panneau Ollama.

**Tests** : **128 pytest + 26 vitest verts** (8 + 8 nouveaux).

**Hors scope** (consigné) : visualiseur du contenu reports (exclu RGPD tant
que juriste n'a pas tranché), inventaire / réglages, websockets / SSE, modif
de l'ingestion, seuils d'alerte santé fins (affichage brut en v1), ZÉRO
touche M4.

## 2026-06-06 — Chantier N1 étape 1 : Dashboard fleet view (`v0.10.0-fleet-dashboard`)

Première vraie page console branchée sur de la donnée. Tout sous
`Depends(require_admin)` dès le départ (règle consignée au déploiement matin).

**Backend** :
- `GET /api/fleet` (router `app/api/fleet.py`) renvoie une liste typée
  `FleetItem` par établissement.
- Calcul de santé live isolé dans `app/services/fleet.py::compute_health`
  (fonction pure, testable seule). Seuils ajustables en tête de module :
  `HEALTH_ONLINE_MAX_MIN=5`, `HEALTH_SILENT_MIN_MIN=15`. Règles : aucun HB →
  silent ; HB ≥ 15 min → silent ; HB.status ≠ "ok" → degraded ; HB ≥ 5 min →
  degraded ; sinon online.
- Agrégation par établissement : dernier `sessions kind='live'` (élèves
  connectés + classes), historiques `kind='historique' granularite='jour'`
  (`sessions_total` tout-l'historique, `sessions_7j`, `trend_14d` normalisée à
  14 ints chronologiques, `nb_eleves` agrégé, `duree_moyenne_min` pondérée par
  `nb_sessions`), incidents `received_at ≥ now − 7 j` (somme des 3
  `nb_refus_*`), flag `is_dormant = (health == "online" AND sum(trend_14d) == 0)`
  strict (pas de tolérance pour la v1).

**Frontend** :
- Page `Dashboard.tsx` réécrite, sous `<RequireAuth>` (chantier 4 phase C).
  Hook `usePolling` (30 s, cleanup correct, flag d'annulation).
- Composants : `EstablishmentTile` (3 couches : nom + pastille / live +
  usage + sparkline / badges), `StatusDot`, `Sparkline` (SVG pure, zéro
  dépendance).
- États gérés : `loading`, `empty` (0 établissement), bandeau « tous
  silencieux », `populated`.
- Charte chalkboard : 3 tokens ajoutés (`ardoise-700` #2A3137, `chalk-50`
  #F5F1E8, `ambre-100/500` pour le badge dormant). Pastilles santé : online
  `sauge-500`, degraded `chaleur-500`, silent `brique-500`. Badge dormant
  `ambre-500` — sobre, **jamais rouge** (signal commercial, pas une panne).
  Sentence case partout.

**Inspection prod préalable** : 1 seul établissement (`Dialeo Pilote 001`),
dernier heartbeat il y a ~5 jours (bug `load_dotenv` non appelé côté
collecteur M4 confirmé) ; tables `sessions` / `incidents` / `reports` vides.
**Conséquence sur la prod (:8000)** : tant que le collecteur M4 n'est pas
réparé, la grille affichera **1 tuile « Dialeo Pilote 001 » en santé silent**,
zéro session, zéro incident, sparkline plate. C'est le comportement nominal
attendu du calcul de santé (`HB ≥ 15 min → silent`), pas un bug — la page
fait simplement remonter la panne d'amont. Le seed dev-only (ci-dessous) est
le seul moyen de démontrer les 4 états + le badge dormant et l'incident.

**Hypothèse ouverte** (à confirmer quand de vraies `sessions_historiques`
arriveront en prod) : la couche **trend_14d / sessions_7j repose sur
`granularite == 'jour'`** et un `periode` en ISO date `YYYY-MM-DD`. Le
contrat Pydantic (`SessionsHistoriquesIn`) autorise aussi `'semaine'` et
`'mois'` avec `periode: str` libre — non vérifié contre l'émetteur réel
(le collecteur M4 vit dans un autre repo, pas observable ici). Si M4
n'émet que `'semaine'`/`'mois'`, la sparkline et le compteur 7 j resteront
à zéro tant qu'une variante jour n'est pas ajoutée. À traiter à ce
moment-là (parser `2026-W23` / `2026-06` et projeter sur les jours
correspondants, ou ajouter `granularite='jour'` côté collecteur).

**Seed dev-only** : `app/scripts/seed_fleet.py` peuple 5 établissements
couvrant online / degraded / silent / dormant / incident récent.
**Garde-fou** : refuse d'écrire dans la base prod (URL par défaut **ou**
chemin absolu équivalent à `data/diallo_sup.db`). Recette de démo
**dev-only** (3 terminaux) :

```bash
# Terminal 1 — seed + backend de démo, secrets jetables, base hors-prod
export DATABASE_URL="sqlite:////tmp/diallo_fleet_seed.db"
export JWT_SECRET=$(.venv/bin/python -c "import secrets;print(secrets.token_urlsafe(32))")
export TOTP_AT_REST_KEY=$(.venv/bin/python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")
.venv/bin/python -m app.scripts.seed_fleet
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8017

# Terminal 2 — créer l'admin dans la base seedée (ne touche pas .env réel)
DATABASE_URL="sqlite:////tmp/diallo_fleet_seed.db" .venv/bin/python <<'PY'
import getpass
from app.core.db import SessionLocal, init_db
from app.scripts.create_admin import create_admin
init_db()
db = SessionLocal()
create_admin(input("Email : "), getpass.getpass("Mdp (>=12) : "), db)
db.close()
PY

# Terminal 3 — Vite dev pointant sur le backend de démo (pas :8000 prod)
cd frontend && VITE_API_TARGET=http://127.0.0.1:8017 npm run dev
# puis http://localhost:5173 → login + MFA → /dashboard
```

**Tests** : 14 nouveaux pytest (`test_fleet_health.py` 8 cas purs,
`test_fleet_endpoint.py` 6 cas HTTP : 401 sans session, structure complète,
silent par défaut, dormant détecté, agrégation usage + trend + sessions_7j,
incidents fenêtre 7 j) + 5 pytest seed safeguard + 4 vitest Dashboard
(empty / populated / badge incident / bandeau tous silencieux). **Total :
120 pytest + 18 vitest verts**.

**Hors scope** (consigné) : drill-down établissement, vue incidents dédiée,
inventaire / rapports / réglages, SSE / websockets, toute modification de
l'ingestion.

## 2026-06-06 — Déploiement prod chantier 4 (auth admin B+C)

Opération de **déploiement** uniquement (aucun changement de code, pas de
nouveau tag). État avant : process uvicorn DialSup tournait toujours **v0.7.0**
en mémoire ; le code **v0.9.0** (Phases B + C committées les 31/05) était déjà
sur le disque, `git status` propre, en sync avec `origin/main`.

Séquence exécutée command-by-command :

1. **Backup base SQLite** : copie de `data/diallo_sup.db` vers
   `data/diallo_sup.db.bak-20260606-pre-phaseB` (19 Mo).
2. `.venv/bin/pip install -e ".[dev]"` — deps déjà satisfaites
   (`pyotp 2.9.0`, `cryptography 48.0.0` déjà présents).
3. `python -m app.scripts.migrate_phase_b` — **no-op** (les colonnes
   `failed_login_count` et `locked_until` étaient déjà présentes dans le schéma
   DialSup, schéma à jour).
4. `python -m app.scripts.init_secrets` — `JWT_SECRET` et `TOTP_AT_REST_KEY`
   déjà présents dans `.env`, **préservés** (idempotence honorée).
5. `launchctl kickstart -k gui/501/com.diallosup.uvicorn` — nouveau PID,
   `state = running`, `/health` → 200.

**Bootstrap MFA admin** : `gmd@dialeo.com` (id=1) au 1er login post-upgrade →
réponse `enrolement_requis` → enrôlement TOTP via authenticator → confirmation →
10 codes de récupération **sauvegardés hors-bande**. Cycle `logout → login (mdp) →
verify-totp → /me 200` revalidé end-to-end. **Aucun secret affiché ni exfiltré**
pendant l'opération.

**Résultat** : console DialSup en production **v0.9.0** — verrou auth + MFA actif,
`POST /api/establishments` sous `require_admin` effectif en runtime (la dette portée
depuis la phase 3.1 est définitivement levée côté prod).

## 2026-05-31 — Chantier 4 phase C : frontend auth + verrouillage console (`v0.9.0-auth-frontend`)

UI d'authentification complète : login mot de passe → flux 2 étapes (saisie code TOTP
**ou** code de récupération) → console. Premier login d'un user non enrôlé : écran
d'enrôlement avec **QR (react-qr-code)** + repli "saisie manuelle" (parse du secret
depuis l'URI `otpauth://`) → 10 codes de récupération affichés **une seule fois**, gate
"j'ai sauvegardé mes codes" obligatoire + boutons Copier / Télécharger .txt. Bouton
Déconnexion dans la sidebar (sous l'indicateur santé). Toutes les pages de la console
sont désormais derrière `<RequireAuth>` (redirection automatique `/login` si la session
disparaît, intercepteur 401 global hors `/api/auth/*`). Backend : `POST /api/establishments`
passe sous `require_admin` (dette de la phase 3.1 levée). `make_establishment` refacto
en direct DB (les autres tests d'ingest/heartbeats n'ont pas à configurer l'auth admin).
Registre **vouvoiement** uniforme dans toute l'UI. **Aucun déploiement** : Phases B+C
groupées plus tard en mini-chantier séparé. **101 tests pytest** verts (3 nouveaux) +
**14 tests Vitest** verts (13 nouveaux : api wrapper, AuthProvider, login flow, recovery
gate, app under RequireAuth).

## 2026-05-31 — Chantier 4 phase B : MFA TOTP (`v0.8.0-auth-mfa-totp`)

Flux login 2 étapes (mot de passe → TOTP) + enrôlement avec QR (URI otpauth) +
10 codes de récupération à usage unique. Chiffrement at-rest du secret TOTP
(Fernet, `TOTP_AT_REST_KEY` dans `.env`). Throttling/lockout 5 essais / 15 min
sur `/login` ET `/verify-totp`, avec règle non-négociable : **le compteur ne
reset QUE sur établissement d'une session complète** (jamais sur succès du mdp
seul, sinon brute-force TOTP rouvert). Script de migration
`migrate_phase_b.py` (ALTER `users` idempotent) — Alembic toujours différé.
33 nouveaux tests pytest (98 au total). Doc : `RESILIENCE.md` complété (tradeoff
423, lockout-as-DoS auto-résolu 15 min, 2 secrets critiques dans `.env`,
backlog reset TOTP).

## 2026-05-31 — Chantier 4 phase A : socle auth admin (`v0.7.0-auth-backend-password`)

Table `users`, hash bcrypt via passlib (bcrypt pinné `<5`), JWT HS256 en cookie
`diallosup_session` (HttpOnly / SameSite=Strict / 12 h), endpoints
`/api/auth/{login,logout,me}`, dépendance `require_admin`. `JWT_SECRET`
optionnel (WARN au boot + `/api/auth/*` 503 si absent, mais `/api/ingest`
continue → upgrade non-bloquant). Scripts `init_secrets` (idempotent) et
`create_admin` (interactif `getpass`, min 12 caractères, refus doublons).
Claim `purpose="session"` (prise pour `pre_auth` de la phase B). 22 nouveaux
tests pytest (65 au total).

## 2026-05-24 — Chantier 3 sous-phase 3.4.B : launchd uvicorn (`v0.6.0-launchd-uvicorn`)

uvicorn DialSup placé sous launchd (LaunchAgent `com.diallosup.uvicorn`,
uid 501) : `RunAtLoad` + `KeepAlive`, logs `~/Library/Logs/diallosup-uvicorn.log`,
`WorkingDirectory=/Users/serveur/Projects/Diallo-sup` (critique : la base
SQLite est en chemin relatif). Source : `ops/com.diallosup.uvicorn.plist`.
Procédures bascule/rollback/`bootstrap`/`bootout`/`kickstart` documentées
dans `docs/RESILIENCE.md`. 8 tests structure du plist (plistlib).

## 2026-05-24 — Chantier 3 sous-phase 3.4.C : 11ᵉ type `daemon_uvicorn_health` (`v0.5.0-payload-daemon-health`)

Ajout du signal du daemon de surveillance M4 (ping uvicorn 60 s) à l'union
discriminée d'ingestion. Stockage `raw_pushes` uniquement (signal "status",
pas de table dédiée). Discriminant aligné sur le pattern existant
(`type` + `timestamp`) — escalade tranchée avec le repo M4 pour
homogénéiser le contrat. 7 nouveaux tests.

## 2026-05-23 — Chantier 3 phase 3.2 : payload N1 exhaustif (`v0.4.0-payload-n1`)

`POST /api/ingest` accepte les 10 types du cadrage N1 via union discriminée
Pydantic v2 (`type`), validation stricte `extra="forbid"`. Stockage hybride
`raw_pushes` (log brut universel) + tables dédiées
(`heartbeats`/`sessions`/`incidents`/`reports`). Anti-PII reports : champ
identifiant → `400` explicite via handler global
(`RequestValidationError → extra_forbidden`). `niveau_scolaire = list[str]`
parmi enum CP→3e. 22 nouveaux tests (28 au total).

## 2026-05-23 — Chantier 3 phase 3.1 : auth API key + ingest réel (`v0.3.0-ingest-api`)

API key 256 bits / établissement (`secrets.token_urlsafe(32)`), hash SHA-256
stocké, clé en clair renvoyée 1× à la création. Auth Bearer via dépendance
`get_current_etablissement`. `POST /api/ingest` réel (202) → table `heartbeats`.
`GET /api/establishments/{id}/heartbeats` avec `?limit=` 50/max 1000, tri
desc, cloisonnement par établissement (403). 10 tests.

## 2026-05-23 — Chantier 2 : scaffolding frontend (`v0.2.0-frontend-scaffold`)

Ossature React 19 + TypeScript + Vite 7 + Tailwind v4 + React Router 7,
charte Dialeo (bleu craie, vert sauge/orange chaleureux/rouge brique,
Inter bundlé via `@fontsource`). Layout (sidebar fixe DiALEO + breadcrumb),
6 routes placeholder, `HealthIndicator` (sonde `GET /health`). FastAPI sert
`frontend/dist/` en prod (`StaticFiles` + fallback SPA). 1 test Vitest.

## 2026-05-23 — Chantier 0 : fondation backend (`v0.1.0-scaffold`)

Backend FastAPI + SQLAlchemy 2.0 + SQLite, table `etablissements` (`id, name,
api_key_hash, status, created_at`), endpoint `/health`, `/api/ingest` en
stub 501. Documentation initiale (`README`, `CLAUDE.md`, `ARCHITECTURE.md`,
`ROADMAP.md`). 3 tests pytest.

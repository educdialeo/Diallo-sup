# Journal des chantiers — Diallo-sup

Index horodaté des chantiers livrés sur ce repo, du plus récent au plus ancien.
Référence : tags annotés sur `main`. Détails techniques dans le commit / les diffs.

---

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

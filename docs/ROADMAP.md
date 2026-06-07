# Roadmap — Console de supervision Dialeo (Diallo-sup)

> Phasage acté au cadrage du **23 mai 2026**. Les dates sont des cibles, pas des
> engagements contractuels. Référence d'architecture : [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Chantier 0 — Fondation (23 mai 2026) ✅ *ce chantier*

Pose la fondation du repo. **Ne livre aucune fonctionnalité.**

- Structure de projet (backend FastAPI + arborescence).
- Endpoint `/health` opérationnel.
- Endpoint `/api/ingest` en **stub 501** (point d'entrée des push clients).
- SQLite initialisé avec la table `etablissements` (inventaire / licences).
- Tests pytest verts (`/health`, persistance d'un établissement, stub `/api/ingest`).
- Documentation : `README.md`, `CLAUDE.md`, `docs/ARCHITECTURE.md`, ce fichier.
- Tag `v0.1.0-scaffold`.

---

## Phase N1 — Console lecture seule (cible : mi-juin 2026)

> **🎯 Suivi des écrans N1** (ordre validé 2026-06-06) :
>
> 1. **Dashboard fleet view** — **LIVRÉ (`v0.10.0-fleet-dashboard`, 2026-06-06)** ✅
>    `GET /api/fleet` sous `require_admin`, grille de tuiles par établissement
>    (santé live calculée, sessions live, usage agrégé, sparkline 14 j, badges
>    incident & dormant), polling 30 s. Cf JOURNAL 2026-06-06.
> 2. **Drill-down établissement** — **LIVRÉ (`v0.11.0-establishment-detail`, 2026-06-06)** ✅
>    `GET /api/fleet/{id}` sous `require_admin`, page détail avec panneaux
>    Machine / Dialeo / Daemon / Ollama / Historique 30 j / Incidents 30 j ;
>    chaque panneau marque sa propre fraîcheur (badge « périmé » côté UI,
>    seuil 10 min). Tuile cliquable, polling 30 s. Cf JOURNAL 2026-06-06.
> 3. **Vue incidents modération** — **LIVRÉ (`v0.12.0-incidents-overview`, 2026-06-07)** ✅
>    `GET /api/incidents/overview` sous `require_admin`, vue d'agrégation flotte :
>    KPI 7 j/30 j par catégorie (blacklist/llamaguard/systemprompt), tendance
>    30 j par catégorie, top 10 établissements (drill cliquable), 50 derniers
>    incidents. Aucun contenu utilisateur — compteurs uniquement. Nouvelle entrée
>    nav « Modération » (icône ShieldAlert). Cf JOURNAL 2026-06-07.
> 4. **Inventaire / rapports / réglages** (groupés) — *prochain*
>
> ⚠️ Règle non-négociable : **tous les endpoints backend servant ces écrans sont
> créés d'emblée sous `Depends(require_admin)`** (cf section Plateforme/Auth +
> JOURNAL chantier 4 phase C, règle confirmée par les étapes 1, 2 et 3).
> Pattern à copier : `POST /api/establishments`, `GET /api/fleet`,
> `GET /api/incidents/overview`.

Console de supervision **multi-établissements en lecture seule**. Livraison des
**6 écrans** alimentés par les **10 données** remontées (cf ARCHITECTURE §2.1).

Grandes briques à construire :

- **Ingestion** : implémentation réelle de `/api/ingest` (auth par API key 256
  bits, validation, persistance) + endpoints de pull pour le daemon client.
- **Modèle de données** : tables `sessions`, `incidents`, `reports`, `logs`,
  `hardware_stats`, `inventaire` + introduction d'**Alembic**.
- **Frontend** : scaffolding **React + TS + Vite + Tailwind**, sidebar + breadcrumb,
  identité visuelle Dialeo.
- **Temps réel** : flux **SSE** + toggle Pause (chantier dédié).
- **Écrans** : Dashboard global → Vue établissement → Reports → Inventaire/licences
  → Réglages console → Déploiements N2 (vue préparatoire).
- **Audit** : table `audit_log` + traçage A2 (connexions), A3 (requêtes entrantes,
  format compact), A4 (anomalies), A5 (exports).
- **Accès** : connexion de **Cloudflare Tunnel + Access (Email OTP)**.

---

## Phase N2 — Pilotage actif (cible : fin juin → début juillet 2026)

Les **4 actions** sont livrées **une par une**, chacune sous les **5 garde-fous**
(signature crypto, validation préalable, canary 12 h / 24-48 h, rollback auto,
audit trail — cf ARCHITECTURE §2.2 et §7.3).

Ordre de livraison acté :

1. **Push blacklist**
2. **Push system prompts**
3. **Push config Ollama**
4. **Redémarrage de services à distance**

Prérequis transverses à la phase N2 :

- Mécanique de **signature cryptographique** des ordres (génération de clés,
  certificats — chantier dédié).
- Pipeline **canary + rollback automatique**.
- Traçage **A1** (toutes actions N2) avec rétention longue.

---

## Hors phasage / ultérieur

- Console **multi-utilisateurs** effective (le modèle est prêt dès N1, l'activation
  viendra quand le besoin réel apparaît).
- Montée en charge **50+ établissements** (l'architecture est dimensionnée pour, la
  validation se fera à l'usage).

---

## Dette technique connue

À traiter au bon moment, sans urgence à ce stade :

- **`POST /api/establishments` non protégé** (phase 3.1) → doit passer derrière
  **Cloudflare Access** avant toute exposition externe (cf ARCHITECTURE §7.1).
- ~~**Timestamps SQLite sans fuseau** (phase 3.1)~~ — **RÉSOLU 2026-06-07
  (`v0.11.2-tz-utc`)** : type Pydantic centralisé `UtcDatetime` dans
  `app/schemas/_utc.py` (BeforeValidator wrap UTC + PlainSerializer Z), appliqué
  à TOUS les schémas de réponse (fleet, détail, auth, establishment, heartbeat,
  ingest). Front : helper `parseUtcIso` pour traiter défensivement toute string
  sans marqueur comme UTC. Cf JOURNAL 2026-06-07.
- **Migrations** → encore en `create_all` ; introduire **Alembic** quand le schéma
  N1 se fige (`create_all` n'altère pas les tables existantes). Workaround
  ponctuel pour phase 4-B : `app/scripts/migrate_phase_b.py` (ALTER idempotent).
- **Fleet dashboard — granularité historique non observée en prod** (chantier
  N1 étape 1, 2026-06-06) : `sessions_7j` et `trend_14d` reposent sur
  `granularite == 'jour'` + `periode` ISO date. Le contrat Pydantic autorise
  `'semaine'`/`'mois'` mais aucune ligne historique n'a encore été reçue en
  prod (collecteur M4 KO), donc le format réel émis n'a pas pu être vérifié.
  À reconfirmer quand les premières données arriveront ; le cas échéant,
  ajouter un parseur `2026-W23` / `2026-06` ou aligner le collecteur sur
  `granularite='jour'`. Cf JOURNAL 2026-06-06.
- **Fleet — health top-level ne reflète pas la dégradation au niveau service**
  (chantier N1 étape 2, 2026-06-06) : `compute_health` ne pondère que la
  fraîcheur + le `status` du heartbeat. Or `heartbeats.status` vaut toujours
  `"ok"` en prod aujourd'hui. Conséquence concrète : un établissement peut
  afficher 🟢 alors qu'un service est tombé (`sante_systeme.status_global="degraded"`,
  `dialeo_status.uvicorn_status="down"`, `daemon.consecutive_failures` élevé).
  Pour ces deux chantiers on s'appuie sur les **panneaux fins** de la page
  détail qui exposent ces signaux. Candidat à enrichir `compute_health` (et
  donc la pastille de la tuile) avec ces sources quand le fix du collecteur M4
  ramènera de la donnée fraîche et qu'on aura des exemples concrets de
  dégradation. Cf JOURNAL 2026-06-06.
- **Fleet — `ollama_status` jamais observé en prod** (chantier N1 étape 2,
  2026-06-06) : 0 ligne `raw_pushes` de type `ollama_status` au moment du
  build. Le panneau Ollama de la page détail est en place et lira la donnée
  quand elle arrivera ; en attendant l'UI affiche « Non rapporté ». À
  reconfirmer quand M4 émettra ce type.
- **Déploiement frontend — toujours rebuild `frontend/dist/` sur DialSup**
  (leçon 2026-06-07) : un bug « Dashboard affiche Erreur de chargement (HTTP 200) »
  apparu en prod alors que la suite Vitest était verte localement, traceable
  au fait qu'uvicorn DialSup sert `frontend/dist/` statique. Un `git pull` +
  `kickstart` ne rebuilde PAS le SPA — il faut explicitement
  `cd frontend && npm install && npm run build` puis recharger. Le hard-refresh
  navigateur seul ne suffit pas si la dist/ servie est ancienne. À ajouter dans
  la procédure de déploiement N1 (cf `docs/RESILIENCE.md` le moment venu).

---

## Plateforme / Auth admin (chantier 4)

Suivi détaillé dans `docs/JOURNAL.md`. Pour rappel :

- **Phase A — socle (`v0.7.0-auth-backend-password`, 31 mai 2026)** ✅
  livré : table `users`, login mdp, cookie session JWT, `/me`, `require_admin`.
- **Phase B — MFA TOTP (`v0.8.0-auth-mfa-totp`, 31 mai 2026)** — **DÉPLOYÉ EN PROD (2026-06-06)** ✅
  Login 2 étapes, enrôlement TOTP + URI otpauth, codes de récupération, lockout
  5/15 min, chiffrement at-rest. Bascule DialSup détaillée dans `docs/JOURNAL.md`
  (entrée 2026-06-06).
- **Phase C — frontend auth (`v0.9.0-auth-frontend`, 31 mai 2026)** — **DÉPLOYÉ EN PROD (2026-06-06)** ✅
  UI login 2 étapes + enrôlement MFA (QR + saisie manuelle) + 10 codes de
  récupération avec gate "j'ai sauvegardé", bouton Déconnexion, route guard
  `<RequireAuth>` sur toutes les pages console, intercepteur 401 global. Backend :
  `POST /api/establishments` sous `require_admin` (dette phase 3.1 levée, effective
  en runtime). Admin `gmd@dialeo.com` (id=1) enrôlé en MFA TOTP au 1er login
  post-upgrade, 10 codes de récupération sauvegardés hors-bande.

### Règles à appliquer aux futurs chantiers N1

- **Tout nouvel endpoint backend servant les écrans console** (Dashboard, Vue
  établissement, Reports, Déploiements N2, Inventaire/licences, Réglages) doit
  être déclaré **d'emblée sous `Depends(require_admin)`**. Pas de "on protégera
  plus tard" — c'est la leçon de la dette portée par `POST /api/establishments`
  depuis la phase 3.1. Pattern à copier : voir l'endpoint actuel.
- Les endpoints **client** (consommés par les Mac mini avec leur API key, type
  `/api/ingest` ou les futurs `GET /api/ingest/...`) restent sous
  `get_current_etablissement` (Bearer). Bien distinguer les deux familles dès
  la conception.
- Pour l'admin qui veut lire les données d'**un** établissement (ex. heartbeats),
  prévoir un endpoint dédié `/api/admin/establishments/{id}/...` sous
  `require_admin`, **distinct** du `/api/establishments/{id}/heartbeats` client.

### Risque connu — onglet fermé avant sauvegarde des codes de récup

À la confirmation d'enrôlement, les 10 codes sont affichés **une seule fois**.
Si l'utilisateur **ferme l'onglet** ou recharge la page avant d'avoir noté/
téléchargé les codes (ou avant de cocher "j'ai sauvegardé"), ils sont **perdus**
côté client (côté serveur ils sont déjà hashés, donc non récupérables). La
session reste valide grâce au cookie ; la seule conséquence est l'absence de
filet de secours en cas de perte du téléphone. **Mitigation actuelle** : la gate
"j'ai sauvegardé" + l'avertissement fort dans l'écran. **Mitigation future
(backlog)** : endpoint de régénération des codes de récupération côté admin
authentifié, à brancher dans l'écran "sécurité du compte" (phase D ou plus tard).

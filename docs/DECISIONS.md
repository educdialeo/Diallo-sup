# Décisions — Console de supervision Dialeo (Diallo-sup)

> **Projet clôturé le 2026-07-19** (`v1.0.0-final-cloture`). Ce fichier consigne
> les décisions structurantes prises pendant la vie du projet **et leur raison**,
> y compris les points restés **ouverts et non tranchés** au moment de l'arrêt.
> Sources : `git`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/JOURNAL.md`,
> `docs/RESILIENCE.md`, `CLAUDE.md`. **Rien n'est inventé ici** ; les points non
> documentés dans le dépôt sont explicitement marqués comme tels.

---

## Décisions actées (avec leur raison)

### D1 — Nom technique `Diallo-sup` conservé délibérément
Le repo s'appelle `Diallo-sup` (et non `dialeo-supervision`). Choix **volontaire et
ferme** : c'est le nom officiel dans le code, les chemins et la doc technique. Le nom
fonctionnel produit reste « Console de supervision Dialeo » côté client.
*Source : `CLAUDE.md`.*

### D2 — Auth admin maison comme socle intérimaire, en attendant Cloudflare Access
La cible d'architecture délègue l'authentification console à **Cloudflare Access
(Email OTP)**, sans auth applicative maison. Cloudflare n'ayant jamais été connecté,
un **socle d'auth admin maison** a été construit et **déployé** : mot de passe (phase A,
`v0.7.0`), puis MFA TOTP (phase B, `v0.8.0`) et frontend d'auth (phase C, `v0.9.0`),
tous **déployés en prod le 2026-06-06** (MFA admin `gmd@dialeo.com` actif). C'était le
verrou pragmatique en l'absence de la couche Cloudflare.
*Sources : `docs/ARCHITECTURE.md` §7.1, `docs/JOURNAL.md` (2026-06-06), `docs/ROADMAP.md`.*

### D3 — SQLite + `create_all`, Alembic différé
Persistance sur **SQLite**, tables créées via `create_all`. **Alembic** a été
volontairement **différé** jusqu'à ce que le schéma N1 se fige. Caveat assumé :
`create_all` **n'altère pas** une table existante → les évolutions de schéma en prod
ont été faites par **scripts ALTER idempotents ponctuels** (ex. `app/scripts/migrate_phase_b.py`).
*Sources : `CLAUDE.md`, `docs/ROADMAP.md` (dette technique).*

### D4 — Anonymisation des reports : RGPD by design, jamais de données élève nominatives
La console est un outil **vendeur** qui n'observe que des **agrégats anonymisés**.
Sur `POST /api/ingest` type `reports`, tout **champ identifiant** (prénom, nom, ids de
session/classe/connexion, établissement…) est **refusé par un `400` explicite**. Côté
lecture, la page Rapports fait un **SELECT explicite des seules colonnes sûres** : les
colonnes de contenu (`question`, `reponse`, `note_enseignant`) **ne sont jamais chargées**
(test dédié `test_recent_reports_NEVER_leak_content`). Défense en profondeur : même un
bug d'UI ne peut pas fuiter le contenu.
*Sources : `docs/ARCHITECTURE.md` §7.4, `docs/JOURNAL.md` (chantier N1 étape 4).*

### D5 — FastAPI sert le SPA statique ; origine locale en clair derrière Cloudflare Tunnel
Pas de Caddy : `app/main.py` sert `frontend/dist/` en **StaticFiles + fallback SPA**
(inerte en dev/CI/tests). En prod, l'origine tourne **en clair sur `127.0.0.1`**,
Cloudflare Tunnel + Access étant censés terminer le TLS et constituer l'unique point
d'entrée public (jamais connecté).
*Sources : `docs/ARCHITECTURE.md` §7, `CLAUDE.md`.*

### D6 — JWT stateless : logout non révocable, rotation `JWT_SECRET` comme option nucléaire
Le JWT de session est signé mais **non révocable côté serveur** : `logout` n'efface que
le cookie navigateur ; un token volé reste valide jusqu'à son `exp` (12 h). Pour invalider
**toutes** les sessions vivantes : **rotation du `JWT_SECRET`** (édition `.env` + `kickstart`).
Caveat inhérent au choix stateless, assumé.
*Source : `docs/RESILIENCE.md` (caveat « logout stateless »).*

### D7 — Secrets MFA : TOTP chiffré at-rest (Fernet), codes de récupération hashés SHA-256
Le secret TOTP est **chiffré at-rest** (Fernet, `TOTP_AT_REST_KEY`). Les 10 codes de
récupération sont **hashés en SHA-256** (haute entropie → pas besoin de bcrypt), affichés
en clair **une seule fois**, consommables à usage unique.
*Source : `docs/JOURNAL.md` (chantier 4 phase B).*

### D8 — Lockout : le compteur d'échecs ne se réinitialise que sur session complète
Verrou par compte : 5 essais / 15 min → `423 Locked`. **Le compteur ne reset QUE sur une
session complète réussie** (verify-totp OK / confirm OK), **jamais** sur le seul succès du
mot de passe → empêche le brute-force du second facteur TOTP (test
`test_password_ok_does_not_reset_failure_counter`).
*Source : `docs/JOURNAL.md` (chantier 4 phase B).*

### D9 — uvicorn sous launchd (RunAtLoad + KeepAlive)
Le service uvicorn tourne sous **launchd** (LaunchAgent `com.diallosup.uvicorn`, uid 501) :
démarrage au boot, redémarrage auto au crash. `WorkingDirectory` fixé au repo — **critique**
car la base SQLite est référencée en chemin **relatif**.
*Sources : `CLAUDE.md`, `docs/RESILIENCE.md`, `ops/com.diallosup.uvicorn.plist`.*

### D10 — Datetimes API en UTC explicite
Tous les `datetime` des réponses API sont sérialisés en **UTC explicite** (suffixe `Z`),
via un type Pydantic centralisé `UtcDatetime` ; le front traite défensivement toute string
sans marqueur comme UTC. Dette « timestamps sans fuseau » **résolue** (`v0.11.2-tz-utc`).
*Source : `docs/ROADMAP.md` (dette technique), `docs/JOURNAL.md` (2026-06-07).*

### D11 — Rebuild du frontend obligatoire à chaque déploiement DialSup
uvicorn sert `frontend/dist/` **statique** : un `git pull` + `kickstart` ne rebuilde **pas**
le SPA. Tout déploiement doit inclure `cd frontend && npm install && npm run build`, sinon
l'UI servie reste périmée (bug observé le 2026-06-07 : « Erreur de chargement » sur HTTP 200).
*Source : `docs/ROADMAP.md` (dette), `docs/JOURNAL.md` (2026-06-07).*

---

## Points restés ouverts et non tranchés

### O1 — Validation juriste de la liste anonymisée des derniers reports
La page Rapports expose une **liste anonymisée des derniers reports** (date + établissement
+ niveaux + mode pédagogique, **sans aucun contenu utilisateur**). Défendable (métadonnées
techniques), mais **restée à valider avec le juriste**. Bandeau RGPD ambré permanent en tête
de page en attendant. **Non tranché.**
*Source : `docs/ROADMAP.md` (Point ouvert RGPD), `docs/JOURNAL.md` (chantier N1 étape 4).*

### O2 — Throttling / rate-limit du login (dette phase B)
**Aucun rate-limit** par IP sur `POST /api/auth/login`. Contenu en local mono-user sur LAN,
mais à traiter **avant toute exposition externe** (Cloudflare Access ne suffit pas si
quelqu'un est déjà dans le tunnel). Jamais implémenté. **Non tranché.**
*Source : `docs/RESILIENCE.md` (dette : throttling).*

### O3 — Régénération des codes de récupération MFA
Si l'onglet est fermé avant sauvegarde, les 10 codes de récupération sont **perdus côté
client** (hashés côté serveur, donc non récupérables). Mitigation actuelle : gate « j'ai
sauvegardé ». Mitigation future envisagée mais **jamais construite** : endpoint de
régénération côté admin authentifié. **Backlog non traité.**
*Source : `docs/ROADMAP.md` (risque connu — onglet fermé).*

### O4 — Watchdog externe de liveness *(point soulevé en discussion, non tranché, non documenté in-repo)*
> Issu de discussions non versionnées (27/06/2026), consigné pour un repreneur — **teneur
> exacte, rien de plus** :

DialSup ne peut pas détecter sa propre panne (un système ne se surveille pas lui-même).
Idée d'un dead-man's switch hébergé hors du réseau domicile, envoyant un simple ping de vie,
sans aucune donnée élève ni école. À distinguer de la couche d'alertes N1. Jamais spécifié
ni codé.

### O5 — Hébergement cible : Mac mini local vs cloud souverain EU *(point soulevé en discussion, non tranché, non documenté in-repo)*
> Issu de discussions non versionnées (27/06/2026), consigné pour un repreneur — **teneur
> exacte, rien de plus** :

Hébergement cible : Mac mini local (point unique de défaillance) vs cloud souverain EU
(OVH / Scaleway / Outscale). La stack étant déjà portable, c'était une migration d'ops et
non une réécriture. Jamais arbitré.

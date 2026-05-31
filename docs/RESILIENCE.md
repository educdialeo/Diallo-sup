# Résilience — uvicorn DialSup sous launchd

> Sous-phase 3.4.B. Met le backend uvicorn de la console (DialSup, Mac mini M1)
> sous **launchd** : démarrage automatique au boot, redémarrage automatique en cas
> de crash, logs persistants. Réplique le pattern du repo Dialeo M4
> (`com.dialeo.uvicorn`, tag `v0.11.0-launchd-uvicorn`).

## Service

- **Type** : LaunchAgent (session utilisateur `serveur`, auto-login activé).
  Pas de LaunchDaemon : aucun besoin de root, tout est dans le home de `serveur`.
- **Label** : `com.diallosup.uvicorn`
- **Source canonique** : [`ops/com.diallosup.uvicorn.plist`](../ops/com.diallosup.uvicorn.plist)
- **Déployé dans** : `~/Library/LaunchAgents/com.diallosup.uvicorn.plist`
- **Domaine launchd** : `gui/501` (uid de `serveur`)
- **Commande** : `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **WorkingDirectory** : `/Users/serveur/Projects/Diallo-sup` — **critique** : la base
  SQLite est en chemin relatif (`./data/diallo_sup.db`) ; un mauvais dossier de
  travail créerait une base vide ailleurs.
- **RunAtLoad** : démarre au chargement et au boot.
- **KeepAlive** : relance automatique à tout arrêt (crash inclus).
- **Logs** : `~/Library/Logs/diallosup-uvicorn.log` (stdout + stderr).

## Installation (première fois)

```bash
mkdir -p ~/Library/LaunchAgents
cp /Users/serveur/Projects/Diallo-sup/ops/com.diallosup.uvicorn.plist ~/Library/LaunchAgents/
plutil -lint ~/Library/LaunchAgents/com.diallosup.uvicorn.plist
```

## Bascule (foreground → launchd)

```bash
# 1. Arrêter l'uvicorn foreground (Ctrl+C dans sa fenêtre Terminal)
# 2. Vérifier le port 8000 libre
lsof -nP -iTCP:8000 -sTCP:LISTEN     # doit ne rien renvoyer

# 3. Charger le service (syntaxe moderne)
launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.diallosup.uvicorn.plist

# 4. Vérifier
launchctl print gui/501/com.diallosup.uvicorn | grep -E "state|pid"
curl -s http://127.0.0.1:8000/health      # {"status":"ok",...}
```

## Commandes courantes (launchctl moderne)

| Action | Commande |
|---|---|
| Charger / démarrer | `launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.diallosup.uvicorn.plist` |
| Arrêter / décharger | `launchctl bootout gui/501/com.diallosup.uvicorn` |
| Redémarrer (tuer + relancer) | `launchctl kickstart -k gui/501/com.diallosup.uvicorn` |
| État / PID | `launchctl print gui/501/com.diallosup.uvicorn` |
| Recharger après modif du plist | `bootout` puis `cp` puis `bootstrap` |

> ⚠️ `KeepAlive=true` : un simple `kill <pid>` est suivi d'une **relance immédiate**.
> Pour arrêter réellement le service, utiliser **`bootout`**.

## Rollback (< 1 min) — retour au foreground

```bash
launchctl bootout gui/501/com.diallosup.uvicorn          # stoppe + décharge (KeepAlive off)
cd /Users/serveur/Projects/Diallo-sup
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000   # état initial
```

## Test de résilience (autorestart)

```bash
launchctl kickstart -k gui/501/com.diallosup.uvicorn   # tue le process
sleep 2
launchctl print gui/501/com.diallosup.uvicorn | grep pid   # un NOUVEAU pid doit apparaître
curl -s http://127.0.0.1:8000/health                       # de nouveau 200
```

## Notes

- Pas de warm-up (DialSup = FastAPI + SQLAlchemy, **pas** de modèle Ollama/Llama),
  donc reprise quasi immédiate après redémarrage.
- Pendant une brève coupure (~5–10 s), les clients M4 (collecteur + daemon
  supervisor) loggent des `ConnectError` puis reprennent en 202 au cycle suivant
  (clients conçus pour ne jamais lever d'exception).

---

## Auth admin de la console (chantier 4 phase A)

### Bootstrap (à faire une fois après `git pull` sur DialSup)

```bash
cd /Users/serveur/Projects/Diallo-sup
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m app.scripts.create_admin    # interactif : email + mdp (>= 12)
launchctl kickstart -k gui/501/com.diallosup.uvicorn   # recharge le code
```

`create_admin` génère `JWT_SECRET` dans `.env` s'il manque (idempotent ; un
secret existant n'est **jamais** régénéré, cf leçon Dialeo principal).

### Déploiement non-bloquant

Si `JWT_SECRET` n'est pas configuré, le service démarre quand même : un
**WARN** apparaît dans les logs (`[diallosup.auth] WARN: JWT_SECRET non
configuré …`), `/api/auth/*` renvoie **503**, mais `/api/ingest` et `/health`
fonctionnent normalement. → un `git pull` qui oublie le bootstrap **ne casse
pas l'ingestion**.

### Caveat « logout stateless » ⚠️

Le JWT est signé mais **non révocable côté serveur** : `POST /api/auth/logout`
n'efface que le cookie côté navigateur. **Un token volé reste valide jusqu'à
son `exp`** (12 h par défaut). Mitigations :

- Réduire `SESSION_TTL_HOURS` (au prix d'UX).
- **Option nucléaire** pour invalider toutes les sessions vivantes : rotation
  du `JWT_SECRET` (édite `.env`, supprime la ligne ou met une nouvelle valeur,
  `kickstart -k`) — tous les cookies en circulation deviennent invalides.
- Phase B (MFA TOTP) ne change pas ce caveat : c'est inhérent au JWT stateless.

### Dette : throttling (phase B)

**Aucun rate-limit** sur `POST /api/auth/login` à ce stade. En local mono-user
sur LAN, l'exposition est contenue, mais avant toute exposition externe
(Cloudflare Access ne suffit pas si quelqu'un est dans le tunnel) il faudra
**throttler** les tentatives par IP (ex. compteur en mémoire ou via un middleware
type `slowapi`), idéalement couplé à un blocage progressif. À traiter en
**phase B**, avec la MFA.

---

## MFA TOTP (chantier 4 phase B)

### Déploiement (à faire dans l'ordre, command-by-command)

```bash
cd /Users/serveur/Projects/Diallo-sup
git pull origin main
.venv/bin/pip install -e ".[dev]"              # ajoute pyotp + cryptography
.venv/bin/python -m app.scripts.migrate_phase_b   # ALTER TABLE users (idempotent)
.venv/bin/python -m app.scripts.init_secrets       # ajoute TOTP_AT_REST_KEY (idempotent)
launchctl kickstart -k gui/501/com.diallosup.uvicorn
```

Au premier login après upgrade, l'admin existant aura `totp_enrolled=False` →
flux d'enrôlement obligatoire (login → /totp/enroll → /totp/confirm).

### Décision : compteur d'échec NE RESET QUE sur session complète

Le compteur de lockout (5 échecs / 15 min) ne se remet à zéro **que sur
`verify-totp OK` ou `confirm OK`** (= établissement d'une session complète),
**jamais sur le succès du mot de passe seul**. Sinon, un attaquant qui aurait
le mot de passe pourrait brute-forcer le TOTP à l'infini en bouclant
`/login` + `/verify-totp`. Test dédié :
`test_password_ok_does_not_reset_failure_counter`.

### Tradeoffs assumés

- **`423 Locked` révèle l'état du compte.** L'attaquant voit qu'un email
  existe et qu'il est verrouillé (vs 401 pour email inconnu ou mdp faux).
  Acceptable car le bénéfice (clarté serveur + UX claire pour le user
  légitime) prime sur la fuite mineure d'énumération.
- **Lockout-as-DoS auto-résolu en 15 min.** Quelqu'un peut volontairement
  faire 5 mauvais mots de passe sur l'email d'un admin pour le verrouiller
  ; la fenêtre de 15 min limite l'impact et la valeur de l'attaque (un
  simple `register_failure` après expiration repart à zéro). Pas de
  reset manuel exposé en API à ce stade (compatible avec phase C).
- **`.env` porte désormais 2 secrets critiques** : `JWT_SECRET` (signature
  des cookies de session) **et** `TOTP_AT_REST_KEY` (chiffrement des
  secrets TOTP en BDD). Backup hors-bande de `.env` recommandé (au moins
  la `TOTP_AT_REST_KEY` : sans elle, plus aucun admin enrôlé ne peut
  vérifier son TOTP). En cas de perte, les utilisateurs ré-enrôlent
  (les codes de récupération les laissent rentrer une fois). Cf §
  caveat clé Fernet ci-dessous.

### Caveat clé Fernet (TOTP_AT_REST_KEY) perdue

Si `TOTP_AT_REST_KEY` est perdue/changée, **tous les secrets TOTP en base
deviennent illisibles** → chaque admin doit ré-enrôler. Les **codes de
récupération restent valides** (hash SHA-256 indépendant) : un admin peut
encore se logger une fois avec un code de récup, puis re-faire
`/totp/enroll` + `/confirm` pour repartir d'un nouveau secret. C'est la
ceinture de sécurité.

### Backlog Phase C (et au-delà)

- **Flux reset/ré-enrôlement TOTP** (perte de téléphone, codes de récup
  épuisés) : script CLI `python -m app.scripts.reset_totp <email>` qui
  vide `totp_secret` + `totp_enrolled=False` (admin local sur DialSup).
  Hors scope phase B.
- **Régénération de codes de récupération** côté API : à brancher quand
  l'écran "sécurité du compte" arrivera (phase C).
- **Throttling IP** (au-delà du throttle par compte) pour résister à un
  flood d'emails inconnus. Phase C ou plus tard.

### Risque connu (phase C) — onglet fermé avant sauvegarde des codes de récup

Les 10 codes de récupération sont affichés **une seule fois** à la
confirmation d'enrôlement. Si l'utilisateur ferme l'onglet, recharge la page,
ou contourne la case "j'ai sauvegardé", ils sont **perdus côté client**
(hashés en base, non récupérables). La session reste valide grâce au cookie ;
seule conséquence : plus de filet de secours en cas de perte du téléphone →
ré-enrôlement TOTP CLI requis (cf backlog ci-dessus). Cf `docs/ROADMAP.md`.

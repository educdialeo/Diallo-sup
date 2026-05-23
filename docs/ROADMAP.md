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
- **Timestamps SQLite sans fuseau** (phase 3.1) → les datetimes sont en UTC mais
  renvoyés sans suffixe `Z` (limitation SQLite). Donnée correcte, étiquetage à
  normaliser si un client en a besoin.
- **Migrations** → encore en `create_all` ; introduire **Alembic** quand le schéma
  N1 se fige (`create_all` n'altère pas les tables existantes).

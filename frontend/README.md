# Frontend — Console de supervision Dialeo

> **Pas encore scaffoldé.** Ce dossier matérialise l'emplacement et acte la stack
> du SPA. Le toolchain JS (et `node_modules`) sera initialisé au **chantier N1**,
> pas au chantier de fondation — afin de garder le commit de fondation propre.

## Stack actée (cadrage 23 mai 2026)

- **React** + **TypeScript**
- **Vite** (build statique)
- **TailwindCSS**

## Intégration

Le build statique produit par Vite (`frontend/dist/`) sera **servi directement
par FastAPI** (`StaticFiles` + fallback SPA). Pas de reverse proxy local : la
console est exposée derrière Cloudflare Tunnel + Access. Voir
[`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) §4.

## Identité visuelle (cible)

- Header avec wordmark **DiALEO**, accent **bleu craie `#7DB8E8`**, police **Inter**.
- Couleurs fonctionnelles : **vert sauge** (ok), **orange chaleureux** (alerte),
  **rouge brique** (critique).
- Navigation : **sidebar verticale fixe** + **breadcrumb** contextuel.
- Page d'accueil : **Dashboard global**.
- Rafraîchissement temps réel : **SSE** sur tous les écrans + **toggle Pause**.

## Scaffolding prévu (chantier N1)

```bash
# Depuis la racine du repo, à exécuter au chantier N1 (pas maintenant) :
npm create vite@latest frontend -- --template react-ts
# puis installation et configuration de TailwindCSS
```

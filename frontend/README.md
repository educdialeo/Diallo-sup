# Frontend — Console de supervision Dialeo

SPA de la console. **Ossature posée au chantier 2** (`v0.2.0-frontend-scaffold`) :
layout, navigation et charte Dialeo — **sans écrans réels** (ils arrivent feature
par feature au chantier N1).

## Stack

- **React 19** + **TypeScript**
- **Vite 7** (build statique + HMR)
- **TailwindCSS 4** (config CSS-first via `@theme` dans `src/index.css`)
- **React Router 7** (navigation des 6 écrans)
- **Inter** bundlé en local via `@fontsource/inter` (pas de CDN externe → souverain)
- **lucide-react** (icônes de la sidebar)
- **Vitest** + **Testing Library** (tests) · **ESLint** (lint)

Pas de ShadCN/Radix ni de store global (Zustand) : YAGNI à ce stade, ~5 composants
hand-roll possédés entièrement. Réévaluable quand les écrans N1 arriveront.

## Démarrage (dev — 2 process)

```bash
# Terminal 1 — backend (à la racine du repo)
make dev                 # uvicorn :8000

# Terminal 2 — frontend (ici)
make front-install       # 1re fois seulement
make front-dev           # Vite :5173
```

Vite proxifie `/api` et `/health` vers `127.0.0.1:8000` (cf `vite.config.ts`), donc
les `fetch` utilisent des URLs **relatives** et fonctionnent en dev comme en prod.
Ouvrir <http://127.0.0.1:5173>.

## Build (prod)

```bash
make front-build         # génère frontend/dist/
make dev                 # FastAPI sert le SPA sur http://127.0.0.1:8000
```

En prod, FastAPI sert `frontend/dist/` (StaticFiles + fallback SPA, cf
`app/main.py`). `dist/` n'est pas versionné. Voir [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) §4.

## Structure

```
src/
├── main.tsx            # entrée + BrowserRouter
├── App.tsx             # déclaration des 6 routes (défaut → /dashboard)
├── index.css           # Tailwind v4 + tokens charte Dialeo + Inter
├── lib/nav.ts          # config des 6 entrées de navigation
├── hooks/useHealth.ts  # sonde GET /health (preuve d'intégration)
├── components/         # Layout, Sidebar, Breadcrumb, HealthIndicator, StatusPill, PagePlaceholder
├── pages/              # 6 placeholders (Dashboard, Etablissement, Reports, Deployments, Inventory, Settings)
└── test/               # setup + smoke test (Vitest)
```

## Charte Dialeo (tokens dans `src/index.css`)

- Accent **bleu craie `#7DB8E8`** (`craie-400`) — boutons primaires, état actif sidebar.
- Statuts fonctionnels : **vert sauge** (`sauge-500`, OK), **orange chaleureux**
  (`chaleur-500`, warning), **rouge brique** (`brique-500`, critique).
- Police **Inter**, fond clair (`slate-50`).

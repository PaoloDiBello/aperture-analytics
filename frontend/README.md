# Aperture Analytics — Frontend

React 19 + TypeScript + Vite frontend for Aperture Analytics. Styled with
Tailwind CSS v4 and small shadcn-style primitives under `src/ui/`.

## Scripts

```bash
npm install          # install dependencies
npm run dev          # start Vite dev server (http://localhost:5173)
npm run build        # type-check (tsc) + production build into dist/
npm run preview      # preview the production build locally
```

## Setup

Point the app at the backend by copying the example env file:

```bash
cp .env.example .env.local
# VITE_API_BASE_URL=http://localhost:8000
```

## Project layout

```
src/
├── main.tsx            # entry point (imports index.css)
├── App.tsx             # landing (CSV upload) + workspace (assistant chat)
├── api.ts              # typed client for /api/upload and /api/query
├── types.ts            # DatasetPreview, UploadResponse, QueryResponse
├── index.css           # Tailwind v4 import + dark design tokens
├── lib/utils.ts        # cn() — clsx + tailwind-merge
├── components/
│   └── Answer.tsx      # tiny markdown-lite renderer for assistant answers
└── ui/                 # shadcn-style primitives (Button, Card, Input, Badge, Separator)
```

## Styling notes

- Tailwind v4 is wired through `@tailwindcss/vite` and the `@import "tailwindcss"`
  in `src/index.css`.
- The dark theme uses CSS variables (oklch) mapped to Tailwind tokens
  (`background`, `card`, `primary`, `muted`, `border`, …).
- The `@` alias (`@/lib/utils`) is configured in `vite.config.ts`.

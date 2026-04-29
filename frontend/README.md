# MinerU Medical RAG Frontend

React + TypeScript Web console for the MinerU-ready medical literature RAG project.

## Stack

- Vite
- React + TypeScript
- Tailwind CSS
- shadcn/ui-style local components
- lucide-react icons
- recharts charts
- React Router

## Local Development

Start the backend first:

```bash
cd ..
MEDRAG_EMBEDDING_BACKEND=hash MEDRAG_VECTOR_STORE=sqlite make dev
```

Start the frontend:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173`.

## Build

```bash
npm run build
npm run preview
```

## Environment

`VITE_API_BASE_URL` points to the FastAPI API prefix, for example:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Pages

- Dashboard
- Knowledge base list
- Knowledge base detail
- Documents
- Document detail with chunk search and filtering
- RAG QA with citations and retrieved chunks
- MinerU integration configuration
- Evaluation and analysis
- System settings

## Docker / Compose Suggestion

For production-style deployment, build the frontend with `npm run build` and serve `frontend/dist` through Nginx or any static file server. In docker-compose, add a `medrag-frontend` service that sets `VITE_API_BASE_URL` at build time and proxies `/api` to the FastAPI service.

## MinerU Integration Touchpoints

The frontend reads parser mode and MinerU URL from `GET /api/v1/config`. Real MinerU integration mainly changes the backend adapter in `backend/app/parsers/mineru.py`. If additional parse-task lifecycle APIs are added later, extend `frontend/src/lib/api.ts` and `frontend/src/pages/MinerUConfigPage.tsx`.


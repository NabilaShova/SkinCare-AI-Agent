# AI Customer Support Agent for Shopify Beauty & Skincare Stores

Production-ready AI customer support SaaS for Shopify beauty and skincare merchants. The platform combines Shopify product sync, RAG knowledge retrieval, LangGraph agent routing, order support, human escalation, and a modern admin dashboard.

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Frontend | Next.js 15, React, Tailwind CSS |
| Backend | Python FastAPI |
| Database | PostgreSQL 15 + pgvector |
| AI | OpenAI, LangChain, LangGraph, RAG |
| Auth | Shopify OAuth (scaffolded) |
| Runtime | Docker Compose |

## Features

- AI skincare consultant chat at `/chat`
- Product recommendations from synced Shopify catalog
- Ingredient compatibility and FAQ answers via RAG
- Order status lookup for demo order `#3452`
- Shipping, return, and policy answers from knowledge base
- Medical safety guardrails and human escalation detection
- Admin dashboard for conversations, products, knowledge, analytics, and settings
- Demo store seeded automatically on first startup

## Project Structure

```text
SkinCare-AI-Agent/
├── backend/                 # FastAPI app, agents, RAG, Shopify routes
│   └── app/
│       ├── api/routes/      # chat, conversations, shopify, analytics, auth
│       ├── db/              # models, init/seed, session
│       └── services/        # LangGraph agent + RAG retrieval
├── frontend/                # Next.js app and dashboard UI
├── docker-compose.yml       # postgres + backend + frontend
├── .env.example             # root env template for Docker
└── README.md
```

## Quick Start (Docker)

### 1. Create environment file

```bash
cp .env.example .env
```

Add your OpenAI key for best responses:

```env
OPENAI_API_KEY=sk-your-key-here
```

The app still runs without an OpenAI key using a local fallback responder backed by seeded catalog and policy data.

### 2. Start the stack

```bash
docker compose up --build
```

### 3. Open the app

- Customer chat UI: [http://localhost:3000/chat](http://localhost:3000/chat)
- Landing page: [http://localhost:3000](http://localhost:3000)
- Admin dashboard: [http://localhost:3000/dashboard](http://localhost:3000/dashboard)
- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

## Try These Prompts

Use the chat UI to test common flows:

- `I have oily, acne-prone skin. What moisturizer should I use?`
- `Can I use Niacinamide with Vitamin C?`
- `Where is my order #3452?`
- `Do you ship internationally?`
- `I want a simple morning and night routine.`
- `I have a severe rash and need a diagnosis.`

## AI Architecture

LangGraph orchestrates specialized routing:

1. Intent Classifier
2. Product Knowledge Agent
3. Order Support Agent
4. Policy & FAQ Agent
5. Recommendation Agent
6. Human Escalation Agent

Each response uses:

- Store product catalog from PostgreSQL
- Knowledge chunks and embeddings from uploaded/seeded documents
- Conversation profile memory stored on the conversation record
- Safety rules for medical and escalation scenarios

## Database

On startup the backend:

1. Enables the `vector` extension
2. Creates all tables
3. Seeds a demo Shopify store: `Glow Beauty Co.`
4. Seeds 8 skincare products, 4 policy/FAQ documents, 1 demo order, and starter conversations

Main tables:

- `stores`
- `products`
- `customers`
- `orders`
- `conversations`
- `messages`
- `documents`
- `embeddings`
- `escalations`

## API Endpoints

### Chat

- `POST /api/chat/start`
- `POST /api/chat/message`
- `GET /api/chat/{conversation_id}`

### Admin Conversations

- `GET /api/conversations`
- `GET /api/conversations/{id}`
- `POST /api/conversations/message`
- `POST /api/conversations/escalate`

### Shopify

- `GET /api/shopify/oauth/connect`
- `POST /api/shopify/sync`
- `GET /api/shopify/products`

## Local Development Without Docker

### Backend

```bash
cd backend
cp .env.example .env
pip install .
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm install --legacy-peer-deps
npm run dev
```

You still need PostgreSQL with pgvector running locally, or use Docker only for Postgres:

```bash
docker compose up postgres -d
```

## Environment Variables

### Root / Docker (`.env`)

| Variable | Description |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI API key for chat + embeddings |
| `OPENAI_CHAT_MODEL` | Chat model, default `gpt-4o-mini` (use `gpt-4o` in production) |
| `OPENAI_INTENT_MODEL` | Intent classifier model |
| `OPENAI_EMBEDDING_MODEL` | Embedding model, default `text-embedding-3-small` |
| `RAG_TOP_K` / `RAG_MIN_SCORE` | Knowledge retrieval tuning |
| `PRODUCT_TOP_K` / `CHAT_HISTORY_LIMIT` | Product ranking and memory window |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `SHOPIFY_API_KEY` | Shopify app API key |
| `SHOPIFY_API_SECRET` | Shopify app secret |
| `SHOPIFY_APP_URL` | App URL for OAuth callbacks |
| `DEMO_STORE_ID` | Demo store id, default `1` |

### Backend (`backend/.env`)

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string |
| `PGVECTOR_DIMENSION` | Embedding vector size |
| `SHOPIFY_SCOPES` | Shopify OAuth scopes |

### Frontend (`frontend/.env.local`)

| Variable | Description |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Backend base URL |
| `NEXT_PUBLIC_SHOPIFY_APP_URL` | Shopify app URL |

## Production Deployment Log

All implementation steps and the manual production checklist live in:

`DEPLOYMENT_LOG.txt`

## Production Deployment Roadmap

You are past local demo. Move to production in this order:

### Phase 1 — Production infrastructure (now)

1. Push the repo to GitHub/GitLab/Bitbucket.
2. Set production secrets:
   - `OPENAI_API_KEY`
   - `SHOPIFY_API_KEY` / `SHOPIFY_API_SECRET`
   - `POSTGRES_PASSWORD`
   - `CORS_ORIGINS` (your real frontend URL)
   - `NEXT_PUBLIC_API_URL` (your public API URL)
3. Deploy with one of:
   - **Render Blueprint**: use the included `render.yaml`
   - **Docker Compose production**: `docker compose -f docker-compose.prod.yml up --build -d`
4. Use production Dockerfiles:
   - `backend/Dockerfile.prod` (no hot reload, 2 workers)
   - `frontend/Dockerfile.prod` (Next.js build + `npm start`)
5. Point a custom domain and HTTPS to frontend + API.

### Phase 2 — Real Shopify integration

1. Create a Shopify Partner app and configure OAuth redirect URLs.
2. Implement full OAuth token exchange in `backend/app/api/routes/auth.py`.
3. Build product/order/customer sync in `backend/app/services/shopify_sync.py`.
4. Schedule sync jobs (cron or background worker) so catalog data stays current.
5. Replace demo seed data with live store records per tenant.

### Phase 3 — SaaS hardening

1. Multi-tenant isolation by `store_id` on every query.
2. Admin authentication (Shopify session or JWT for dashboard).
3. Rate limiting and abuse protection on `/api/chat/*`.
4. File upload pipeline for PDFs/manuals with async embedding jobs.
5. Observability: structured logs, error tracking (Sentry), AI latency metrics.
6. Backups and migration strategy for PostgreSQL.

### Phase 4 — Go-to-market

1. Shopify App Store listing and compliance review.
2. Billing (Shopify Billing API or Stripe).
3. Merchant onboarding flow: connect store → sync catalog → upload policies → enable chat widget.
4. Embed chat widget on storefront theme or checkout extension.

### Recommended production `.env`

```env
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL=gpt-4o
OPENAI_INTENT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
SHOPIFY_API_KEY=...
SHOPIFY_API_SECRET=...
SHOPIFY_APP_URL=https://app.yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
CORS_ORIGINS=https://app.yourdomain.com
POSTGRES_PASSWORD=strong-password
ENVIRONMENT=production
```

### Deploy on Render

1. Connect your Git repo in Render.
2. Choose **New Blueprint** and select `render.yaml`.
3. Fill secret env vars when prompted.
4. Ensure `DATABASE_URL` uses the `postgresql+psycopg://` prefix if needed.
5. Set `NEXT_PUBLIC_API_URL` to the deployed API service URL.

## Chat Accuracy Improvements

Recent upgrades in this repo:

- **LLM intent classification** with regex fallback
- **Intent-specific prompts** and temperature tuning per agent type
- **Profile-aware retrieval** (skin type, concerns, budget remembered across turns)
- **Hybrid product search** (semantic embeddings + keyword + profile weighting)
- **Product catalog embeddings** indexed at startup
- **Conversation-aware retrieval queries** using recent user messages
- **Grounding rules** so the model only uses provided catalog/policy/order context
- **Fixed order lookup** so the bot no longer guesses order `#3452` without a number

To maximize accuracy in production:

1. Set `OPENAI_API_KEY` (required for best results).
2. Use `OPENAI_CHAT_MODEL=gpt-4o` for final responses.
3. Keep `OPENAI_EMBEDDING_MODEL=text-embedding-3-small` for RAG.
4. Upload real store policies and ingredient guides into the knowledge base.
5. Sync live Shopify products so recommendations match inventory.
6. Restart backend after deploy so `ensure_product_indexes()` rebuilds product embeddings.

## Current Status

Implemented now:

- Dockerized local development
- Production Dockerfiles and `docker-compose.prod.yml`
- Render Blueprint (`render.yaml`)
- Customer chat frontend
- Database schema, seed data, and pgvector extension
- LangGraph-based agent routing with improved accuracy
- RAG retrieval over seeded knowledge documents and product embeddings
- Product recommendation and order support using demo data
- Admin conversation viewer wired to the database

Planned next:

- Full Shopify OAuth onboarding and live product sync
- Document upload UI and async embedding pipeline
- Real-time human takeover workflow
- Multi-tenant store isolation and production auth
- Analytics backed by live conversation metrics

## Troubleshooting

### Chat returns generic fallback responses

Set `OPENAI_API_KEY` in `.env`, then restart:

```bash
docker compose down
docker compose up --build
```

### Frontend cannot reach backend

Confirm `NEXT_PUBLIC_API_URL=http://localhost:8000` and that the backend is healthy at [http://localhost:8000/health](http://localhost:8000/health).

### Database reset

```bash
docker compose down -v
docker compose up --build
```

This recreates PostgreSQL and reseeds demo data.

### Re-index product embeddings after upgrade

Restart the backend container. On startup it runs `ensure_product_indexes()` for all stores.

## License

Private project scaffold for a Shopify beauty support SaaS platform.

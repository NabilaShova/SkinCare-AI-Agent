# AI Customer Support Agent for Shopify Beauty & Skincare Stores

Production-ready AI customer support SaaS for Shopify beauty and skincare merchants. The platform combines Shopify OAuth and product sync, RAG knowledge retrieval, LangGraph agent routing, order support, human escalation, and an admin dashboard.

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Frontend | Next.js 15, React, Tailwind CSS |
| Backend | Python FastAPI |
| Database | PostgreSQL 15 + pgvector |
| AI | OpenAI, LangChain, LangGraph, RAG |
| Auth | Shopify OAuth, admin API key |
| Runtime | Docker Compose, Render Blueprint |

## Features

- AI skincare consultant chat at `/chat` and embeddable widget at `/embed/chat?store_id=N`
- Shopify storefront chat button via theme snippet (`integrations/shopify/glow-beauty-chat-widget.liquid`)
- Product recommendations from synced Shopify catalog
- Ingredient compatibility and FAQ answers via RAG
- Order status lookup when order number is provided
- Shipping, return, and policy answers from knowledge base
- Medical safety guardrails and human escalation detection
- Admin dashboard for conversations, products, knowledge, analytics, and settings
- Shopify OAuth connect + catalog sync
- Knowledge document upload (`.txt`, `.md`, `.pdf`)
- Demo catalog auto-seeded on first deploy for empty databases

## Live Production (Render)

| Service | URL |
| --- | --- |
| Frontend | https://skincare-frontend-z72h.onrender.com |
| API | https://skincare-api-68pp.onrender.com |
| Chat | https://skincare-frontend-z72h.onrender.com/chat |
| Settings | https://skincare-frontend-z72h.onrender.com/dashboard/settings |
| Products | https://skincare-frontend-z72h.onrender.com/dashboard/products |
| Knowledge | https://skincare-frontend-z72h.onrender.com/dashboard/knowledge |
| Health | https://skincare-api-68pp.onrender.com/health |

**Connected dev store:** `glow-beauty-dev-dmf5uuka.myshopify.com`  
**Shopify OAuth redirect URL:** `https://skincare-api-68pp.onrender.com/api/auth/callback`

Full deployment history and step-by-step ops guide: `DEPLOYMENT_LOG.txt`

## Shopify storefront chat widget

Merchants can add a floating chat button to their Shopify theme:

1. Paste `integrations/shopify/glow-beauty-chat-widget.liquid` into `theme.liquid` before `</body>`
2. Set `skincare_ai_store_id` to the merchant's Store ID
3. Preview the theme and click the chat button

**Test embed without Shopify:**

```
https://skincare-frontend-z72h.onrender.com/embed/chat?store_id=3
```

**Full merchant onboarding guide (subscription + integration):** `docs/SHOPIFY_STORE_OWNER_GUIDE.md`

## Store IDs (Important)

This app supports multiple stores in one database. Each connected Shopify shop gets its own numeric **Store ID**.

| Store ID | Domain | Products | Notes |
| --- | --- | --- | --- |
| `1` | `demo-glow-beauty.myshopify.com` | 8 demo products | Auto-seeded on first deploy (Ceramide Barrier Repair Cream, Gentle Foaming Cleanser, etc.) — **not** from your Shopify admin |
| `3` | `glow-beauty-dev-dmf5uuka.myshopify.com` | **120 live products** | **Your real connected Shopify store** — use this ID in the dashboard |

### Which Store ID to use

Use **Store ID `3`** for:

- Dashboard → Products
- Dashboard → Knowledge uploads
- Dashboard → Settings → Sync now
- Chat accuracy (set `DEMO_STORE_ID=3` on the API service in Render)

To confirm your Store ID: open **Settings** → **Connected stores** and note the `id` next to your shop domain.

### Catalog (120 products)

Store ID `3` is synced with **120 skincare products** (cleansers, serums, moisturizers, sunscreens, masks, exfoliants, eye care, body care, routine sets, and more). After importing or editing products in Shopify, run **Settings → Sync now** so chat and the dashboard stay up to date.

### Adding or updating products

Products are managed in **Shopify Admin**, not in this app.

**Option A — Bulk import (`glow-beauty-products-import.csv`, 120 products)**

1. Set store currency in Shopify Admin → **Settings** → **Store details** (BDT if using the provided CSV as-is, or USD and adjust prices before import)
2. **Products** → **Import** → upload `knowledge-base/glow-beauty-products-import.csv`
3. Dashboard → **Settings** → Store ID `3` → **Sync now**
4. Dashboard → **Products** → Store ID `3` — you should see **120 products**

The CSV includes 120 trending-inspired items with skin-type and concern tags for better AI matching. Regenerate with:

```bash
py -3 scripts/generate_product_csv.py
```

**Option B — Add one product manually**

1. Shopify Admin → **Products** → **Add product**
2. Fill title, description, price (in BDT), tags, and product type (tags help AI matching)
3. Dashboard → **Settings** → Store ID `3` → **Sync now**
4. Dashboard → **Products** → Store ID `3` to verify

### Removing demo products

There is no in-app delete for products. Demo items on Store ID `1` can be ignored, or removed from Postgres if you no longer need the demo store. Always confirm the store domain before deleting data.

## Project Structure

```text
SkinCare-AI-Agent/
├── backend/                 # FastAPI app, agents, RAG, Shopify routes
│   └── app/
│       ├── api/routes/      # chat, conversations, shopify, knowledge, auth
│       ├── db/              # models, init/seed, session
│       └── services/        # LangGraph agent, RAG, Shopify sync
├── frontend/                # Next.js app and dashboard UI
├── knowledge-base/          # Policy/FAQ files + Shopify product import CSV (BDT)
├── scripts/                 # generate_product_csv.py and production sync helpers
├── docker-compose.yml       # Local: postgres + backend + frontend
├── docker-compose.prod.yml  # Production Docker Compose
├── render.yaml              # Render Blueprint (free tier)
├── DEPLOYMENT_LOG.txt       # Full deployment + troubleshooting guide
├── render-env-values.txt    # Production env reference
└── README.md
```

## Quick Start (Docker — Local)

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

Locally, the demo store uses **Store ID `1`** with 8 seeded skincare products.

## Try These Prompts

Use the chat UI to test common flows:

- `I have oily, acne-prone skin. What moisturizer should I use?`
- `Can I use Niacinamide with Vitamin C?`
- `Do you ship internationally?`
- `What is your return policy?`
- `I want a simple morning and night routine.`
- `I have a severe rash and need a diagnosis.`

Upload the files in `knowledge-base/` via **Dashboard → Knowledge** (Store ID `3`) for policy, ingredient, and skincare consultation answers. See `knowledge-base/README.txt` for the recommended upload order (includes skin-types, concerns, routine formulas, and compatibility guides).

## AI Architecture

LangGraph orchestrates specialized routing:

1. Intent Classifier (LLM + regex fallback)
2. Product Recommendation Agent
3. Ingredient Question Agent
4. Order Support Agent
5. Policy & FAQ Agent (topic-aware: shipping vs returns)
6. Medical Safety + Human Escalation Agents

Each response uses:

- Store product catalog from PostgreSQL (synced from Shopify)
- Knowledge chunks and embeddings from uploaded documents
- **Learned chat FAQs** promoted from helpful customer conversations
- Conversation profile memory (skin type, concerns, preferences)
- Safety rules for medical and escalation scenarios

### Learning from chat (continuous improvement)

This app does **not** retrain the OpenAI model. Instead it uses **RAG learning**:

1. Customer clicks **Yes** (helpful) under an assistant reply in `/chat`
2. Backend saves that **question + answer** pair as a new knowledge document (`chat-learned-message-*.txt`)
3. The pair is embedded and indexed like uploaded policy files
4. Future similar questions retrieve the learned FAQ with a small relevance boost

View learned files in **Dashboard → Knowledge** (filenames start with `chat-learned-message-`).

To disable auto-learning, set on the API service:

```env
CHAT_AUTO_LEARN_ON_FEEDBACK=false
```

## Database

On startup the backend:

1. Enables the `vector` extension (with graceful fallback if unavailable)
2. Creates all tables
3. Seeds demo data when the database is empty (`ensure_minimum_store()`), or when `SEED_DEMO_DATA=true`

Main tables: `stores`, `products`, `customers`, `orders`, `conversations`, `messages`, `documents`, `embeddings`, `escalations`

## API Endpoints

### Chat

- `POST /api/chat/start`
- `POST /api/chat/message`
- `POST /api/chat/feedback` — helpful / not helpful; promotes Q&A to knowledge on helpful
- `GET /api/chat/{conversation_id}`

### Admin

- `GET /api/conversations`
- `GET /api/conversations/{id}`
- `POST /api/conversations/message`
- `POST /api/conversations/escalate`
- `GET /api/knowledge`
- `POST /api/knowledge/upload`
- `DELETE /api/knowledge/{document_id}`

### Shopify & Auth

- `GET /api/auth/start` — begin Shopify OAuth
- `GET /api/auth/callback` — OAuth callback
- `GET /api/auth/status` — list connected stores (admin)
- `POST /api/shopify/sync?store_id=3` — sync catalog from Shopify
- `GET /api/shopify/products?store_id=3` — list synced products

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
| `SHOPIFY_SCOPES` | Default: `read_products,read_orders,read_content` |
| `ADMIN_API_KEY` | Dashboard admin key |
| `JWT_SECRET` | Token signing secret |
| `DEMO_STORE_ID` | Default store for chat when none specified (use `3` in production) |
| `SEED_DEMO_DATA` | `true` locally; `false` on Render production |

### Production tuning (Render → skincare-api)

```env
OPENAI_CHAT_MODEL=gpt-4o
OPENAI_INTENT_MODEL=gpt-4o-mini
RAG_TOP_K=6
PRODUCT_TOP_K=6
CHAT_HISTORY_LIMIT=16
DEMO_STORE_ID=3
SEED_DEMO_DATA=false
```

### Frontend (`frontend/.env.local` or Render → skincare-frontend)

| Variable | Description |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Backend base URL |
| `NEXT_PUBLIC_SHOPIFY_APP_URL` | Shopify app URL |
| `NEXT_PUBLIC_DEMO_STORE_ID` | Store ID for dashboard and chat branding (use `3` in production) |
| `NEXT_PUBLIC_STORE_NAME` | Fallback store name in sidebar if API lookup fails |

## Deploy on Render

1. Connect the GitHub repo (`NabilaShova/SkinCare-AI-Agent`, branch `main`).
2. Choose **New Blueprint** and select `render.yaml`.
3. Enter secrets: `OPENAI_API_KEY`, `ADMIN_API_KEY`, `JWT_SECRET`, Shopify credentials.
4. Set env URLs after first deploy (see `render-env-values.txt`).
5. Redeploy **skincare-frontend** after changing any `NEXT_PUBLIC_*` variable.
6. Connect Shopify store via **Settings** → enter shop domain → authorize.
7. Set `DEMO_STORE_ID` to your connected store ID (e.g. `3`).
8. Upload knowledge files from `knowledge-base/` and run **Sync now**.

## Chat Accuracy Improvements

Implemented in this repo:

- LLM intent classification with regex fallback
- Intent-specific prompts and temperature tuning
- Topic-aware policy answers (shipping vs returns)
- Profile-aware retrieval (skin type, concerns, budget)
- Hybrid product search (semantic + keyword + profile weighting)
- Product catalog embeddings indexed after sync
- Grounding rules so the model uses only provided context

To maximize accuracy in production:

1. Set `OPENAI_API_KEY` and `OPENAI_CHAT_MODEL=gpt-4o`
2. Set `DEMO_STORE_ID=3` so chat uses your live catalog
3. Upload policies from `knowledge-base/` (Store ID `3`)
4. Sync Shopify after adding or editing products
5. Re-upload knowledge files after backend updates (improved chunking)

## Current Status

### Completed

- Dockerized local development + production Dockerfiles
- Render Blueprint deployed (free tier)
- Customer chat frontend with error handling and starter prompts
- LangGraph agent routing + RAG pipeline
- Shopify OAuth connect and product sync
- Partial sync when customer API returns 403 (products still sync)
- Knowledge upload API + dashboard UI
- Admin API key auth and rate limiting
- Policy FAQ routing fix (distinct shipping vs return answers)
- Production URLs live on Render
- Live Shopify dev store connected (**120 products**, Store ID `3`)
- Evidence-based skincare knowledge guides (skin types, concerns, routines, actives, compatibility)
- Concern-aware product recommendations and ingredient compatibility follow-ups
- Dashboard sidebar fixes (active nav, store name, Analytics links)
- Customer-facing chat copy uses **our store** / **we carry** (not “your catalog”)

### Optional next steps

- Upload full knowledge-base pack to Store ID `3` (if not already done)
- Shopify Protected Customer Data approval for full customer/order sync
- Scheduled sync (`scripts/production_sync.ps1` / `.sh`)
- Custom domain and paid Render tier (faster cold starts)
- Shopify App Store listing and billing
- Default dashboard Store ID to connected store instead of `1`

## Troubleshooting

### Dashboard shows demo products (Ceramide Cream, Foaming Cleanser, etc.)

You are viewing **Store ID `1`** (demo catalog). Switch to **Store ID `3`** on the Products page, or check **Settings → Connected stores** for your real store ID.

### Chat recommends wrong or demo products

Set `DEMO_STORE_ID=3` on the Render API service and `NEXT_PUBLIC_DEMO_STORE_ID=3` on the frontend, then redeploy both. Run **Sync now** for Store ID `3` and confirm **120 products** on Dashboard → Products.

### Chat returns generic or garbled policy answers

1. Confirm `OPENAI_API_KEY` is set on Render
2. Upload knowledge files from `knowledge-base/` to Store ID `3`
3. Re-upload after backend deploys (chunk format improvements)

### Shopify sync 403 on customers

Expected without Shopify Protected Customer Data approval. Products still sync; customers/orders are skipped with warnings.

### Frontend cannot reach backend

Confirm `NEXT_PUBLIC_API_URL` matches the live API URL and redeploy the frontend after changes.

### Database reset (local only)

```bash
docker compose down -v
docker compose up --build
```

This recreates PostgreSQL and reseeds demo data locally.

## License

Private project for a Shopify beauty support SaaS platform.

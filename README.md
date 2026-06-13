# AI Customer Support Agent for Shopify Beauty & Skincare Stores

Production-ready AI customer support SaaS for Shopify beauty and skincare merchants. The platform combines Shopify OAuth and product sync, RAG knowledge retrieval, LangGraph agent routing, order support, human escalation, an admin dashboard, and a **storefront-embeddable chat widget**.

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Frontend | Next.js 15, React, Tailwind CSS 3.4 |
| Backend | Python FastAPI |
| Database | PostgreSQL 15 + pgvector |
| AI | OpenAI, LangChain, LangGraph, RAG |
| Auth | Shopify OAuth, admin API key |
| Runtime | Docker Compose, Render Blueprint |

## Features

- AI beauty advisor chat at `/chat?store_id=N`
- **Embeddable storefront widget** at `/embed/chat?store_id=N` + Shopify theme snippet
- Concern-aware recommendations (skin + hair: acne, dryness, hair fall, dandruff, frizz, etc.)
- Product recommendations from synced Shopify catalog
- Ingredient compatibility and FAQ answers via RAG
- **Chat learning** — helpful answers promoted into knowledge base
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
| Chat | https://skincare-frontend-z72h.onrender.com/chat?store_id=3 |
| Embed chat | https://skincare-frontend-z72h.onrender.com/embed/chat?store_id=3 |
| Settings | https://skincare-frontend-z72h.onrender.com/dashboard/settings |
| Products | https://skincare-frontend-z72h.onrender.com/dashboard/products |
| Knowledge | https://skincare-frontend-z72h.onrender.com/dashboard/knowledge |
| Health | https://skincare-api-68pp.onrender.com/health |

**Connected dev store:** `glow-beauty-dev-dmf5uuka.myshopify.com` (Store ID **3**)  
**Shopify OAuth redirect URL:** `https://skincare-api-68pp.onrender.com/api/auth/callback`

| Doc | Purpose |
| --- | --- |
| `DEPLOYMENT_LOG.txt` | Full deployment history, local Docker fixes, ops checklist |
| `render-env-values.txt` | Copy-paste Render environment variables |
| `docs/SHOPIFY_STORE_OWNER_GUIDE.md` | Merchant subscription + widget integration |
| `docs/WEBSITE_INTEGRATION_GUIDE.md` | Integrate the agent on any non-Shopify website |
| `docs/MERCHANT_ONBOARDING_KIT.md` | Operator checklist, QA script, handoff template |
| `docs/MERCHANT_WELCOME_EMAIL.txt` | Welcome email template for new merchants |
| `docs/HAIR_PRODUCTS_SETUP.md` | Import 55 hair products + knowledge + test prompts |
| `knowledge-base/README.txt` | Knowledge upload + product CSV import |
| `integrations/shopify/README.txt` | Storefront widget install steps |
| `integrations/web/README.txt` | Non-Shopify website widget install steps |

## Shopify storefront chat widget

Add a floating chat button to any Shopify theme:

1. Open `integrations/shopify/glow-beauty-chat-widget.liquid`
2. Set `skincare_ai_store_id` to the merchant's Store ID
3. Shopify Admin → **Themes → Edit code** → paste into `theme.liquid` before `</body>`
4. **Preview** theme → click the pink chat button (bottom-right)

**Test embed without Shopify:**

```
https://skincare-frontend-z72h.onrender.com/embed/chat?store_id=3
```

**How it works:** The theme loads an iframe pointing at your hosted `/embed/chat` page. Chat API calls go to your backend from the iframe origin (no CORS issues). Each merchant is isolated by `store_id`.

## Store IDs (Important)

This app supports multiple stores in one database. Each connected Shopify shop gets its own numeric **Store ID**.

| Store ID | Domain | Products | Notes |
| --- | --- | --- | --- |
| `1` | `demo-glow-beauty.myshopify.com` | 8 demo products | Auto-seeded locally — not from Shopify admin |
| `3` | `glow-beauty-dev-dmf5uuka.myshopify.com` | **120+ live products** | **Production connected store** |

### Which Store ID to use

Use **Store ID `3`** for:

- Dashboard → Products, Knowledge, Settings → Sync now
- Chat and embed URLs (`?store_id=3`)
- Theme widget snippet (`skincare_ai_store_id = 3`)
- Render env: `DEMO_STORE_ID=3`, `NEXT_PUBLIC_DEMO_STORE_ID=3`

Confirm in **Settings → Connected stores** — note the `id` next to your shop domain.

### Catalog and product import

Products are managed in **Shopify Admin**, then synced into this app.

| CSV | Items | Currency |
| --- | --- | --- |
| `glow-beauty-products-import.csv` | 120 skincare | USD |
| `glow-beauty-hair-care-import.csv` | 55 hair care | USD |

**Import steps:**

1. Shopify Admin → **Settings → Store details** → currency **USD**
2. **Products → Import** → upload each CSV
3. Dashboard → **Settings** → Store ID `3` → **Sync now**
4. Dashboard → **Products** → expect **~175** products after both imports

Regenerate CSVs:

```bash
py -3 scripts/generate_product_csv.py
py -3 scripts/generate_hair_care_csv.py
```

See `knowledge-base/README.txt` for full import and knowledge upload instructions.

## Project Structure

```text
SkinCare-AI-Agent/
├── backend/                 # FastAPI app, agents, RAG, Shopify routes
│   └── app/
│       ├── api/routes/      # chat, conversations, shopify, knowledge, auth
│       ├── db/              # models, init/seed, session
│       └── services/        # LangGraph agent, RAG, Shopify sync
├── frontend/                # Next.js app, dashboard, chat, embed
│   ├── app/chat/            # Full-page customer chat
│   ├── app/embed/chat/      # Iframe-friendly embed chat
│   └── components/          # chat-panel, chat-page-with-store, side-nav
├── docs/                    # Merchant guides, onboarding kit, hair setup
├── integrations/shopify/    # Theme widget Liquid + README
├── integrations/web/        # Non-Shopify website widget loader + README
├── knowledge-base/          # Policies, guides, product import CSVs (USD)
├── scripts/                 # CSV generators, production sync helpers
├── docker-compose.yml
├── render.yaml              # Render Blueprint
├── DEPLOYMENT_LOG.txt
├── render-env-values.txt
└── README.md
```

## Quick Start (Docker — Local)

**Recommended on Windows** when Python is not installed locally. Requires Docker Desktop.

### 1. Create environment file

From the project root:

```bash
cp .env.example .env
```

Add your OpenAI key (optional for local UI; required for live AI chat):

```env
OPENAI_API_KEY=sk-your-key-here
```

Shopify OAuth keys can stay empty for local dashboard and demo chat testing.

Optional: copy `frontend/.env.example` to `frontend/.env` if you run the frontend outside Docker.

### 2. Start the stack

```bash
docker compose up --build -d
```

Services:

| Service | Image / build | Port |
| --- | --- | --- |
| postgres | `pgvector/pgvector:pg15` | 5432 |
| backend | `./backend` (FastAPI + psycopg) | 8000 |
| frontend | `./frontend` (Next.js 15 dev) | 3000 |

The frontend container runs `npm install` on start and keeps `node_modules` in a named Docker volume so bind-mounting the source tree does not hide installed packages.

View logs:

```bash
docker compose logs -f frontend
docker compose logs -f backend
```

Stop:

```bash
docker compose down
```

### 3. Open the app

| Page | URL |
| --- | --- |
| Landing | http://localhost:3000 |
| Chat | http://localhost:3000/chat?store_id=1 |
| Embed chat | http://localhost:3000/embed/chat?store_id=1 |
| Dashboard | http://localhost:3000/dashboard |
| API docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |

Locally, **Store ID `1`** has 8 seeded demo products (`SEED_DEMO_DATA=true`, `DEMO_STORE_ID=1` in root `.env`).

## Try These Prompts

- `I have oily, acne-prone skin. What moisturizer should I use?`
- `Can I use Niacinamide with Vitamin C?`
- `Can I use retinol and salicylic acid together?` → then `Yes please`
- `What shampoo helps with hair fall in humid weather?`
- `Do you ship internationally?`
- `I want a simple morning and night routine.`

Upload files from `knowledge-base/` via **Dashboard → Knowledge** (Store ID `3`). See `knowledge-base/README.txt` for recommended upload order.

## AI Architecture

LangGraph orchestrates specialized routing:

1. Intent Classifier (LLM + regex fallback)
2. Product Recommendation Agent (concern-aware skin + hair)
3. Ingredient Question Agent
4. Order Support Agent
5. Policy & FAQ Agent
6. Medical Safety + Human Escalation Agents

Each response uses:

- Store product catalog from PostgreSQL (synced from Shopify)
- Knowledge chunks from uploaded documents
- Learned chat FAQs from helpful customer feedback
- Conversation profile memory (skin type, concerns)
- Safety rules for medical and escalation scenarios

### Learning from chat

1. Customer clicks **Yes** under a helpful assistant reply
2. Backend saves Q&A as `chat-learned-message-*.txt`
3. Document is embedded and indexed for future retrieval

Disable with `CHAT_AUTO_LEARN_ON_FEEDBACK=false` on the API service.

## API Endpoints

### Chat (public, rate-limited)

| Method | Endpoint | Notes |
| --- | --- | --- |
| POST | `/api/chat/start` | Optional `store_id`; defaults to `DEMO_STORE_ID` |
| POST | `/api/chat/message` | Requires `conversation_id` |
| POST | `/api/chat/feedback` | Helpful / not helpful |
| GET | `/api/chat/{conversation_id}` | Read conversation |

### Shopify (public + admin)

| Method | Endpoint | Auth |
| --- | --- | --- |
| GET | `/api/shopify/store-info` | `?store_id=` or `?shop=domain.myshopify.com` |
| GET | `/api/shopify/products` | Public |
| GET | `/api/auth/start` | OAuth install |
| GET | `/api/auth/callback` | OAuth callback |
| POST | `/api/shopify/sync` | Admin API key |

### Admin

- `GET /api/conversations`, `POST /api/knowledge/upload`, `GET /api/auth/status`, etc.

Full list in API docs: https://skincare-api-68pp.onrender.com/docs

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
cp .env.example .env
npm install --legacy-peer-deps
npm run dev
```

Postgres with pgvector required, or start only the database via Docker:

```bash
docker compose up postgres -d
```

Set `DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/support_agent` in `backend/.env` when the DB runs in Docker.

## Environment Variables

See `.env.example` (project root for Docker Compose), `backend/.env.example`, `frontend/.env.example`, and `render-env-values.txt`.

### Production essentials (Render)

**skincare-api:**

```env
DEMO_STORE_ID=3
CHAT_AUTO_LEARN_ON_FEEDBACK=true
OPENAI_CHAT_MODEL=gpt-4o
CORS_ORIGINS=https://skincare-frontend-z72h.onrender.com
SEED_DEMO_DATA=false
```

**skincare-frontend:**

```env
NEXT_PUBLIC_API_URL=https://skincare-api-68pp.onrender.com
NEXT_PUBLIC_DEMO_STORE_ID=3
NEXT_PUBLIC_STORE_NAME=Glow Beauty Co.
```

Redeploy **skincare-frontend** after any `NEXT_PUBLIC_*` change.

## Deploy on Render

1. Connect GitHub repo → **New Blueprint** → `render.yaml`
2. Enter secrets: `OPENAI_API_KEY`, `ADMIN_API_KEY`, `JWT_SECRET`, Shopify credentials
3. Set URLs from `render-env-values.txt`
4. Set `DEMO_STORE_ID=3` and `NEXT_PUBLIC_DEMO_STORE_ID=3`
5. Connect Shopify via **Settings** → authorize → **Sync now**
6. Upload knowledge files; install theme widget (optional)
7. Redeploy frontend after env changes

## Merchant onboarding (selling to store owners)

Share `docs/SHOPIFY_STORE_OWNER_GUIDE.md` with merchants. Summary:

1. **Subscribe** (manual billing today; Shopify Billing API planned)
2. **Connect Shopify** via dashboard OAuth
3. **Sync catalog** + upload knowledge
4. **Install widget** — paste theme snippet with their Store ID
5. **Test** embed URL and theme preview before publishing

## Current Status

### Completed

- Render deployment (free tier) + live URLs
- Shopify OAuth + product sync (Store ID 3, 120 products)
- Concern-aware skin + hair product recommendations
- Ingredient compatibility + "Yes please" follow-up fix
- Chat learning from helpful feedback
- Evidence-based knowledge guides (skin + hair)
- Dashboard fixes (nav, store name, analytics)
- Storefront embed chat + theme widget snippet
- Merchant integration guide (`docs/SHOPIFY_STORE_OWNER_GUIDE.md`)
- Next.js 15 build fix (Suspense for `useSearchParams` on chat pages)
- Hair care import CSV (55 products, USD)
- Local Docker reliability fixes (psycopg driver, frontend `node_modules` volume, Tailwind 3.4)
- Windows font fix — system font stack instead of unloaded `Inter` (symbol-glyph text bug)

### Recommended next steps

- Upload full `knowledge-base/` pack to Store ID 3
- Verify hair catalog synced (~175 products) — see `docs/HAIR_PRODUCTS_SETUP.md` (import likely done)
- Onboard paying merchants with `docs/MERCHANT_ONBOARDING_KIT.md`
- Shopify Protected Customer Data for full order sync
- Shopify theme app extension + App Store billing

## Troubleshooting

### Landing page or dashboard text shows symbols / icons (Windows)

CSS referenced **Inter** without loading it. Some Windows installs map that name to a symbol font (Wingdings-like glyphs).

**Fix (already in repo):** the app uses a system font stack (`Segoe UI` on Windows) via `font-sans` in `frontend/app/layout.tsx` — no bare `Inter` name in CSS.

If you still see symbols after pulling latest code:

```bash
docker compose restart frontend
```

Then hard refresh the browser (**Ctrl+Shift+R**).

### Frontend 500 or missing Tailwind styles in Docker

Usually caused by an empty `node_modules` folder inside the bind-mounted frontend directory.

**Fix:** ensure `docker-compose.yml` includes the `frontend-node-modules` named volume, then rebuild:

```bash
docker compose down
docker compose up --build -d
```

Do not use Tailwind CSS v4 with this Next.js 15 setup — the project pins **Tailwind 3.4.17** (`@tailwindcss/postcss` is not used).

### Frontend build fails on `/chat` or `/embed/chat`

Next.js 15 requires `useSearchParams` inside a `Suspense` boundary. Ensure `components/chat-page-with-store.tsx` is used by both chat pages, then redeploy.

### Dashboard shows demo products (8 items)

You are on **Store ID `1`**. Switch to **Store ID `3`** on Products page.

### Chat recommends wrong products

Set `DEMO_STORE_ID=3` (API) and `NEXT_PUBLIC_DEMO_STORE_ID=3` (frontend). Use `?store_id=3` in chat/embed URLs. Run **Sync now**.

### Widget shows wrong catalog

Fix `skincare_ai_store_id` in `glow-beauty-chat-widget.liquid`.

### Chat connection errors

Confirm `NEXT_PUBLIC_API_URL` on frontend. Free tier API cold start may take ~60 seconds.

### Shopify sync 403 on customers

Expected without Protected Customer Data approval. Products still sync.

### Database reset (local only)

```bash
docker compose down -v
docker compose up --build
```

## License

Private project for a Shopify beauty support SaaS platform.

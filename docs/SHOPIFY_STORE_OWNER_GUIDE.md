# Skincare AI Agent — Shopify Store Owner Guide

This guide is for **beauty and skincare Shopify merchants** who want to subscribe to the Skincare AI Agent and add a **live chat widget** on their storefront.

For technical setup by the SaaS operator (you), see the [Integration checklist](#for-the-saas-operator-integration-checklist) at the end.

**Related documentation:**

| File | Audience |
|------|----------|
| `README.md` | Developers — architecture, env vars, troubleshooting |
| `DEPLOYMENT_LOG.txt` | Operators — deployment history and ops checklist |
| `render-env-values.txt` | Operators — Render copy-paste env vars |
| `knowledge-base/README.txt` | Merchants — knowledge upload + product CSV import |
| `integrations/shopify/README.txt` | Merchants — widget install quick steps |
| `docs/MERCHANT_ONBOARDING_KIT.md` | Operators — per-merchant checklist + QA script |
| `docs/MERCHANT_WELCOME_EMAIL.txt` | Operators — copy-paste welcome email |
| `docs/HAIR_PRODUCTS_SETUP.md` | Merchants — import 55 hair products + sync |

---

## What merchants get

- A floating **chat button** on every storefront page
- AI answers about **products**, **ingredients**, **routines**, **shipping**, **returns**, and **order status**
- Recommendations pulled from **their own Shopify catalog** (after sync)
- Optional **knowledge base** uploads (policies, FAQs, clinical guides)
- Admin dashboard to view conversations, sync products, and upload knowledge

**Live demo URLs (operator-hosted):**

| Resource | URL |
|----------|-----|
| Chat (full page) | https://skincare-frontend-z72h.onrender.com/chat?store_id=3 |
| Chat (embed) | https://skincare-frontend-z72h.onrender.com/embed/chat?store_id=3 |
| Merchant dashboard | https://skincare-frontend-z72h.onrender.com/dashboard/settings |

---

## Subscription options (how store owners pay)

Billing is **not yet automated** in the app. Use one of these models until Shopify Billing is added.

### Option A — Direct subscription (recommended for early customers)

1. Merchant signs up on your website or contacts you by email.
2. You send a **payment link** (Stripe, PayPal, bKash, bank transfer — your choice).
3. After payment, you **activate** their store and send:
   - Their **Store ID** (e.g. `3`)
   - **Dashboard login** instructions (admin API key)
   - **Chat widget** install steps (below)

**Suggested plans (example — set your own pricing):**

| Plan | Monthly | Includes |
|------|---------|----------|
| Starter | $29 | 1 store, up to 200 products, 2,000 chat messages |
| Growth | $79 | 1 store, unlimited products, 10,000 messages, knowledge uploads |
| Pro | $149 | 1 store, priority support, custom knowledge, analytics |

### Option B — Shopify App Store (future)

1. List the app in the [Shopify Partner Dashboard](https://partners.shopify.com).
2. Merchants install from **Apps** in Shopify Admin.
3. Shopify handles **recurring billing** via Managed Pricing or the Billing API.
4. OAuth connects the store automatically — no manual Store ID handoff.

Use `shopify.app.toml.example` in this repo as the starting point when you publish.

### Option C — Agency / white-label

- You host one multi-tenant platform.
- Each merchant gets a unique **Store ID** and branded chat (custom `NEXT_PUBLIC_STORE_NAME` or per-store name from DB).
- Invoice merchants monthly outside Shopify.

---

## Onboarding flow (step by step for store owners)

### Step 1 — Subscribe

Contact the operator (you) and complete payment for your chosen plan.

You will receive:

- **Store ID** — unique number for your shop in the AI platform
- **Admin API key** — for dashboard access (keep private)
- **Support email** — for escalations

### Step 2 — Connect Shopify

1. Open **Dashboard → Settings**:  
   https://skincare-frontend-z72h.onrender.com/dashboard/settings
2. Paste your **Admin API key** and click save.
3. Enter your shop domain, e.g. `your-store.myshopify.com`.
4. Click **Connect Shopify** and approve permissions in Shopify Admin.
5. After redirect, note your **Store ID** in **Connected stores**.
6. Click **Sync now** to import products, orders, and customers.

**Optional — expand catalog:** Import `knowledge-base/glow-beauty-products-import.csv` (120 skincare) and/or `glow-beauty-hair-care-import.csv` (55 hair care) in Shopify Admin → Products → Import (USD pricing). Sync again after import.

**Required Shopify permissions:** read products, read orders, read content.

### Step 3 — Upload knowledge (recommended)

1. Go to **Dashboard → Knowledge**.
2. Set **Store ID** to your connected store.
3. Upload policy and guide files from `knowledge-base/` (shipping, returns, skin guides, hair guide, etc.).

Better knowledge = better answers.

### Step 4 — Add chat widget to the storefront

#### Method 1 — Theme code snippet (works today)

1. Shopify Admin → **Online Store → Themes → Edit code**.
2. Open `theme.liquid`.
3. Paste the contents of `integrations/shopify/glow-beauty-chat-widget.liquid` **before** `</body>`.
4. Edit these two lines at the top of the snippet:

```liquid
{% assign skincare_ai_store_id = 3 %}
{% assign skincare_ai_app_url = 'https://skincare-frontend-z72h.onrender.com' %}
```

Replace `3` with **your Store ID**.

5. **Save** and use **Preview** to test.

#### Method 2 — Full-page chat link (no widget)

Add a navigation link or button anywhere in the theme:

```html
<a href="https://skincare-frontend-z72h.onrender.com/chat?store_id=3">
  Chat with our beauty advisor
</a>
```

#### Method 3 — Shopify app embed (future, one-click)

When you publish a Shopify app with a **theme app extension**, merchants will enable the widget under **Theme customizer → App embeds** without editing code.

---

## How to test the integration

### Test 1 — Embed URL (no Shopify required)

Open in a browser:

```
https://skincare-frontend-z72h.onrender.com/embed/chat?store_id=YOUR_STORE_ID
```

- Chat should load and greet you with your store name.
- Ask: *"What products do you recommend for acne?"*
- Replies should reference **your** catalog, not a demo store.

### Test 2 — Theme preview

1. Install the Liquid snippet (Step 4).
2. Click **Preview** on your theme (do not publish yet).
3. Confirm the **pink chat button** appears bottom-right.
4. Open chat and send 3 test messages:

| Prompt | Expected |
|--------|----------|
| "Do you ship internationally?" | Answer from your shipping policy / knowledge |
| "Recommend a moisturizer for dry skin" | Products from your synced catalog |
| "Where is my order #1001?" | Order lookup if that order exists |

### Test 3 — Dashboard verification

1. **Dashboard → Products** — correct Store ID, products listed.
2. **Dashboard → Conversations** — test chat appears.
3. **Dashboard → Settings → Sync now** — run after adding products in Shopify.

### Test 4 — Mobile

Preview on a phone or use Chrome DevTools device mode. The widget should resize (`min(400px, 100vw - 32px)`).

### Troubleshooting

| Problem | Fix |
|---------|-----|
| Chat shows wrong products | Wrong `store_id` in snippet; fix and redeploy theme |
| "Could not connect to AI service" | API cold start (wait 60s) or `NEXT_PUBLIC_API_URL` misconfigured on frontend |
| Button shows but iframe blank | Check `skincare_ai_app_url` and that embed route is deployed |
| Generic / demo answers | Run **Sync now**; upload knowledge files |
| OAuth fails | Confirm redirect URL in Partner app matches `https://skincare-api-68pp.onrender.com/api/auth/callback` |
| Frontend deploy / build failed | Ensure latest code uses `chat-page-with-store.tsx` (Suspense for Next.js 15); redeploy frontend |

---

## What store owners manage ongoing

| Task | Frequency |
|------|-----------|
| Sync catalog after new products | After each major catalog change |
| Update knowledge when policies change | As needed |
| Review conversations / escalations | Weekly |
| Renew subscription | Monthly per plan |

---

## Data and privacy (share with merchants)

- Product, order, and customer data are synced via **Shopify Admin API** (read-only scopes).
- Chat messages are stored in the operator’s database for support and quality improvement.
- Merchants should add a note to their **Privacy Policy** that an AI chat tool processes customer questions.
- For EU/UK stores, plan for GDPR webhooks before App Store launch.

---

## For the SaaS operator: integration checklist

Use this when onboarding a **new paying merchant**.

### Shopify Partner app

- [ ] Create app in [Shopify Partners](https://partners.shopify.com)
- [ ] Set **App URL** = your frontend URL
- [ ] Set **Allowed redirection URL** = `{API_URL}/api/auth/callback`
- [ ] Copy API key and secret to Render env: `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET`
- [ ] Scopes: `read_products,read_orders,read_content`

### Render environment (production)

Copy full values from `render-env-values.txt`. Minimum:

**API service:** `DEMO_STORE_ID`, `SHOPIFY_API_*`, `BACKEND_PUBLIC_URL`, `FRONTEND_PUBLIC_URL`, `CORS_ORIGINS`, `ADMIN_API_KEY`, `OPENAI_API_KEY`, `CHAT_AUTO_LEARN_ON_FEEDBACK=true`, `OPENAI_CHAT_MODEL=gpt-4o`

**Frontend service:** `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_DEMO_STORE_ID`, `NEXT_PUBLIC_STORE_NAME`

Redeploy frontend after any `NEXT_PUBLIC_*` change.

### Per-merchant setup

- [ ] Merchant completes OAuth → new row in `stores` table → note **Store ID**
- [ ] Run initial **Sync now**
- [ ] Upload knowledge files for their brand
- [ ] Send merchant their Store ID + admin key + widget snippet
- [ ] Merchant pastes snippet into theme with correct `store_id`
- [ ] Verify embed URL and theme preview tests pass

### Roadmap to full Shopify app

1. **Theme app extension** — app embed block (no manual Liquid)
2. **Shopify Billing API** — automated subscriptions
3. **Webhooks** — `app/uninstalled`, product update auto-sync
4. **App Bridge** — embed admin dashboard inside Shopify Admin
5. **Store lookup by domain** — `GET /api/shopify/store-info?shop=store.myshopify.com` (already supported)

---

## Quick reference

| Item | Value (current production) |
|------|----------------------------|
| Frontend | https://skincare-frontend-z72h.onrender.com |
| API | https://skincare-api-68pp.onrender.com |
| Embed chat | `/embed/chat?store_id=N` |
| OAuth callback | `/api/auth/callback` |
| Widget snippet | `integrations/shopify/glow-beauty-chat-widget.liquid` |
| Connect store | Dashboard → Settings → Connect Shopify |

---

*Document version: June 2026 — Skincare AI Agent*

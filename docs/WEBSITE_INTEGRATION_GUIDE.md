# Regular Website Integration Guide (non-Shopify)

Use this guide for beauty brands that **do not** have a Shopify store — any
website hosted on a domain (custom HTML, WordPress, Wix, Webflow, Squarespace,
React/Next, etc.). Shopify stores keep using
[`SHOPIFY_STORE_OWNER_GUIDE.md`](./SHOPIFY_STORE_OWNER_GUIDE.md); this is an
additive path and changes nothing about the Shopify flow.

The agent reuses the same multi-tenant backend. A regular website is simply a
**site tenant** (`site_type = "web"`) with its own product catalog and knowledge
base. The chat widget is an `<iframe>`, so there are **no CORS issues** and **no
build changes** required on the customer's site.

---

## How it differs from Shopify

| | Shopify store | Regular website |
|---|---|---|
| Tenant creation | OAuth install | `POST /api/web/sites` (admin) |
| Product catalog | Synced via Admin API | Added manually / bulk via API |
| Knowledge base | `POST /api/knowledge/upload` | Same |
| Widget embed | Theme Liquid snippet | One-line `<script>` loader |
| Identifier | `*.myshopify.com` domain | `site_key` (website host or slug) |

Everything else — chat, RAG, concern-aware recommendations, chat learning — is
identical because both store types share the same `Store` / `Product` /
embedding infrastructure.

---

## Step 1 — Register the website as a site (operator/admin)

Create the tenant once and note the returned `id` (your `store_id`):

```bash
curl -X POST "$API_URL/api/web/sites" \
  -H "X-Admin-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Brand Name", "website_url": "https://brandname.com"}'
```

If you omit `site_key`, it is derived from the website host (or a slug of the
name). The response includes `id`, `site_key`, and `site_type: "web"`.

## Step 2 — Add the product catalog (no Shopify sync)

Add products so the agent can recommend them:

```bash
curl -X POST "$API_URL/api/web/sites/<SITE_ID>/products" \
  -H "X-Admin-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Niacinamide 10% Oil Control Serum",
    "description": "Lightweight serum for oily, acne-prone skin.",
    "ingredients": "Niacinamide, Zinc PCA, Hyaluronic Acid",
    "price": "$28.00",
    "collections": ["Serums", "Oily Skin"],
    "available": true
  }'
```

- **Bulk import:** `POST /api/web/sites/<SITE_ID>/products/bulk` with body
  `{"products": [ ... ]}`.
- **Update:** `PUT /api/web/sites/<SITE_ID>/products/<PRODUCT_ID>`
- **Remove:** `DELETE /api/web/sites/<SITE_ID>/products/<PRODUCT_ID>`

Embeddings re-index automatically on every change.

## Step 3 — Upload knowledge (shipping, returns, ingredient FAQ)

Identical to Shopify: `POST /api/knowledge/upload` with `store_id=<SITE_ID>` and
a `.txt` / `.md` / `.pdf` file (or use the dashboard Knowledge page).

## Step 4 — Embed the chat widget

Give the customer **one** snippet to paste before `</body>`:

**Option A — one-line loader (recommended):**

```html
<script
  src="https://skincare-frontend-z72h.onrender.com/widget/chat-widget.js"
  data-store-id="<SITE_ID>"
  data-accent="#ec4899"
  data-title="Beauty Advisor"
  defer
></script>
```

| Attribute | Required | Notes |
|---|---|---|
| `data-store-id` | yes | The site ID from Step 1 |
| `data-app-url` | no | Defaults to the script origin |
| `data-accent` | no | Launcher button color (default `#ec4899`) |
| `data-title` | no | Iframe accessibility title |
| `data-position` | no | `right` (default) or `left` |

**Option B — self-contained snippet:** see
[`integrations/web/chat-widget-snippet.html`](../integrations/web/chat-widget-snippet.html);
replace the `store_id` and app URL.

Both work on any CMS or hand-coded site. The button appears bottom-right and
opens `/embed/chat?store_id=<SITE_ID>` in an iframe.

## Step 5 — Test

- Open the website and click the chat button.
- Ask "What do you recommend for oily skin?" and confirm answers match the
  products added in Step 2.
- Ask a shipping/returns question to confirm knowledge answers.

---

## Reference

- API routes: `backend/app/api/routes/web.py` (prefix `/api/web`)
- Widget loader: `frontend/public/widget/chat-widget.js` (served at
  `/widget/chat-widget.js`)
- Integration files + quick steps: `integrations/web/README.txt`
- Public site lookup for the widget: `GET /api/web/site-info?store_id=<ID>`

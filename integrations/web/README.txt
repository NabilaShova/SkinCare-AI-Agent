Skincare AI Agent — Regular Website Integration
================================================

Use this when a beauty brand does NOT have a Shopify store — just a regular
website hosted on any domain (custom HTML, WordPress, Wix, Webflow, Squarespace,
React/Next, etc.). Shopify stores should keep using integrations/shopify/.

The AI agent reuses the same multi-tenant backend. A regular website is just a
"site" tenant (site_type = "web") with its own product catalog and knowledge
base. The chat widget is an iframe, so there are NO CORS issues and NO build
changes on the customer's website.


STEP 1 — Register the website as a site (operator / admin)
----------------------------------------------------------
Call the admin API once to create the tenant and get its site ID.

  curl -X POST "$API_URL/api/web/sites" \
    -H "X-Admin-API-Key: $ADMIN_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"name": "Brand Name", "website_url": "https://brandname.com"}'

Response includes "id" (the store/site ID). Use it as the store_id below.


STEP 2 — Add the product catalog (no Shopify sync)
--------------------------------------------------
Add products manually so the agent can recommend them.

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

Bulk import many at once with POST /api/web/sites/<SITE_ID>/products/bulk
(body: {"products": [ ... ]}). Update with PUT .../products/<ID>, remove with
DELETE .../products/<ID>. Embeddings re-index automatically on every change.


STEP 3 — Upload knowledge (shipping, returns, ingredient FAQ, etc.)
-------------------------------------------------------------------
Same as Shopify: POST /api/knowledge/upload with store_id=<SITE_ID> and a
.txt/.md/.pdf file (or use the dashboard Knowledge page).


STEP 4 — Embed the chat widget on the website
----------------------------------------------
Give the customer ONE of the following to paste before </body>:

Option A (one-line loader, recommended):
  <script
    src="https://skincare-frontend-z72h.onrender.com/widget/chat-widget.js"
    data-store-id="<SITE_ID>"
    data-accent="#ec4899"
    data-title="Beauty Advisor"
    defer
  ></script>

Option B (self-contained snippet): see chat-widget-snippet.html and replace
the store_id and app URL.

Both work on any CMS or hand-coded site. The button appears bottom-right and
opens /embed/chat?store_id=<SITE_ID> in an iframe.


STEP 5 — Test
-------------
- Open the website and click the chat button.
- Ask "What do you recommend for oily skin?" and confirm the answers match the
  products added in Step 2.
- Ask a shipping/returns question to confirm knowledge answers.


FILES
-----
- chat-widget.js ............ canonical loader (also served at /widget/chat-widget.js)
- chat-widget-snippet.html .. paste-in HTML version + loader example
- README.txt ............... this guide

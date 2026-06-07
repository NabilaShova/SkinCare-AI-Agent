Shopify Storefront Chat Widget — Install Guide
==============================================

FILE: glow-beauty-chat-widget.liquid

Adds a floating chat button (bottom-right) on every storefront page. Clicking
opens an iframe to the hosted AI chat for that merchant's Store ID.

BEFORE YOU START
- Merchant must be connected via Dashboard -> Settings -> Connect Shopify
- Run Sync now so chat uses live catalog
- Know the merchant Store ID (e.g. 3)

INSTALL (Theme code)
1. Shopify Admin -> Online Store -> Themes -> Edit code
2. Open theme.liquid
3. Paste the full contents of glow-beauty-chat-widget.liquid BEFORE </body>
4. Edit these two lines at the top of the snippet:
     {% assign skincare_ai_store_id = 3 %}
     {% assign skincare_ai_app_url = 'https://skincare-frontend-z72h.onrender.com' %}
5. Save
6. Preview theme (do not publish until tested)

TEST WITHOUT SHOPIFY
Open in browser:
  https://skincare-frontend-z72h.onrender.com/embed/chat?store_id=3

TEST ON STOREFRONT
1. Theme preview -> click pink chat button (bottom-right)
2. Ask: "Recommend a moisturizer for dry skin"
3. Confirm answers reference merchant catalog (not demo store)

TROUBLESHOOTING
- Wrong products: wrong store_id in snippet
- Blank iframe: frontend not deployed or wrong skincare_ai_app_url
- Connection error: API cold start (wait 60s on free tier)

FULL MERCHANT ONBOARDING
See docs/SHOPIFY_STORE_OWNER_GUIDE.md

# Merchant Onboarding Kit — Skincare AI Agent

Use this kit when a **new paying merchant** subscribes. You (the operator) run the technical setup; the merchant gets the welcome email and widget instructions.

---

## Operator checklist (per new merchant)

### Before first contact

- [ ] Merchant chose a plan (Starter / Growth / Pro)
- [ ] Payment received
- [ ] Shop domain confirmed (e.g. `brand-name.myshopify.com`)

### Technical setup (you)

- [ ] Shopify Partner app credentials on Render (`SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET`)
- [ ] Merchant completes OAuth OR you walk them through **Dashboard → Settings → Connect Shopify**
- [ ] Note new **Store ID** from **Connected stores**
- [ ] Run **Sync now**
- [ ] Upload default knowledge pack from `knowledge-base/` (see `knowledge-base/README.txt`)
- [ ] Set `DEMO_STORE_ID` / `NEXT_PUBLIC_DEMO_STORE_ID` if this merchant is your primary demo (optional)

### Handoff to merchant

- [ ] Send welcome email (`docs/MERCHANT_WELCOME_EMAIL.txt` — fill in blanks)
- [ ] Send **Store ID** and **Admin API key** (secure channel)
- [ ] Send widget snippet with their Store ID (`integrations/shopify/glow-beauty-chat-widget.liquid`)
- [ ] Link to `docs/SHOPIFY_STORE_OWNER_GUIDE.md`

### Merchant self-service (they do)

- [ ] Paste widget into `theme.liquid` (or you do it for them)
- [ ] Preview theme → test chat
- [ ] Publish theme
- [ ] Customize policies in knowledge files if needed

### QA before go-live

- [ ] Embed URL works: `/embed/chat?store_id=N`
- [ ] Storefront button opens chat
- [ ] Skincare prompt returns their products
- [ ] Hair prompt returns hair products (if hair catalog imported)
- [ ] "Yes" after hair question builds **hair** routine
- [ ] Policy questions match uploaded knowledge
- [ ] Conversation appears in **Dashboard → Conversations**

---

## Suggested pricing (copy for your website)

| Plan | Monthly | Best for |
|------|---------|----------|
| **Starter** | $29 | Small catalogs, up to 200 products, ~2,000 chats/mo |
| **Growth** | $79 | Full catalog, knowledge uploads, ~10,000 chats/mo |
| **Pro** | $149 | Priority support, custom knowledge, analytics |

Add your payment link (Stripe, PayPal, bKash) and support email.

---

## Merchant test script (send after widget install)

Ask the merchant to run these in the live chat:

**Skincare**
1. `I have oily, acne-prone skin. What products help with prevention?`
2. `Can I use retinol and salicylic acid together?`

**Hair** (if catalog imported)
3. `What shampoo helps with hair fall?` → reply **Yes**
4. `I have dandruff — what should I use?`

**Store**
5. `Do you ship internationally?`
6. `What is your return policy?`

**Pass criteria:** Answers mention **their** products; hair follow-up uses shampoo/conditioner steps; policies match their uploaded docs.

---

## Handoff template (fill in per merchant)

```
Merchant: _______________________
Shop domain: ____________________.myshopify.com
Store ID: _____
Plan: Starter / Growth / Pro
Activated: ____-__-__
Admin API key: (sent separately)

Dashboard: https://skincare-frontend-z72h.onrender.com/dashboard/settings
Embed test: https://skincare-frontend-z72h.onrender.com/embed/chat?store_id=_____

Widget snippet: integrations/shopify/glow-beauty-chat-widget.liquid
  skincare_ai_store_id = _____
  skincare_ai_app_url = https://skincare-frontend-z72h.onrender.com

Knowledge uploaded: [ ] shipping [ ] returns [ ] skin guides [ ] hair guide
Catalog synced: ___ products
Widget live on theme: [ ] Preview [ ] Published
```

---

## Related docs

| Document | Use |
|----------|-----|
| `docs/SHOPIFY_STORE_OWNER_GUIDE.md` | Full merchant-facing guide |
| `docs/MERCHANT_WELCOME_EMAIL.txt` | Copy-paste welcome email |
| `docs/HAIR_PRODUCTS_SETUP.md` | Hair CSV import + sync |
| `integrations/shopify/README.txt` | Widget install steps |
| `knowledge-base/README.txt` | Knowledge + product CSVs |

---

*Skincare AI Agent — Merchant Onboarding Kit*

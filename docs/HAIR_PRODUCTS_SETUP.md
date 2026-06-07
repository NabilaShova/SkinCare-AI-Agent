# Hair Care Catalog Setup

Add 55 trending hair care products (USD) to your connected Shopify store so chat can recommend shampoos, conditioners, scalp treatments, and more.

## Already imported?

If you already imported `glow-beauty-hair-care-import.csv` and ran **Sync now**, skip to **Verify** below.

**Quick verify:**
1. Dashboard → **Products** → Store ID `3` — count should be **~175** (120 skincare + 55 hair), or at least include `HC-0001` style SKUs
2. Chat: *"What shampoo helps with hair fall?"* — should suggest hair products, not only skincare
3. Dashboard → **Knowledge** — confirm `hair-care-guide.txt` is uploaded (optional but improves answers)

## Files

| File | Items |
|------|-------|
| `knowledge-base/glow-beauty-hair-care-import.csv` | 55 hair products |
| `knowledge-base/hair-care-guide.txt` | RAG knowledge for hair Q&A |
| `scripts/generate_hair_care_csv.py` | Regenerate CSV |

## Step 1 — Import hair products into Shopify

1. Shopify Admin → **Settings** → **Store details** → currency **USD**
2. **Products** → **Import**
3. Upload `knowledge-base/glow-beauty-hair-care-import.csv`
4. Review columns → **Import products**

You should see new SKUs prefixed `HC-0001`, `HC-0002`, etc.

## Step 2 — Sync into the AI agent

1. Open [Dashboard → Settings](https://skincare-frontend-z72h.onrender.com/dashboard/settings)
2. Confirm **Store ID** = `3` (or your connected store)
3. Click **Sync now**
4. Open **Dashboard → Products** — expect **~175** products (120 skincare + 55 hair) after both CSVs are imported

## Step 3 — Upload hair knowledge

1. **Dashboard → Knowledge** → Store ID `3`
2. Upload `knowledge-base/hair-care-guide.txt`
3. Wait for status: **processed**

## Step 4 — Test chat

Use the storefront widget or embed URL:

```
https://skincare-frontend-z72h.onrender.com/embed/chat?store_id=3
```

| Prompt | Expected |
|--------|----------|
| What shampoo helps with hair fall? | Hair fall shampoos / routine sets — not skincare moisturizers |
| Yes (after hair recommendation) | **Hair care routine** (shampoo, conditioner, scalp treatment) — not morning/night skincare |
| I have dandruff — what should I use? | Anti-dandruff shampoo / scalp treatment |
| Recommend products for frizzy curly hair | Leave-in, curl shampoo, conditioner |

## Regenerate CSV

```bash
py -3 scripts/generate_hair_care_csv.py
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Chat still only knows skincare | Run **Sync now** after import |
| Hair answers are generic | Upload `hair-care-guide.txt` |
| "Yes" builds skincare routine | Redeploy **skincare-api** (hair routine fix in agent) |
| Duplicate products on re-import | Shopify may create duplicates; delete old imports or use unique SKUs |

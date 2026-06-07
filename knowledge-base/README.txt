Knowledge Base Upload Pack — Glow Beauty Co.
============================================

These files are ready to upload to your production knowledge base.

HOW TO UPLOAD
1. Open https://skincare-frontend-z72h.onrender.com/dashboard/knowledge
2. Save your ADMIN_API_KEY in Settings first
3. Set Store ID to your connected store (production: 3, local demo: 1)
4. Upload each .txt file one at a time (or all 6 in sequence)
5. Wait for status: processed

RECOMMENDED UPLOAD ORDER
1. shipping-policy.txt
2. return-refund-policy.txt
3. store-faq.txt
4. skin-types-guide.txt
5. skin-concerns-treatment-guide.txt
6. routine-formulas-guide.txt
7. active-ingredients-clinical-guide.txt
8. ingredient-compatibility-guide.txt
9. hair-care-guide.txt
10. ingredient-faq.txt
11. product-usage-guide.txt
12. skin-consultation-guide.txt

CUSTOMIZE BEFORE UPLOAD
- Replace "Glow Beauty Co." with your real store name
- Adjust shipping times, return window, and free shipping threshold to match your policies
- Add product-specific notes if you sell unique formulas

TEST PROMPTS AFTER UPLOAD
- "Do you ship internationally?"
- "What is your return policy?"
- "Can I use Niacinamide with Vitamin C?"
- "How do I layer my skincare products?"
- "I have oily acne-prone skin — help me build a routine."
- "Can you suggest products for acne prevention?"
- "What routine is best for dry sensitive skin?"
- "Can I use retinol and salicylic acid together?"
- "How do I treat dark spots and hyperpigmentation?"
- "What shampoo helps with hair fall in humid weather?"
- "I have dandruff — what should I use?"
- "Recommend products for frizzy curly hair."

SHOPIFY PRODUCT IMPORT CSV
- glow-beauty-products-import.csv (120 trending-inspired skincare products, USD pricing)
- glow-beauty-hair-care-import.csv (55 trending hair care products for Bangladesh, USD pricing)
- product_template.csv (Shopify sample template)

PRICES
- Skincare CSV (glow-beauty-products-import.csv): USD
- Hair care CSV (glow-beauty-hair-care-import.csv): USD
- Set Shopify store currency to USD before import (Settings -> Store details -> Store currency)

HOW TO IMPORT PRODUCTS INTO SHOPIFY
1. Shopify Admin -> Settings -> Store details -> set currency to US Dollar (USD)
2. Products -> Import -> choose glow-beauty-products-import.csv (skincare)
3. Products -> Import -> choose glow-beauty-hair-care-import.csv (hair care — can import after skincare)
4. Review columns and click Import products for each file
5. AI dashboard Settings (Store ID 3) -> Sync now
6. Verify at Dashboard -> Products (Store ID 3) — expect ~175 products after both imports

REGENERATE CSV
  py -3 scripts/generate_product_csv.py
  py -3 scripts/generate_hair_care_csv.py

PRODUCT CSV COVERAGE
Skincare (120 items)
- Cleansers, toners, serums, moisturizers, sunscreens
- Masks, exfoliants, eye care, lip care, body care
- Mists, oils, spot treatments, routine sets
- Tags for skin type, concern, ingredient, and price tier
- Inspired by trending products from klassy.com.bd and global bestsellers

Hair care (55 items)
- Shampoos, conditioners, hair oils, serums, masks
- Scalp treatments, leave-ins, styling, routine sets
- Bangladesh-popular brands: Sunsilk, Dove, Head & Shoulders, Parachute, Vatika, Indulekha
- Concern tags: hair-fall, dandruff, frizz, curly, dry-damaged, humid-climate, hijab-friendly

FILES IN THIS FOLDER
- glow-beauty-products-import.csv
- glow-beauty-hair-care-import.csv
- product_template.csv
- shipping-policy.txt
- return-refund-policy.txt
- store-faq.txt
- skin-types-guide.txt (oily, dry, combination, sensitive, normal)
- skin-concerns-treatment-guide.txt (acne, aging, spots, redness, dehydration)
- routine-formulas-guide.txt (morning/night routines by skin type and concern)
- active-ingredients-clinical-guide.txt (BHA, retinol, vitamin C, niacinamide, etc.)
- ingredient-compatibility-guide.txt (layering and combination rules)
- hair-care-guide.txt (hair fall, dandruff, frizz, curly hair — Bangladesh climate)
- ingredient-faq.txt
- product-usage-guide.txt
- skin-consultation-guide.txt

STOREFRONT CHAT WIDGET
After products are synced, add the floating chat button to the Shopify theme:
- Snippet: integrations/shopify/glow-beauty-chat-widget.liquid
- Install steps: integrations/shopify/README.txt
- Full merchant guide: docs/SHOPIFY_STORE_OWNER_GUIDE.md

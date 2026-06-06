Knowledge Base Upload Pack — Glow Beauty Co.
============================================

These files are ready to upload to your production knowledge base.

HOW TO UPLOAD
1. Open https://skincare-frontend-z72h.onrender.com/dashboard/knowledge
2. Save your ADMIN_API_KEY in Settings first
3. Set Store ID (usually 1, or your connected store ID)
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
9. ingredient-faq.txt
10. product-usage-guide.txt
11. skin-consultation-guide.txt

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

SHOPIFY PRODUCT IMPORT CSV
- glow-beauty-products-import.csv (120 trending-inspired skincare products, BDT pricing)
- product_template.csv (Shopify sample template)

PRICES ARE IN BDT
- Converted at 110 BDT per USD reference price
- Rounded to retail-friendly amounts (nearest 50 BDT under 2000, nearest 100 BDT above)
- Example: serum ~BDT 800-4000, routine sets ~BDT 6500-10500
- Set Shopify store currency to BDT BEFORE import (Settings -> Store details -> Store currency)

HOW TO IMPORT PRODUCTS INTO SHOPIFY
1. Shopify Admin -> Settings -> Store details -> set currency to Bangladeshi Taka (BDT)
2. Products -> Import -> choose glow-beauty-products-import.csv
3. Review columns and click Import products
4. AI dashboard Settings (Store ID 3) -> Sync now
5. Verify at Dashboard -> Products (Store ID 3)

REGENERATE CSV
  py -3 scripts/generate_product_csv.py

PRODUCT CSV COVERAGE (120 items)
- Cleansers, toners, serums, moisturizers, sunscreens
- Masks, exfoliants, eye care, lip care, body care
- Mists, oils, spot treatments, routine sets
- Tags for skin type, concern, ingredient, and price tier
- Inspired by trending products from klassy.com.bd and global bestsellers

FILES IN THIS FOLDER
- glow-beauty-products-import.csv
- product_template.csv
- shipping-policy.txt
- return-refund-policy.txt
- store-faq.txt
- skin-types-guide.txt (oily, dry, combination, sensitive, normal)
- skin-concerns-treatment-guide.txt (acne, aging, spots, redness, dehydration)
- routine-formulas-guide.txt (morning/night routines by skin type and concern)
- active-ingredients-clinical-guide.txt (BHA, retinol, vitamin C, niacinamide, etc.)
- ingredient-compatibility-guide.txt (layering and combination rules)
- ingredient-faq.txt
- product-usage-guide.txt
- skin-consultation-guide.txt

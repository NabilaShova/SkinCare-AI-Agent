"""Generate Shopify hair care import CSV for Glow Beauty Co. (Bangladesh market, USD pricing)."""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "knowledge-base" / "glow-beauty-hair-care-import.csv"
TEMPLATE = ROOT / "knowledge-base" / "product_template.csv"

CATEGORIES = {
    "Shampoo": "Health & Beauty > Personal Care > Hair Care > Shampoo & Conditioner",
    "Conditioner": "Health & Beauty > Personal Care > Hair Care > Shampoo & Conditioner",
    "Hair Oil": "Health & Beauty > Personal Care > Hair Care > Hair Oils",
    "Hair Serum": "Health & Beauty > Personal Care > Hair Care > Hair Treatments",
    "Hair Mask": "Health & Beauty > Personal Care > Hair Care > Hair Treatments",
    "Scalp Treatment": "Health & Beauty > Personal Care > Hair Care > Hair Treatments",
    "Leave-In": "Health & Beauty > Personal Care > Hair Care > Hair Treatments",
    "Styling": "Health & Beauty > Personal Care > Hair Care > Hair Styling Products",
    "Hair Set": "Health & Beauty > Personal Care > Hair Care > Hair Care Sets",
}

# title, vendor, type, tags, description, ingredients, price_usd, compare_usd, size
PRODUCTS: list[tuple] = [
    ("Sunsilk Hijab Natural Shampoo", "Sunsilk", "Shampoo", "bangladesh, hijab-friendly, gentle, daily, trending-bd", "Gentle shampoo for covered hair and sensitive scalps in humid climates.", "Aloe vera, Olive oil, Vitamin E", 6.00, 8.00, "180ml"),
    ("Sunsilk Black Shine Shampoo", "Sunsilk", "Shampoo", "bangladesh, shine, black-hair, daily", "Shampoo for glossy, smooth-looking dark hair.", "Pearl extract, Amino acids, Vitamin B3", 6.00, 8.00, "180ml"),
    ("Sunsilk Thick & Long Shampoo", "Sunsilk", "Shampoo", "bangladesh, hair-growth, length, biotin", "Strengthening shampoo for longer, thicker-looking hair.", "Biotin, Collagen, Keratin", 6.00, 8.00, "180ml"),
    ("Sunsilk Hair Fall Solution Shampoo", "Sunsilk", "Shampoo", "bangladesh, hair-fall, strengthening, daily", "Reduces hair fall from breakage with nourishing actives.", "Soya protein, Vitamins, Argan oil", 6.50, 8.50, "180ml"),
    ("Dove Intense Repair Shampoo", "Dove", "Shampoo", "dry-damaged, repair, bangladesh, keratin", "Repairs dry and damaged hair with keratin actives.", "Keratin, Vitamins, Glycerin", 7.00, 9.00, "340ml"),
    ("Dove Daily Moisture Shampoo", "Dove", "Shampoo", "dry, hydration, gentle, bangladesh", "Moisturizing shampoo for soft, manageable hair.", "Pro-moisture complex, Glycerin", 7.00, 9.00, "340ml"),
    ("Head & Shoulders Anti-Dandruff Shampoo", "Head & Shoulders", "Shampoo", "dandruff, oily-scalp, bangladesh, humid-climate", "Classic anti-dandruff shampoo for flaky, itchy scalps.", "Pyrithione zinc, Menthol", 7.50, 10.00, "330ml"),
    ("Head & Shoulders Smooth & Silky Shampoo", "Head & Shoulders", "Shampoo", "dandruff, frizz, bangladesh, smooth", "Anti-dandruff care with frizz control for humid weather.", "Pyrithione zinc, Dimethicone", 7.50, 10.00, "330ml"),
    ("Tresemme Keratin Smooth Shampoo", "Tresemme", "Shampoo", "frizz, keratin, smooth, salon-style", "Keratin-infused shampoo to fight frizz and flyaways.", "Keratin, Marula oil, Silicones", 8.00, 11.00, "580ml"),
    ("Tresemme Botanique Nourish Shampoo", "Tresemme", "Shampoo", "dry, coconut, aloe, natural", "Sulfate-free blend with coconut milk and aloe vera.", "Coconut milk, Aloe vera, Essential oils", 8.00, 11.00, "500ml"),
    ("Pantene Hair Fall Control Shampoo", "Pantene", "Shampoo", "hair-fall, strengthening, bangladesh, pro-v", "Pro-V formula to reduce hair fall from breakage.", "Pro-V blend, Caffeine, Histidine", 7.00, 9.00, "340ml"),
    ("Pantene Silky Smooth Care Shampoo", "Pantene", "Shampoo", "dry, smooth, shine, bangladesh", "Smoothing shampoo for silky, touchable hair.", "Pro-V, Silk extracts, Argan oil", 7.00, 9.00, "340ml"),
    ("L'Oreal Elvive Extraordinary Oil Shampoo", "L'Oreal", "Shampoo", "dry, oil-nourish, shine, trending", "Nourishing shampoo with flower oils for dull hair.", "Coconut oil, Sunflower oil, Avocado oil", 9.00, 12.00, "250ml"),
    ("L'Oreal Elvive Total Repair 5 Shampoo", "L'Oreal", "Shampoo", "damaged, repair, protein, heat-damage", "Rebuilds five signs of hair damage from styling and pollution.", "Protein, Ceramides, Arginine", 9.00, 12.00, "250ml"),
    ("Clinic Plus Strong & Long Shampoo", "Clinic Plus", "Shampoo", "bangladesh, budget-friendly, hair-fall, milk-protein", "Milk protein shampoo popular for everyday family use.", "Milk protein, Multivitamins", 4.50, 6.00, "175ml"),
    ("OGX Biotin & Collagen Shampoo", "OGX", "Shampoo", "volume, fine-hair, biotin, trending", "Thickening shampoo for fuller-looking hair.", "Biotin, Collagen, Wheat protein", 10.00, 13.00, "385ml"),
    ("OGX Coconut Milk Shampoo", "OGX", "Shampoo", "dry, curly, hydration, sulfate-free", "Hydrating shampoo with coconut milk and whipped egg white.", "Coconut milk, Egg white protein, Coconut oil", 10.00, 13.00, "385ml"),
    ("Mielle Rosemary Mint Strengthening Shampoo", "Mielle", "Shampoo", "scalp-health, growth, natural, trending-2025", "Stimulating shampoo with rosemary and mint for scalp circulation.", "Rosemary, Mint, Biotin", 12.00, 15.00, "355ml"),
    ("Shea Moisture Jamaican Black Castor Oil Shampoo", "Shea Moisture", "Shampoo", "curly, damaged, castor-oil, natural", "Strengthening sulfate-free shampoo for weak, brittle hair.", "Castor oil, Shea butter, Peppermint", 11.00, 14.00, "384ml"),
    ("Glow Beauty Co. Gentle Scalp Clarifying Shampoo", "Glow Beauty Co.", "Shampoo", "oily-scalp, buildup, weekly, sulfate-free", "Weekly clarifying shampoo to remove product buildup and pollution.", "Salicylic acid, Tea tree, Niacinamide", 14.00, 18.00, "250ml"),
    ("Sunsilk Soft & Smooth Conditioner", "Sunsilk", "Conditioner", "bangladesh, detangle, daily, smooth", "Lightweight conditioner for easy detangling after wash.", "Olive oil, Vitamin B3, Amino acids", 6.00, 8.00, "180ml"),
    ("Dove Intense Repair Conditioner", "Dove", "Conditioner", "dry-damaged, repair, bangladesh", "Deep conditioner to restore dry, damaged strands.", "Keratin, Vitamins, Glycerin", 7.00, 9.00, "340ml"),
    ("Tresemme Keratin Smooth Conditioner", "Tresemme", "Conditioner", "frizz, keratin, humid-climate, smooth", "Keratin conditioner for frizz control in humidity.", "Keratin, Marula oil", 8.00, 11.00, "580ml"),
    ("Pantene Pro-V Miracles Conditioner", "Pantene", "Conditioner", "dry, repair, bangladesh, smooth", "Rich conditioner for smooth, strong hair.", "Pro-V, Lipids, Antioxidants", 7.00, 9.00, "340ml"),
    ("L'Oreal Elvive Dream Lengths Conditioner", "L'Oreal", "Conditioner", "long-hair, split-ends, repair, trending", "Conditioner for long hair prone to split ends and breakage.", "Castor oil, Vitamins, Keratin", 9.00, 12.00, "250ml"),
    ("Shea Moisture Curl & Shine Conditioner", "Shea Moisture", "Conditioner", "curly, wavy, hydration, natural", "Moisturizing conditioner for curls and waves.", "Coconut oil, Silk protein, Neem oil", 11.00, 14.00, "384ml"),
    ("Glow Beauty Co. Bond Repair Conditioner", "Glow Beauty Co.", "Conditioner", "damaged, color-treated, bond-repair, salon", "Bond-building conditioner inspired by salon repair treatments.", "Amino acids, Peptides, Squalane", 18.00, 22.00, "250ml"),
    ("Parachute Advansed Coconut Hair Oil", "Parachute", "Hair Oil", "bangladesh, coconut-oil, scalp-massage, classic-bd", "Light coconut hair oil for daily scalp massage and shine.", "Coconut oil, Vitamin E", 5.00, 7.00, "200ml"),
    ("Parachute Advansed Gold Coconut Hair Oil", "Parachute", "Hair Oil", "bangladesh, coconut-oil, premium, shine", "Enriched coconut oil with gold formula for extra nourishment.", "Coconut oil, Almond extract", 6.00, 8.00, "200ml"),
    ("Indulekha Bringha Ayurvedic Hair Oil", "Indulekha", "Hair Oil", "bangladesh, ayurvedic, hair-fall, scalp-health", "Ayurvedic oil with bringharaj for hair fall and scalp care.", "Bringharaj, Amla, Brahmi", 12.00, 15.00, "100ml"),
    ("Vatika Naturals Almond Hair Oil", "Vatika", "Hair Oil", "bangladesh, almond, dry-hair, nourishment", "Almond-enriched hair oil for dry and dull hair.", "Almond oil, Henna, Aloe vera", 5.50, 7.50, "200ml"),
    ("Vatika Naturals Henna Hair Oil", "Vatika", "Hair Oil", "bangladesh, henna, shine, traditional", "Henna hair oil for shine and strength in South Asian routines.", "Henna, Coconut oil, Lemon", 5.50, 7.50, "200ml"),
    ("Moroccanoil Treatment Original", "Moroccanoil", "Hair Oil", "frizz, argan-oil, shine, premium", "Iconic argan oil treatment for frizz and shine.", "Argan oil, Linseed extract, Silicones", 34.00, 42.00, "100ml"),
    ("Glow Beauty Co. Rosemary Scalp Oil", "Glow Beauty Co.", "Hair Oil", "scalp-health, growth, rosemary, trending", "Lightweight rosemary scalp oil for massage and thinning concerns.", "Rosemary oil, Peppermint, Jojoba", 16.00, 20.00, "50ml"),
    ("L'Oreal Elvive Extraordinary Oil Serum", "L'Oreal", "Hair Serum", "frizz, shine, heat-protection, trending-bd", "Multi-use hair oil serum for frizz and heat protection.", "Flower oils, UV filter, Silicones", 11.00, 14.00, "100ml"),
    ("Tresemme Keratin Smooth Serum", "Tresemme", "Hair Serum", "frizz, keratin, humid-climate, styling", "Anti-frizz serum for smooth styles in humidity.", "Keratin, Silicones, Marula oil", 9.00, 12.00, "97ml"),
    ("The Ordinary Multi-Peptide Serum for Hair Density", "The Ordinary", "Hair Serum", "thinning, scalp, peptides, budget-friendly", "Scalp serum supporting hair density and fuller-looking hair.", "Peptides, Caffeine, Rosemary", 18.00, 22.00, "60ml"),
    ("Glow Beauty Co. Anti-Frizz Heat Protect Serum", "Glow Beauty Co.", "Hair Serum", "frizz, heat-protection, styling, humid-climate", "Heat protectant serum up to 230°C for blow-dry and flat iron.", "Silicones, Argan oil, Vitamin E", 15.00, 19.00, "100ml"),
    ("Olaplex No.3 Hair Perfector", "Olaplex", "Hair Mask", "damaged, bond-repair, color-treated, cult-favorite", "At-home bond repair treatment for chemically treated hair.", "Bis-Aminopropyl Diglycol Dimaleate", 28.00, 34.00, "100ml"),
    ("Glow Beauty Co. Deep Repair Hair Mask", "Glow Beauty Co.", "Hair Mask", "dry-damaged, weekly, keratin, repair", "Weekly mask with keratin and ceramides for damaged hair.", "Keratin, Ceramides, Shea butter", 18.00, 22.00, "250ml"),
    ("Shea Moisture Manuka Honey Hair Mask", "Shea Moisture", "Hair Mask", "dry, curly, hydration, natural", "Intensive mask with manuka honey and mafura oil.", "Manuka honey, Mafura oil, Shea butter", 14.00, 17.00, "340g"),
    ("Mielle Babassu Oil Mint Deep Conditioner", "Mielle", "Hair Mask", "curly, scalp, mint, protein-moisture", "Deep conditioner with babassu oil and mint for scalp refresh.", "Babassu oil, Mint, Amino acids", 12.00, 15.00, "355ml"),
    ("L'Oreal Elvive Total Repair 5 Hair Mask", "L'Oreal", "Hair Mask", "damaged, repair, weekly, bangladesh", "Weekly repair mask for over-processed hair.", "Protein, Ceramides, Almond oil", 10.00, 13.00, "300ml"),
    ("Glow Beauty Co. Tea Tree Scalp Scrub", "Glow Beauty Co.", "Scalp Treatment", "oily-scalp, dandruff, exfoliating, weekly", "Weekly scalp scrub to remove flakes and buildup.", "Tea tree, Salicylic acid, Sugar crystals", 16.00, 20.00, "120g"),
    ("Glow Beauty Co. Caffeine Scalp Tonic", "Glow Beauty Co.", "Scalp Treatment", "thinning, scalp-health, caffeine, daily", "Leave-on scalp tonic with caffeine and niacinamide.", "Caffeine, Niacinamide, Peppermint", 14.00, 18.00, "100ml"),
    ("Head & Shoulders Scalp Cream Treatment", "Head & Shoulders", "Scalp Treatment", "dandruff, itchy-scalp, bangladesh, treatment", "Intensive scalp cream for persistent dandruff and itch.", "Pyrithione zinc, Menthol, Glycerin", 9.00, 12.00, "200ml"),
    ("Glow Beauty Co. Curl Defining Leave-In Cream", "Glow Beauty Co.", "Leave-In", "curly, wavy, frizz, definition", "Leave-in cream for defined curls without crunch.", "Shea butter, Flaxseed, Glycerin", 14.00, 18.00, "200ml"),
    ("Shea Moisture Coconut & Hibiscus Curl Milk", "Shea Moisture", "Leave-In", "curly, hydration, detangle, natural", "Detangling leave-in milk for thick curly hair.", "Coconut oil, Hibiscus, Silk protein", 12.00, 15.00, "237ml"),
    ("Batiste Dry Shampoo Original", "Batiste", "Styling", "oily-scalp, refresh, no-wash, trending", "Dry shampoo to refresh hair between washes.", "Rice starch, Fragrance, Alcohol denat", 8.00, 11.00, "200ml"),
    ("Glow Beauty Co. Strong Hold Edge Control", "Glow Beauty Co.", "Styling", "edges, frizz, styling, humid-climate", "Non-flaking edge control for humid Bangladesh weather.", "Flaxseed, Olive oil, Castor oil", 10.00, 13.00, "100ml"),
    ("Wella EIMI Flexible Finish Hairspray", "Wella", "Styling", "hold, finishing, salon, humidity-resistant", "Light flexible hairspray with humidity resistance.", "Polymers, UV filter", 12.00, 15.00, "300ml"),
    ("Hair Fall Rescue Routine Set", "Glow Beauty Co.", "Hair Set", "hair-fall, routine-set, bangladesh, bundle", "3-step set: strengthening shampoo, conditioner, scalp serum.", "Biotin, Caffeine, Keratin", 42.00, 52.00, "3 items"),
    ("Curly Hair Hydration Set", "Glow Beauty Co.", "Hair Set", "curly, wavy, routine-set, humid-climate", "Curl shampoo, leave-in cream, and nourishing hair oil.", "Shea butter, Coconut oil, Glycerin", 48.00, 58.00, "3 items"),
    ("Scalp Care Anti-Dandruff Set", "Glow Beauty Co.", "Hair Set", "dandruff, oily-scalp, routine-set, bangladesh", "Anti-dandruff shampoo, scalp treatment, and tea tree oil.", "Pyrithione zinc, Tea tree, Salicylic acid", 45.00, 55.00, "3 items"),
    ("Bond Repair Salon Recovery Set", "Glow Beauty Co.", "Hair Set", "damaged, color-treated, routine-set, premium", "Bond repair shampoo, mask, and leave-in serum.", "Amino acids, Peptides, Argan oil", 58.00, 72.00, "3 items"),
]

IMAGES = [
    "https://burst.shopifycdn.com/photos/beauty-product-skincare.jpg?width=1000",
    "https://burst.shopifycdn.com/photos/skincare-products-on-white.jpg?width=1000",
    "https://burst.shopifycdn.com/photos/face-cream-jar.jpg?width=1000",
    "https://burst.shopifycdn.com/photos/amber-glass-bottle-with-skincare-product.jpg?width=1000",
    "https://burst.shopifycdn.com/photos/flatlay-of-skincare-products.jpg?width=1000",
]

CURRENCY_LABEL = "USD"


def main() -> None:
    with TEMPLATE.open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))

    rows = []
    for index, (title, vendor, ptype, tags, desc, ingredients, price, compare, size) in enumerate(PRODUCTS, 1):
        handle_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        sku = f"HC-{index:04d}"
        cost = round(price * 0.45, 2)
        full_desc = (
            f"{desc} Key ingredients: {ingredients}. Size: {size}. "
            f"Price listed in {CURRENCY_LABEL}. "
            "Trending hair care pick for Bangladesh — curated for Glow Beauty Co. from popular South Asian and global bestsellers."
        )
        category = CATEGORIES.get(ptype, CATEGORIES["Hair Serum"])
        row = {column: "" for column in header}
        row.update(
            {
                "Title": title,
                "URL handle": handle_slug,
                "Description": full_desc,
                "Vendor": vendor,
                "Product category": category,
                "Type": ptype,
                "Tags": f"{tags}, hair-care, usd-pricing, bangladesh",
                "Published on online store": "TRUE",
                "Status": "active",
                "SKU": sku,
                "Option1 name": "Size",
                "Option1 value": size,
                "Price": f"{price:.2f}",
                "Compare-at price": f"{compare:.2f}",
                "Cost per item": f"{cost:.2f}",
                "Charge tax": "TRUE",
                "Inventory tracker": "shopify",
                "Inventory quantity": str(35 + (index % 40)),
                "Continue selling when out of stock": "DENY",
                "Weight value (grams)": "200",
                "Weight unit for display": "g",
                "Requires shipping": "TRUE",
                "Fulfillment service": "manual",
                "Product image URL": IMAGES[index % len(IMAGES)],
                "Image position": "1",
                "Image alt text": title,
                "Gift card": "FALSE",
                "SEO title": f"{title} | {vendor} | Glow Beauty Hair",
                "SEO description": desc[:320],
                "Google Shopping / Google product category": category,
                "Google Shopping / Gender": "Unisex",
                "Google Shopping / Age group": "Adult (13+ years old)",
                "Google Shopping / Manufacturer part number (MPN)": sku,
                "Google Shopping / Ad group name": f"{ptype} Collection",
                "Google Shopping / Ads labels": tags,
                "Google Shopping / Condition": "New",
                "Google Shopping / Custom product": "FALSE",
                "Google Shopping / Custom label 0": vendor,
                "Google Shopping / Custom label 1": ptype,
            }
        )
        rows.append(row)

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} hair care products to {OUT} ({CURRENCY_LABEL})")


if __name__ == "__main__":
    main()

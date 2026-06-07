"""Generate Shopify product import CSV for Glow Beauty Co."""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "knowledge-base" / "glow-beauty-products-import.csv"
TEMPLATE = ROOT / "knowledge-base" / "product_template.csv"

CATEGORIES = {
    "Cleanser": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Cleansers",
    "Toner": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Toners & Astringents",
    "Serum": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Facial Treatments & Serums",
    "Moisturizer": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Moisturizers",
    "Sunscreen": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Sunscreen",
    "Mask": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Facial Masks",
    "Exfoliant": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Facial Peels",
    "Eye Care": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Eye Creams",
    "Lip Care": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Lip Balms & Treatments",
    "Body Care": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Body Moisturizers",
    "Mist": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Facial Mists",
    "Oil": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Facial Oils",
    "Spot Treatment": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Acne Treatments",
    "Set": "Health & Beauty > Personal Care > Cosmetics > Skin Care > Skin Care Sets",
}

# title, vendor, type, tags, description, ingredients, price, compare, size
PRODUCTS: list[tuple] = [
    ("Heartleaf Pore Control Cleansing Oil", "Anua", "Cleanser", "oily, combination, pore-care, k-beauty, fragrance-free", "Dissolves makeup and sunscreen while clearing clogged pores. Heartleaf soothes irritation.", "Heartleaf extract, Sunflower seed oil, Jojoba oil", 24.00, 28.00, "150ml"),
    ("Low pH Good Morning Gel Cleanser", "COSRX", "Cleanser", "oily, combination, gentle, daily, k-beauty", "Gentle gel cleanser with tea tree and BHA for morning refresh without stripping.", "Tea tree oil, Salicylic acid, Betaine", 14.00, 17.00, "150ml"),
    ("Hydrating Facial Cleanser", "CeraVe", "Cleanser", "dry, sensitive, barrier-repair, fragrance-free, dermatologist-tested", "Cream cleanser with ceramides and hyaluronic acid. Non-foaming and barrier-friendly.", "Ceramides, Hyaluronic acid, Glycerin", 16.00, 19.00, "236ml"),
    ("Foaming Facial Cleanser", "CeraVe", "Cleanser", "oily, normal, daily, foaming", "Foaming gel cleanser for normal to oily skin with niacinamide and ceramides.", "Niacinamide, Ceramides, Hyaluronic acid", 15.00, 18.00, "236ml"),
    ("Gentle Foaming Cleanser", "Glow Beauty Co.", "Cleanser", "sensitive, dry, fragrance-free, daily", "pH-balanced foam that removes impurities without disrupting the moisture barrier.", "Cocamidopropyl betaine, Glycerin, Chamomile extract", 18.00, 22.00, "150ml"),
    ("Rice Wash Face Cleanser", "Beauty of Joseon", "Cleanser", "combination, brightening, k-beauty, hydrating", "Low-irritation cleanser with rice extract for soft, bright-looking skin.", "Rice extract, Ginseng root water, Ceramides", 16.00, 20.00, "100ml"),
    ("Green Tea Amino Acid Cleansing Foam", "Haruharu Wonder", "Cleanser", "oily, combination, antioxidant, k-beauty", "Amino acid foam with green tea to cleanse while supporting antioxidant defense.", "Green tea extract, Amino acids, Panthenol", 15.00, 18.00, "120ml"),
    ("SA Smoothing Cleanser", "CeraVe", "Cleanser", "acne, oily, salicylic-acid, exfoliating", "Salicylic acid cleanser for rough and bumpy skin on face and body.", "Salicylic acid, Ceramides, Niacinamide", 17.00, 21.00, "236ml"),
    ("Centella Ampoule Foam", "Skin1004", "Cleanser", "sensitive, redness, madecassoside, k-beauty", "Madagascar centella foam cleanser for sensitive and reactive skin.", "Centella asiatica, Madecassoside, Ceramides", 16.00, 19.00, "125ml"),
    ("Matcha Hemp Hydrating Cleanser", "Krave Beauty", "Cleanser", "dry, sensitive, hydrating, antioxidant", "Non-stripping gel cleanser with matcha and hemp seed oil.", "Matcha, Hemp seed oil, Vitamin B5", 18.00, 22.00, "120ml"),
    ("Micellar Cleansing Water", "Bioderma", "Cleanser", "sensitive, makeup-remover, fragrance-free, all-skin-types", "No-rinse micellar water for gentle makeup removal and cleansing.", "Micellar technology, Cucumber extract", 19.00, 24.00, "250ml"),
    ("AHA BHA PHA 30 Days Miracle Acne Clear Foam", "Some By Mi", "Cleanser", "acne, oily, exfoliating, k-beauty", "Triple-acid foam for acne-prone skin with tea tree and centella.", "AHA, BHA, PHA, Tea tree, Centella", 15.00, 18.00, "100ml"),
    ("Heartleaf 77% Soothing Toner", "Anua", "Toner", "sensitive, redness, pore-care, k-beauty", "Lightweight toner with 77% heartleaf extract to calm and hydrate.", "Heartleaf extract, Panthenol, Hyaluronic acid", 22.00, 26.00, "250ml"),
    ("Ginseng Essence Water", "Beauty of Joseon", "Toner", "dry, anti-aging, brightening, k-beauty", "Hydrating essence toner with 80% ginseng water and niacinamide.", "Ginseng water, Niacinamide, Adenosine", 20.00, 24.00, "150ml"),
    ("Madagascar Centella Toning Toner", "Skin1004", "Toner", "sensitive, barrier-repair, k-beauty", "Soothing toner with centella to support barrier recovery.", "Centella asiatica, Panthenol, Hyaluronic acid", 18.00, 22.00, "210ml"),
    ("Green Tea Fresh Toner", "Isntree", "Toner", "oily, combination, antioxidant, pore-care", "Refreshing toner with 80% green tea from Jeju Island.", "Green tea extract, Hyaluronic acid, Allantoin", 17.00, 20.00, "200ml"),
    ("Supple Preparation Unscented Toner", "Klairs", "Toner", "sensitive, dry, fragrance-free, hydrating", "Hydrating toner without essential oils for sensitive skin.", "Hyaluronic acid, Beta-glucan, Centella", 19.00, 23.00, "180ml"),
    ("Dokdo Toner", "Round Lab", "Toner", "combination, hydration, deep-sea-minerals, k-beauty", "Lightweight toner with deep sea water from Ulleungdo for daily hydration.", "Deep sea water, Panthenol, Allantoin", 20.00, 24.00, "200ml"),
    ("Aloe BHA Skin Toner", "Benton", "Toner", "oily, acne, gentle-exfoliation, k-beauty", "Aloe-based toner with BHA for gentle pore care.", "Aloe vera, BHA, Snail secretion filtrate", 16.00, 19.00, "150ml"),
    ("Glow Toner with Niacinamide", "Glow Beauty Co.", "Toner", "combination, brightening, pore-care, daily", "Daily toner with niacinamide for smoother, more even-looking tone.", "Niacinamide, Panthenol, Witch hazel", 16.00, 20.00, "200ml"),
    ("Cicaplast B5 Soothing Toner", "La Roche-Posay", "Toner", "sensitive, barrier-repair, post-treatment", "Soothing toner for irritated skin after procedures or sun exposure.", "Panthenol, Madecassoside, Glycerin", 22.00, 26.00, "200ml"),
    ("Rose Petal Witch Hazel Toner", "Thayers", "Toner", "oily, combination, natural, alcohol-free", "Alcohol-free witch hazel toner with aloe and rose petal water.", "Witch hazel, Aloe vera, Rose water", 12.00, 15.00, "355ml"),
    ("Hyaluronic Acid Toner", "The Inkey List", "Toner", "dry, dehydration, budget-friendly, hydrating", "Multi-weight hyaluronic toner for layered hydration.", "Hyaluronic acid, Polyglutamic acid", 11.00, 14.00, "200ml"),
    ("Niacinamide 10% + Zinc 1% Serum", "The Ordinary", "Serum", "oily, acne, pore-care, budget-friendly", "High-strength niacinamide serum for blemishes and congestion.", "Niacinamide, Zinc PCA", 7.00, 9.00, "30ml"),
    ("Niacinamide 10% Oil Control Serum", "Glow Beauty Co.", "Serum", "oily, acne-prone, pore-care, daily", "Lightweight serum to regulate oil and calm redness.", "Niacinamide, Zinc PCA, Hyaluronic acid", 28.00, 34.00, "30ml"),
    ("Niacinamide Brightening Serum", "Medicube", "Serum", "hyperpigmentation, oily, k-beauty, brightening", "Niacinamide serum for dull and uneven skin tone.", "Niacinamide, Glutathione, Arbutin", 24.00, 28.00, "30ml"),
    ("Zero Pore Blackhead Serum", "Medicube", "Serum", "oily, pore-care, blackhead, k-beauty", "Pore-tightening serum for blackheads and enlarged pores.", "AHA, BHA, Witch hazel", 26.00, 30.00, "30ml"),
    ("Vitamin C 15% Brightening Serum", "Glow Beauty Co.", "Serum", "brightening, dark-spots, antioxidant, morning", "Antioxidant serum for dull skin and uneven tone. Use before SPF.", "L-Ascorbic acid, Ferulic acid, Vitamin E", 34.00, 40.00, "30ml"),
    ("Vitamin C Suspension 23% + HA Spheres 2%", "The Ordinary", "Serum", "brightening, budget-friendly, anti-aging", "High-strength vitamin C for visible brightening.", "Ascorbic acid, Hyaluronic acid spheres", 8.00, 10.00, "30ml"),
    ("Madagascar Centella Vita-C Serum", "Skin1004", "Serum", "brightening, sensitive, k-beauty, vitamin-c", "Gentle vitamin C derivative serum with centella.", "Ascorbyl glucoside, Centella, Niacinamide", 22.00, 26.00, "30ml"),
    ("Glow Deep Serum Rice + Alpha-Arbutin", "Beauty of Joseon", "Serum", "brightening, hyperpigmentation, k-beauty", "Brightening serum with rice and alpha-arbutin.", "Rice extract, Alpha-arbutin, Niacinamide", 18.00, 22.00, "30ml"),
    ("Hyaluronic Acid 2% + B5 Serum", "The Ordinary", "Serum", "dry, dehydration, budget-friendly, all-skin-types", "Multi-depth hydration serum with vitamin B5.", "Hyaluronic acid, Panthenol", 8.00, 10.00, "30ml"),
    ("Hyaluronic Acid Aqua Boost Serum", "Torriden", "Serum", "dry, dehydration, k-beauty, barrier-repair", "5D hyaluronic complex for deep hydration.", "Hyaluronic acid, Panthenol, Ceramides", 20.00, 24.00, "50ml"),
    ("Dive-In Low Molecule Hyaluronic Acid Serum", "Torriden", "Serum", "dry, sensitive, hydrating, k-beauty", "Fast-absorbing serum with low molecular HA.", "Hyaluronic acid, D-Panthenol, Allantoin", 22.00, 26.00, "50ml"),
    ("Retinol 0.3% Night Renewal Serum", "Glow Beauty Co.", "Serum", "anti-aging, fine-lines, night-care, mature", "Night serum to support smoother-looking skin over time.", "Retinol, Peptides, Squalane", 38.00, 45.00, "30ml"),
    ("Retinol 0.5% in Squalane", "The Ordinary", "Serum", "anti-aging, budget-friendly, night-care", "Moderate-strength retinol in nourishing squalane.", "Retinol, Squalane", 9.00, 12.00, "30ml"),
    ("Revive Eye Serum Ginseng + Retinal", "Beauty of Joseon", "Eye Care", "anti-aging, dark-circles, k-beauty, eye-care", "Eye serum with ginseng and retinal for fine lines.", "Ginseng, Retinal, Niacinamide", 18.00, 22.00, "30ml"),
    ("Retinol B3 Anti-Wrinkle Serum", "La Roche-Posay", "Serum", "anti-aging, sensitive, fine-lines, dermatologist-tested", "Retinol serum formulated for sensitive aging skin.", "Retinol, Niacinamide, Glycerin", 42.00, 48.00, "30ml"),
    ("Salicylic Acid 2% BHA Exfoliant Serum", "Glow Beauty Co.", "Serum", "acne, oily, pore-care, exfoliating", "Leave-on BHA for clogged pores and uneven texture.", "Salicylic acid, Green tea, Allantoin", 22.00, 26.00, "100ml"),
    ("Salicylic Acid 2% Solution", "The Ordinary", "Serum", "acne, oily, budget-friendly, bha", "BHA solution for blemish-prone skin.", "Salicylic acid", 7.00, 9.00, "30ml"),
    ("AHA 30% + BHA 2% Peeling Solution", "The Ordinary", "Serum", "exfoliating, texture, weekly-treatment, advanced", "Weekly exfoliating treatment for experienced users.", "Glycolic acid, Salicylic acid", 9.00, 12.00, "30ml"),
    ("Azelaic Acid Suspension 10%", "The Ordinary", "Serum", "acne, redness, rosacea-prone, brightening", "Multi-purpose azelaic acid for blemishes and redness.", "Azelaic acid", 10.00, 13.00, "30ml"),
    ("Glow Serum Propolis + Niacinamide", "Beauty of Joseon", "Serum", "combination, soothing, brightening, k-beauty", "Propolis serum for radiance and irritation support.", "Propolis, Niacinamide, Honey extract", 18.00, 22.00, "30ml"),
    ("Snail 96 Mucin Power Essence", "COSRX", "Serum", "dry, repair, k-beauty, hydrating", "Lightweight snail mucin essence for hydration and repair.", "Snail secretion filtrate, Betaine", 18.00, 22.00, "100ml"),
    ("Advanced Snail 92 All In One Cream", "COSRX", "Moisturizer", "dry, repair, k-beauty, barrier-repair", "Snail mucin moisturizer for damaged and dry skin.", "Snail secretion filtrate, Betaine, Panthenol", 20.00, 24.00, "100ml"),
    ("Red Bean Water Gel", "Beauty of Joseon", "Moisturizer", "oily, pore-care, lightweight, k-beauty", "Lightweight gel moisturizer with red bean and peptides.", "Red bean extract, Peptides, Panthenol", 18.00, 22.00, "100ml"),
    ("Ceramide Ato Concentrate Cream", "Illiyoon", "Moisturizer", "dry, eczema-prone, barrier-repair, k-beauty", "Ceramide cream for very dry and eczema-prone skin.", "Ceramides, Squalane, Panthenol", 22.00, 26.00, "200ml"),
    ("Peptide 21% Serum", "The Inkey List", "Serum", "anti-aging, fine-lines, peptides, budget-friendly", "Multi-peptide serum for firmness and elasticity.", "Peptides, Hyaluronic acid", 16.00, 19.00, "30ml"),
    ("Caffeine Solution 5% + EGCG", "The Ordinary", "Serum", "dark-circles, puffiness, eye-area, budget-friendly", "Targeted serum for under-eye puffiness and dark circles.", "Caffeine, EGCG", 8.00, 10.00, "30ml"),
    ("Alpha Arbutin 2% + HA Serum", "The Ordinary", "Serum", "hyperpigmentation, brightening, budget-friendly", "Serum for dark spots and uneven tone.", "Alpha arbutin, Hyaluronic acid", 11.00, 14.00, "30ml"),
    ("Centella Asiatica Extract Ampoule", "Skin1004", "Serum", "sensitive, redness, soothing, k-beauty", "Pure centella ampoule for irritated skin.", "Centella asiatica, Madecassoside", 20.00, 24.00, "55ml"),
    ("Dark Spot Correcting Glow Serum", "Axis-Y", "Serum", "hyperpigmentation, brightening, k-beauty, niacinamide", "Brightening serum with niacinamide and plant extracts.", "Niacinamide, Sea buckthorn, Squalane", 18.00, 22.00, "50ml"),
    ("Mugwort Essence", "Arencia", "Serum", "sensitive, soothing, k-beauty, redness", "Single-ingredient mugwort essence for calming skin.", "Mugwort extract", 24.00, 28.00, "120ml"),
    ("Collagen Boosting Peptide Serum", "Glow Beauty Co.", "Serum", "anti-aging, collagen, firmness, mature", "Peptide and collagen-support serum for elasticity.", "Peptides, Collagen amino acids, Hyaluronic acid", 32.00, 38.00, "30ml"),
    ("Ashwagandha Calming Serum", "Glow Beauty Co.", "Serum", "sensitive, adaptogen, redness, trending-2025", "Adaptogen serum with niacinamide for stressed skin.", "Ashwagandha, Niacinamide, Ceramides", 30.00, 36.00, "30ml"),
    ("Ceramide Barrier Repair Cream", "Glow Beauty Co.", "Moisturizer", "dry, sensitive, barrier-repair, ceramides", "Rich cream supporting barrier recovery and hydration.", "Ceramides, Cholesterol, Fatty acids", 30.00, 36.00, "50ml"),
    ("Moisturizing Cream", "CeraVe", "Moisturizer", "dry, normal, barrier-repair, dermatologist-tested", "Daily moisturizer with ceramides and MVE technology.", "Ceramides, Hyaluronic acid, MVE technology", 17.00, 20.00, "340g"),
    ("PM Facial Moisturizing Lotion", "CeraVe", "Moisturizer", "combination, night-care, niacinamide, lightweight", "Night lotion with niacinamide and ceramides.", "Niacinamide, Ceramides, Hyaluronic acid", 16.00, 19.00, "52ml"),
    ("Oil-Free Hydrating Gel Moisturizer", "Glow Beauty Co.", "Moisturizer", "oily, acne-prone, lightweight, non-comedogenic", "Gel moisturizer that hydrates without heaviness.", "Hyaluronic acid, Niacinamide, Aloe vera", 24.00, 28.00, "50ml"),
    ("Dynasty Cream", "Beauty of Joseon", "Moisturizer", "dry, anti-aging, k-beauty, nourishing", "Luxurious cream with rice bran, ginseng, and squalane.", "Rice bran, Ginseng, Squalane", 24.00, 28.00, "50ml"),
    ("Water Bank Blue HA Cream", "Laneige", "Moisturizer", "dry, dehydration, k-beauty, hydrating", "Deep hydration cream with blue hyaluronic acid.", "Hyaluronic acid, Mineral water, Squalane", 32.00, 38.00, "50ml"),
    ("Moisturizing Ointment Sensitive Skin", "Vanicream", "Moisturizer", "dry, eczema-prone, sensitive, fragrance-free", "Long-lasting ointment for very dry and irritated skin.", "Petrolatum, Mineral oil, Cetearyl alcohol", 14.00, 17.00, "368g"),
    ("Toleriane Double Repair Face Moisturizer", "La Roche-Posay", "Moisturizer", "sensitive, barrier-repair, niacinamide, dermatologist-tested", "Daily moisturizer with prebiotic thermal water and ceramides.", "Niacinamide, Ceramides, Prebiotic water", 22.00, 26.00, "75ml"),
    ("Daily Moisturizing Lotion", "Eucerin", "Moisturizer", "dry, body-face, fragrance-free, sensitive", "Lightweight lotion for dry and sensitive skin.", "Urea, Ceramides, Glycerin", 14.00, 17.00, "200ml"),
    ("Hydro Boost Water Gel", "Neutrogena", "Moisturizer", "oily, combination, gel, hydrating", "Oil-free gel moisturizer with hyaluronic acid.", "Hyaluronic acid, Glycerin, Olive extract", 18.00, 22.00, "50ml"),
    ("Regenerist Micro-Sculpting Cream", "Olay", "Moisturizer", "anti-aging, mature, peptides, firmness", "Anti-aging cream with niacinamide and peptides.", "Niacinamide, Peptides, Glycerin", 28.00, 34.00, "50ml"),
    ("Midnight Recovery Omega-Rich Cloud Cream", "Glow Beauty Co.", "Moisturizer", "dry, night-care, omega, barrier-repair", "Night cream with omega fatty acids for barrier support.", "Omega fatty acids, Ceramides, Squalane", 34.00, 40.00, "50ml"),
    ("Relief Sun Rice + Probiotics SPF50+ PA++++", "Beauty of Joseon", "Sunscreen", "all-skin-types, k-beauty, no-white-cast, trending", "Lightweight chemical sunscreen with rice and probiotics.", "Rice extract, Probiotics, Niacinamide", 18.00, 22.00, "50ml"),
    ("Relief Sun Aqua-Fresh Rice + B5 SPF50+ PA++++", "Beauty of Joseon", "Sunscreen", "oily, combination, lightweight, k-beauty", "Watery sunscreen with rice water and panthenol.", "Rice seed water, Panthenol, Ceramides", 18.00, 22.00, "50ml"),
    ("Daily SPF 50 Mineral Sunscreen", "Glow Beauty Co.", "Sunscreen", "sensitive, mineral, fragrance-free, reef-safe", "Broad-spectrum mineral SPF with lightweight finish.", "Zinc oxide, Titanium dioxide, Niacinamide", 26.00, 30.00, "50ml"),
    ("Anthelios Melt-In Milk SPF 60", "La Roche-Posay", "Sunscreen", "all-skin-types, high-spf, dermatologist-tested", "High-protection sunscreen with Cell-Ox Shield technology.", "Mexoryl, Antioxidants, Glycerin", 32.00, 38.00, "150ml"),
    ("UV Aqua Rich Watery Essence SPF50+ PA++++", "Biore", "Sunscreen", "oily, lightweight, japanese, daily", "Popular watery essence sunscreen for daily use.", "Hyaluronic acid, Royal jelly, Citrus extract", 14.00, 17.00, "50ml"),
    ("Quick Sunstick Protection Bar SPF50+ PA++++", "Abib", "Sunscreen", "oily, portable, stick, k-beauty", "Convenient sun stick for on-the-go reapplication.", "Chemical UV filters, Centella, Eucalyptus", 16.00, 19.00, "22g"),
    ("Hyaluronic Acid Watery Sun Gel SPF50+ PA++++", "Isntree", "Sunscreen", "dry, hydrating, k-beauty, no-white-cast", "Hydrating sun gel with 8 types of hyaluronic acid.", "Hyaluronic acid, Niacinamide, Adenosine", 18.00, 22.00, "50ml"),
    ("Unseen Sunscreen SPF 40", "Supergoop!", "Sunscreen", "all-skin-types, makeup-primer, clean, trending", "Invisible weightless sunscreen that doubles as primer.", "Chemical UV filters, Frankincense, Meadowfoam", 36.00, 42.00, "50ml"),
    ("Mineral Matte Sunscreen SPF 30", "Glow Beauty Co.", "Sunscreen", "oily, matte, mineral, acne-prone", "Oil-control mineral sunscreen for shine-prone skin.", "Zinc oxide, Niacinamide, Silica", 24.00, 28.00, "50ml"),
    ("Kids Gentle Mineral Sunscreen SPF 50", "Glow Beauty Co.", "Sunscreen", "sensitive, family, mineral, fragrance-free", "Gentle mineral sunscreen suitable for sensitive skin.", "Zinc oxide, Titanium dioxide, Aloe vera", 20.00, 24.00, "100ml"),
    ("Overnight Hydrating Sleep Mask", "Glow Beauty Co.", "Mask", "dry, night-care, hydrating, weekly", "Overnight mask to lock in moisture while you sleep.", "Hyaluronic acid, Ceramides, Squalane", 22.00, 26.00, "75ml"),
    ("Pore Clearing Clay Mask", "Glow Beauty Co.", "Mask", "oily, pore-care, clay, weekly", "Kaolin clay mask to absorb excess oil and refine pores.", "Kaolin clay, Salicylic acid, Charcoal", 20.00, 24.00, "100ml"),
    ("Snail Hydrogel Sheet Mask 5-Pack", "COSRX", "Mask", "dry, hydrating, k-beauty, sheet-mask", "Hydrogel sheet masks infused with snail mucin.", "Snail secretion filtrate, Hyaluronic acid", 15.00, 18.00, "5 pack"),
    ("Heartleaf Calming Sheet Mask 10-Pack", "Anua", "Mask", "sensitive, soothing, k-beauty, sheet-mask", "Calming sheet masks with heartleaf extract.", "Heartleaf extract, Panthenol, Allantoin", 22.00, 26.00, "10 pack"),
    ("Rice Glow Brightening Mask", "Beauty of Joseon", "Mask", "brightening, dullness, k-beauty, wash-off", "Wash-off mask with rice and honey for glow.", "Rice extract, Honey, Niacinamide", 16.00, 19.00, "150ml"),
    ("Super Volcanic Pore Clay Mask", "Innisfree", "Mask", "oily, pore-care, clay, k-beauty", "Volcanic clay mask for deep pore cleansing.", "Volcanic ash, AHA, Walnut shell powder", 16.00, 19.00, "100ml"),
    ("Cicaplast Baume B5 Repair Mask", "La Roche-Posay", "Mask", "sensitive, barrier-repair, post-treatment", "Soothing repair mask with panthenol and madecassoside.", "Panthenol, Madecassoside, Shea butter", 24.00, 28.00, "100ml"),
    ("Collagen Overnight Lip Mask", "Laneige", "Lip Care", "dry-lips, night-care, k-beauty, hydrating", "Berry-scented lip sleeping mask for soft lips.", "Berry complex, Vitamin C, Shea butter", 18.00, 22.00, "20g"),
    ("Aloe Soothing Gel Mask", "Nature Republic", "Mask", "sensitive, sunburn, soothing, budget-friendly", "Cooling aloe gel mask for irritated or sun-exposed skin.", "Aloe vera, Cucumber extract", 10.00, 13.00, "300ml"),
    ("Charcoal Detox Peel-Off Mask", "Glow Beauty Co.", "Mask", "oily, blackhead, detox, weekly", "Peel-off mask with charcoal to lift surface impurities.", "Charcoal, Witch hazel, Glycerin", 16.00, 20.00, "80ml"),
    ("Salicylic Acid 2% BHA Exfoliant", "Paula's Choice", "Exfoliant", "acne, oily, pore-care, cult-favorite", "Leave-on BHA exfoliant for smoother, clearer skin.", "Salicylic acid, Green tea, Methylpropanediol", 32.00, 38.00, "118ml"),
    ("Retinol 0.3% Night Renewal Cream", "Glow Beauty Co.", "Exfoliant", "anti-aging, night-care, retinol, fine-lines", "Night treatment cream with retinol and ceramides.", "Retinol, Peptides, Ceramides", 42.00, 48.00, "30ml"),
    ("Mandelic Acid 10% + HA Serum", "The Ordinary", "Exfoliant", "sensitive, gentle-exfoliation, budget-friendly", "Gentle AHA for uneven tone and texture.", "Mandelic acid, Hyaluronic acid", 8.00, 10.00, "30ml"),
    ("Glycolic Acid 7% Toning Solution", "The Ordinary", "Exfoliant", "texture, dullness, budget-friendly, toner", "Daily glycolic toner for brighter-looking skin.", "Glycolic acid, Aloe vera, Ginseng", 9.00, 12.00, "240ml"),
    ("PHA Soft Peeling Gel", "Glow Beauty Co.", "Exfoliant", "sensitive, gentle-exfoliation, weekly", "Gentle PHA peeling gel for sensitive skin.", "PHA, Centella, Panthenol", 18.00, 22.00, "100ml"),
    ("Blackhead Power Liquid", "COSRX", "Exfoliant", "blackhead, oily, bha, k-beauty", "BHA liquid for blackhead and sebum control.", "Betaine salicylate, Willow bark water", 16.00, 19.00, "100ml"),
    ("AHA BHA Clarifying Treatment Toner", "COSRX", "Exfoliant", "oily, texture, daily, k-beauty", "Daily clarifying toner with willow bark and apple water.", "AHA, BHA, Willow bark water", 16.00, 19.00, "150ml"),
    ("Rice Enzyme Brightening Powder Wash", "Glow Beauty Co.", "Exfoliant", "brightening, gentle-exfoliation, powder", "Enzyme powder wash for smooth, bright-looking skin.", "Rice enzymes, Papaya enzymes, Allantoin", 20.00, 24.00, "60g"),
    ("Caffeine Depuffing Eye Cream", "Glow Beauty Co.", "Eye Care", "dark-circles, puffiness, morning, caffeine", "Cooling eye cream with caffeine and peptides.", "Caffeine, Peptides, Hyaluronic acid", 22.00, 26.00, "15ml"),
    ("Ceramide Eye Repair Cream", "Glow Beauty Co.", "Eye Care", "dry, anti-aging, barrier-repair, eye-care", "Nourishing eye cream with ceramides and squalane.", "Ceramides, Squalane, Peptides", 26.00, 30.00, "15ml"),
    ("Bakuchiol Eye Serum", "Glow Beauty Co.", "Eye Care", "sensitive, anti-aging, retinol-alternative", "Gentle bakuchiol eye serum for fine lines.", "Bakuchiol, Peptides, Vitamin E", 24.00, 28.00, "15ml"),
    ("Vita-C Dark Circle Eye Gel", "Axis-Y", "Eye Care", "dark-circles, brightening, k-beauty", "Vitamin C eye gel for dark circles and dullness.", "Vitamin C, Niacinamide, Adenosine", 16.00, 19.00, "10ml"),
    ("Peptide 360 Eye Cream", "The Inkey List", "Eye Care", "anti-aging, budget-friendly, peptides", "Multi-peptide eye cream for crow's feet.", "Peptides, Hyaluronic acid, Shea butter", 14.00, 17.00, "15ml"),
    ("SPF 30 Lip Balm", "Glow Beauty Co.", "Lip Care", "sun-protection, daily, hydrating, fragrance-free", "Hydrating lip balm with broad-spectrum SPF.", "Zinc oxide, Shea butter, Vitamin E", 8.00, 10.00, "4g"),
    ("Peptide Plumping Lip Treatment", "Glow Beauty Co.", "Lip Care", "dry-lips, anti-aging, plumping", "Peptide lip treatment for smoother, fuller-looking lips.", "Peptides, Hyaluronic acid, Ceramides", 12.00, 15.00, "10ml"),
    ("Honey Overnight Lip Mask", "Glow Beauty Co.", "Lip Care", "dry-lips, night-care, nourishing", "Rich overnight lip mask with honey and shea butter.", "Honey, Shea butter, Vitamin E", 10.00, 13.00, "15ml"),
    ("SA Smoothing Body Lotion", "CeraVe", "Body Care", "body, rough-skin, salicylic-acid, keratosis", "Salicylic acid body lotion for rough and bumpy skin.", "Salicylic acid, Ceramides, Niacinamide", 16.00, 19.00, "236ml"),
    ("Daily Moisturizing Body Lotion", "Glow Beauty Co.", "Body Care", "body, dry, fragrance-free, daily", "Lightweight daily body lotion with ceramides.", "Ceramides, Glycerin, Squalane", 14.00, 17.00, "400ml"),
    ("Brightening Body Serum", "Glow Beauty Co.", "Body Care", "body, hyperpigmentation, brightening, niacinamide", "Body serum for uneven tone on neck, chest, and arms.", "Niacinamide, Alpha arbutin, Vitamin E", 22.00, 26.00, "200ml"),
    ("AHA Body Exfoliating Lotion", "Glow Beauty Co.", "Body Care", "body, texture, exfoliating, kp", "Gentle AHA body lotion for smoother skin texture.", "Lactic acid, Urea, Ceramides", 20.00, 24.00, "200ml"),
    ("Hand Repair Cream with Ceramides", "Glow Beauty Co.", "Body Care", "hands, dry, barrier-repair, fragrance-free", "Rich hand cream for dry and cracked hands.", "Ceramides, Glycerin, Dimethicone", 12.00, 15.00, "50ml"),
    ("Cica Calming Face Mist", "Glow Beauty Co.", "Mist", "sensitive, redness, on-the-go, soothing", "Fine mist with centella for instant calming.", "Centella, Panthenol, Hyaluronic acid", 14.00, 17.00, "100ml"),
    ("Rose Hydrating Face Mist", "Glow Beauty Co.", "Mist", "dry, hydration, makeup-refresh, floral", "Hydrating rose mist to refresh skin throughout the day.", "Rose water, Glycerin, Aloe vera", 12.00, 15.00, "120ml"),
    ("Squalane Facial Oil", "The Ordinary", "Oil", "dry, all-skin-types, budget-friendly, occlusive", "Plant-derived squalane for sealing in moisture.", "Squalane", 9.00, 12.00, "30ml"),
    ("Tea Tree Purifying Face Oil", "Glow Beauty Co.", "Oil", "oily, acne, lightweight, spot-care", "Lightweight oil blend for blemish-prone areas.", "Tea tree oil, Jojoba oil, Squalane", 16.00, 19.00, "30ml"),
    ("Acne Pimple Master Patch 24-Pack", "COSRX", "Spot Treatment", "acne, spot-treatment, k-beauty, hydrocolloid", "Hydrocolloid patches to absorb impurities overnight.", "Hydrocolloid, Tea tree oil", 6.00, 8.00, "24 patches"),
    ("Invisible Acne Spot Gel", "Glow Beauty Co.", "Spot Treatment", "acne, spot-treatment, salicylic-acid, fast-acting", "Clear spot gel with salicylic acid and zinc.", "Salicylic acid, Zinc PCA, Niacinamide", 10.00, 13.00, "15ml"),
    ("Centella Blemish Cream", "Purito", "Spot Treatment", "acne, soothing, k-beauty, centella", "Centella spot cream for inflamed blemishes.", "Centella, Zinc oxide, Calamine", 12.00, 15.00, "30ml"),
    ("Oily Skin Starter Routine Set", "Glow Beauty Co.", "Set", "oily, acne-prone, routine-set, bundle", "3-step set: gel cleanser, niacinamide serum, oil-free moisturizer.", "Niacinamide, Salicylic acid, Hyaluronic acid", 58.00, 72.00, "3 items"),
    ("Dry Skin Barrier Repair Set", "Glow Beauty Co.", "Set", "dry, sensitive, routine-set, bundle", "3-step set: cream cleanser, HA serum, ceramide cream.", "Ceramides, Hyaluronic acid, Panthenol", 62.00, 78.00, "3 items"),
    ("Brightening Morning Routine Set", "Glow Beauty Co.", "Set", "brightening, morning, routine-set, bundle", "Vitamin C serum, moisturizer, and SPF 50 sunscreen.", "Vitamin C, Niacinamide, SPF filters", 68.00, 85.00, "3 items"),
    ("Anti-Aging Night Routine Set", "Glow Beauty Co.", "Set", "anti-aging, night-care, routine-set, bundle", "Retinol serum, peptide eye cream, and renewal cream.", "Retinol, Peptides, Ceramides", 78.00, 95.00, "3 items"),
    ("K-Beauty Bestsellers Discovery Set", "Glow Beauty Co.", "Set", "k-beauty, bestseller, discovery-set, trending", "Curated minis inspired by trending K-beauty essentials.", "Rice extract, Centella, Propolis", 45.00, 55.00, "5 minis"),
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
    if len(PRODUCTS) < 100:
        raise SystemExit(f"Expected at least 100 products, got {len(PRODUCTS)}")

    with TEMPLATE.open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))

    rows = []
    for index, (title, vendor, ptype, tags, desc, ingredients, price, compare, size) in enumerate(PRODUCTS, 1):
        handle_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        sku = f"GB-{index:04d}"
        cost = round(price * 0.45, 2)
        full_desc = (
            f"{desc} Key ingredients: {ingredients}. Size: {size}. "
            f"Price listed in {CURRENCY_LABEL}. "
            "Curated for Glow Beauty Co. based on trending skincare favorites from premium beauty retailers and global bestseller trends."
        )
        category = CATEGORIES.get(ptype, CATEGORIES["Serum"])
        row = {column: "" for column in header}
        row.update(
            {
                "Title": title,
                "URL handle": handle_slug,
                "Description": full_desc,
                "Vendor": vendor,
                "Product category": category,
                "Type": ptype,
                "Tags": f"{tags}, usd-pricing",
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
                "Inventory quantity": str(40 + (index % 35)),
                "Continue selling when out of stock": "DENY",
                "Weight value (grams)": "120",
                "Weight unit for display": "g",
                "Requires shipping": "TRUE",
                "Fulfillment service": "manual",
                "Product image URL": IMAGES[index % len(IMAGES)],
                "Image position": "1",
                "Image alt text": title,
                "Gift card": "FALSE",
                "SEO title": f"{title} | {vendor} | Glow Beauty",
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

    print(f"Wrote {len(rows)} products to {OUT} ({CURRENCY_LABEL})")


if __name__ == "__main__":
    main()

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import (
    Base,
    Conversation,
    Customer,
    Document,
    EmbeddingRecord,
    Message,
    Order,
    Product,
    Store,
)
from app.db.session import engine
from app.services.rag import chunk_text, generate_embeddings, index_product_embeddings


DEMO_PRODUCTS = [
    {
        "shopify_product_id": "gid://shopify/Product/1001",
        "handle": "niacinamide-10-oil-control-serum",
        "title": "Niacinamide 10% Oil Control Serum",
        "description": "Lightweight serum that helps regulate excess oil, minimize pores, and calm redness. Ideal for oily and acne-prone skin.",
        "ingredients": "Niacinamide, Zinc PCA, Hyaluronic Acid, Panthenol",
        "collections": ["Serums", "Acne Care", "Oily Skin"],
        "variants": [{"title": "30ml", "price": "28.00"}],
        "price": "$28.00",
    },
    {
        "shopify_product_id": "gid://shopify/Product/1002",
        "handle": "vitamin-c-15-brightening-serum",
        "title": "Vitamin C 15% Brightening Serum",
        "description": "Antioxidant serum that brightens dull skin and supports an even tone. Best used in the morning before sunscreen.",
        "ingredients": "L-Ascorbic Acid, Ferulic Acid, Vitamin E, Hyaluronic Acid",
        "collections": ["Serums", "Brightening"],
        "variants": [{"title": "30ml", "price": "34.00"}],
        "price": "$34.00",
    },
    {
        "shopify_product_id": "gid://shopify/Product/1003",
        "handle": "oil-free-hydrating-gel-moisturizer",
        "title": "Oil-Free Hydrating Gel Moisturizer",
        "description": "Non-comedogenic gel moisturizer that hydrates without heaviness. Suitable for oily, combination, and acne-prone skin.",
        "ingredients": "Hyaluronic Acid, Niacinamide, Aloe Vera, Squalane",
        "collections": ["Moisturizers", "Oily Skin"],
        "variants": [{"title": "50ml", "price": "24.00"}],
        "price": "$24.00",
    },
    {
        "shopify_product_id": "gid://shopify/Product/1004",
        "handle": "gentle-foaming-cleanser",
        "title": "Gentle Foaming Cleanser",
        "description": "pH-balanced cleanser that removes makeup and impurities without stripping the skin barrier.",
        "ingredients": "Cocamidopropyl Betaine, Glycerin, Chamomile Extract",
        "collections": ["Cleansers", "Sensitive Skin"],
        "variants": [{"title": "150ml", "price": "18.00"}],
        "price": "$18.00",
    },
    {
        "shopify_product_id": "gid://shopify/Product/1005",
        "handle": "daily-spf-50-mineral-sunscreen",
        "title": "Daily SPF 50 Mineral Sunscreen",
        "description": "Broad-spectrum mineral sunscreen with a lightweight finish. Fragrance-free and suitable for sensitive skin.",
        "ingredients": "Zinc Oxide, Titanium Dioxide, Niacinamide, Squalane",
        "collections": ["Sunscreen", "Sensitive Skin"],
        "variants": [{"title": "50ml", "price": "26.00"}],
        "price": "$26.00",
    },
    {
        "shopify_product_id": "gid://shopify/Product/1006",
        "handle": "retinol-0-3-night-renewal-cream",
        "title": "Retinol 0.3% Night Renewal Cream",
        "description": "Night treatment that supports smoother-looking skin and helps reduce the appearance of fine lines over time.",
        "ingredients": "Retinol, Peptides, Ceramides, Shea Butter",
        "collections": ["Night Care", "Anti-Aging"],
        "variants": [{"title": "30ml", "price": "42.00"}],
        "price": "$42.00",
    },
    {
        "shopify_product_id": "gid://shopify/Product/1007",
        "handle": "salicylic-acid-2-bha-exfoliant",
        "title": "Salicylic Acid 2% BHA Exfoliant",
        "description": "Leave-on exfoliant that helps clear clogged pores and smooth uneven texture for acne-prone skin.",
        "ingredients": "Salicylic Acid, Green Tea Extract, Allantoin",
        "collections": ["Exfoliants", "Acne Care"],
        "variants": [{"title": "100ml", "price": "22.00"}],
        "price": "$22.00",
    },
    {
        "shopify_product_id": "gid://shopify/Product/1008",
        "handle": "ceramide-barrier-repair-cream",
        "title": "Ceramide Barrier Repair Cream",
        "description": "Rich cream for dry and sensitive skin that supports barrier recovery and long-lasting hydration.",
        "ingredients": "Ceramides, Cholesterol, Fatty Acids, Panthenol",
        "collections": ["Moisturizers", "Dry Skin", "Sensitive Skin"],
        "variants": [{"title": "50ml", "price": "30.00"}],
        "price": "$30.00",
    },
]

DEMO_DOCUMENTS = [
    {
        "filename": "shipping-policy.txt",
        "content_type": "text/plain",
        "raw_text": (
            "Shipping Policy\n"
            "We ship domestically within 3-5 business days and internationally within 7-14 business days.\n"
            "Orders over $50 qualify for free standard shipping in the US.\n"
            "Once shipped, customers receive a tracking number by email.\n"
            "International customers are responsible for customs duties where applicable."
        ),
    },
    {
        "filename": "return-refund-policy.txt",
        "content_type": "text/plain",
        "raw_text": (
            "Return and Refund Policy\n"
            "Unopened products may be returned within 30 days of delivery.\n"
            "Opened skincare products can be returned only if defective or damaged on arrival.\n"
            "Refunds are processed within 5-7 business days after the return is received.\n"
            "To start a return, contact support with your order number."
        ),
    },
    {
        "filename": "ingredient-faq.txt",
        "content_type": "text/plain",
        "raw_text": (
            "Ingredient FAQ\n"
            "Niacinamide and Vitamin C can be used together. For sensitive skin, use Vitamin C in the morning and Niacinamide at night.\n"
            "Retinol should be introduced slowly, 2-3 nights per week, and always paired with sunscreen during the day.\n"
            "Salicylic acid is helpful for oily and acne-prone skin but may be too strong for very dry or compromised barriers.\n"
            "If you experience severe irritation, rash, or swelling, stop use and consult a dermatologist."
        ),
    },
    {
        "filename": "store-faq.txt",
        "content_type": "text/plain",
        "raw_text": (
            "Store FAQ\n"
            "All products are cruelty-free and dermatologist-tested.\n"
            "Fragrance-free options are labeled clearly in product descriptions.\n"
            "We do not provide medical diagnoses or prescribe treatments.\n"
            "For personalized medical advice, please consult a licensed dermatologist."
        ),
    },
]


def init_database() -> None:
    with engine.begin() as connection:
        try:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            # Render managed Postgres may not include pgvector; JSON embeddings still work.
            pass
    Base.metadata.create_all(bind=engine)
    _apply_additive_migrations()


def _apply_additive_migrations() -> None:
    """Idempotent column additions so existing databases gain new fields.

    create_all() never alters existing tables, so new columns must be added
    explicitly. These are safe to run on every startup.
    """
    statements = [
        "ALTER TABLE stores ADD COLUMN IF NOT EXISTS site_type VARCHAR(32) DEFAULT 'shopify'",
        "ALTER TABLE stores ADD COLUMN IF NOT EXISTS website_url VARCHAR(512)",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS handle VARCHAR(512)",
    ]
    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception:
                # Non-Postgres backends or already-applied changes can be ignored.
                pass


def seed_demo_data(db: Session) -> None:
    existing = db.query(Store).filter(Store.shopify_domain == "demo-glow-beauty.myshopify.com").first()
    if existing:
        return

    store = Store(
        shopify_domain="demo-glow-beauty.myshopify.com",
        access_token="demo-access-token",
        name="Glow Beauty Co.",
    )
    db.add(store)
    db.flush()

    for product_data in DEMO_PRODUCTS:
        db.add(Product(store_id=store.id, **product_data))
    db.flush()
    index_product_embeddings(db, store.id)

    customer = Customer(
        store_id=store.id,
        shopify_customer_id="gid://shopify/Customer/9001",
        email="ava.customer@example.com",
        first_name="Ava",
        last_name="Chen",
    )
    db.add(customer)
    db.flush()

    db.add(
        Order(
            store_id=store.id,
            shopify_order_id="#3452",
            customer_id=customer.id,
            status="in_transit",
            tracking_number="TRACK12345",
            shipping_address={"city": "San Francisco", "country": "US"},
            raw_order={"line_items": [{"title": "Gentle Foaming Cleanser", "quantity": 1}]},
        )
    )

    for doc_data in DEMO_DOCUMENTS:
        document = Document(
            store_id=store.id,
            filename=doc_data["filename"],
            content_type=doc_data["content_type"],
            status="processed",
            raw_text=doc_data["raw_text"],
        )
        db.add(document)
        db.flush()

        chunks = chunk_text(doc_data["raw_text"])
        embeddings = generate_embeddings(chunks)
        for index, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            db.add(
                EmbeddingRecord(
                    store_id=store.id,
                    document_id=document.id,
                    chunk_text=chunk,
                    vector=vector,
                    meta={"source": doc_data["filename"], "chunk_index": index},
                )
            )

    conversation = Conversation(
        store_id=store.id,
        customer_name="Ava",
        status="open",
        meta={"title": "Welcome chat", "source": "seed"},
    )
    db.add(conversation)
    db.flush()

    db.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=(
                "Hi! I'm your Glow Beauty skincare advisor. I can help with product recommendations, "
                "ingredient questions, shipping, returns, and order status. What can I help you with today?"
            ),
            meta={"agent": "greeting"},
        )
    )

    db.commit()


def ensure_product_indexes(db: Session) -> None:
    stores = db.query(Store).all()
    for store in stores:
        index_product_embeddings(db, store.id)
    db.commit()


def ensure_minimum_store(db: Session) -> None:
    """Seed demo catalog when database is empty (e.g. fresh Render deploy)."""
    if db.query(Store).first() is None:
        seed_demo_data(db)

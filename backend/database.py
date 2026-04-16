import sqlite3
import os
import json
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "ecommerce.db"))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL CHECK(price > 0),
            category TEXT NOT NULL,
            image_url TEXT DEFAULT '',
            stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
            options TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1 CHECK(quantity > 0),
            selected_options TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (product_id) REFERENCES products(id),
            UNIQUE(session_id, product_id, selected_options)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            shipping_address TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            selected_options TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


def seed_products():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    def opts(o): return json.dumps(o)

    SIZE_COLOR_CLOTHES = [
        {"name": "Size", "values": ["XS", "S", "M", "L", "XL", "XXL"]},
        {"name": "Color", "values": ["Black", "White", "Navy", "Gray", "Burgundy"]},
    ]
    SHOE_OPTS = [
        {"name": "Size", "values": ["UK 6", "UK 7", "UK 8", "UK 9", "UK 10", "UK 11", "UK 12"]},
        {"name": "Color", "values": ["Black/White", "All White", "Navy/Red", "Gray/Lime"]},
    ]

    products = [
        # ── Clothing ──────────────────────────────────────────────────────
        ("Organic Cotton T-Shirt",
         "Ultra-soft 200gsm 100% GOTS-certified organic cotton tee. Pre-shrunk, reinforced collar, side-seamed for a tailored fit. Sustainably dyed, ethically made.",
         24.99, "Clothing", "👕", 300, opts(SIZE_COLOR_CLOTHES)),

        ("Premium Hoodie Sweatshirt",
         "Heavyweight 380gsm fleece-lined hoodie with kangaroo pocket, adjustable drawcord, and ribbed cuffs. Brushed interior for exceptional warmth.",
         59.99, "Clothing", "🧥", 150, opts(SIZE_COLOR_CLOTHES)),

        ("Classic Denim Jeans",
         "Straight-cut 12oz selvedge denim with stretch comfort waistband. Five-pocket styling, double-stitched seams, and antique brass hardware.",
         69.99, "Clothing", "👖", 200,
         opts([{"name": "Waist", "values": ["28", "30", "32", "34", "36", "38"]},
               {"name": "Wash", "values": ["Light Wash", "Mid Wash", "Dark Wash", "Black"]}])),

        ("Linen Button-Down Shirt",
         "Lightweight summer linen shirt with mother-of-pearl buttons. Breathable open weave, relaxed fit, single chest pocket. Perfect for warm weather.",
         44.99, "Clothing", "👔", 120,
         opts([{"name": "Size", "values": ["XS", "S", "M", "L", "XL", "XXL"]},
               {"name": "Color", "values": ["White", "Sky Blue", "Sage Green", "Sand"]}])),

        ("High-Waist Yoga Leggings",
         "Four-way stretch fabric with moisture-wicking and squat-proof properties. Wide waistband, hidden pocket, flatlock seams. Studio or street ready.",
         42.99, "Clothing", "🩱", 180,
         opts([{"name": "Size", "values": ["XS", "S", "M", "L", "XL"]},
               {"name": "Color", "values": ["Black", "Midnight Navy", "Heather Gray", "Deep Plum"]}])),

        # ── Sports & Fitness ───────────────────────────────────────────────
        ("Running Shoes",
         "Lightweight road-running shoes with responsive foam midsole and breathable engineered mesh upper. Rubber outsole with multidirectional traction.",
         89.99, "Sports", "👟", 120, opts(SHOE_OPTS)),

        ("Trail Running Shoes",
         "Aggressive lugged outsole for off-road grip, protective toe cap, and waterproof membrane. Cushioned landing for technical terrain.",
         109.99, "Sports", "🥾", 90, opts(SHOE_OPTS)),

        ("Yoga Mat",
         "Extra-thick 6mm eco-friendly TPE mat with dual-layer non-slip texture. Closed-cell surface repels sweat. Includes microfibre towel and carry strap.",
         39.99, "Sports", "🧘", 100,
         opts([{"name": "Thickness", "values": ["4mm", "6mm", "8mm"]},
               {"name": "Color", "values": ["Purple", "Teal", "Slate Blue", "Coral", "Black"]}])),

        ("Resistance Bands Set",
         "Set of 5 latex-free resistance bands (5–40 lbs). Door anchor, foam handles, ankle straps, and carry bag included. Full-body workout anywhere.",
         27.99, "Sports", "💪", 200,
         opts([{"name": "Pack", "values": ["Starter (5–15 lbs)", "Intermediate (10–25 lbs)", "Pro (15–40 lbs)", "Complete Set"]}])),

        ("Sports Water Bottle",
         "Insulated stainless steel sports bottle. Keeps cold 24h, hot 12h. Leak-proof flip lid, carry loop, BPA-free. Fits most cup holders.",
         24.99, "Sports", "🥤", 250,
         opts([{"name": "Size", "values": ["500ml", "750ml", "1 Litre"]},
               {"name": "Color", "values": ["Midnight Black", "Ocean Blue", "Forest Green", "Coral", "White"]}])),

        # ── Bags & Accessories ─────────────────────────────────────────────
        ("Laptop Backpack",
         "Water-resistant 600D polyester backpack with padded 15.6\" laptop sleeve, anti-theft back pocket, USB-A charging pass-through, and breathable back panel.",
         54.99, "Bags", "🎒", 110,
         opts([{"name": "Size", "values": ["13\" (22L)", "15.6\" (30L)", "17\" (38L)"]},
               {"name": "Color", "values": ["Charcoal Black", "Navy Blue", "Slate Gray"]}])),

        ("Leather Tote Bag",
         "Full-grain vegetable-tanned leather tote. Reinforced stitching, magnetic snap closure, interior zip pocket, and cross-body strap included.",
         129.99, "Bags", "👜", 60,
         opts([{"name": "Size", "values": ["Small (30cm)", "Medium (38cm)", "Large (45cm)"]},
               {"name": "Color", "values": ["Black", "Cognac Brown", "Tan", "Burgundy"]}])),

        ("Canvas Crossbody Bag",
         "Waxed canvas crossbody with antique brass hardware, adjustable webbing strap, and YKK zip. Three external pockets. Compact yet spacious.",
         49.99, "Bags", "👝", 80,
         opts([{"name": "Size", "values": ["Mini (18cm)", "Regular (24cm)", "Large (30cm)"]},
               {"name": "Color", "values": ["Natural Canvas", "Olive", "Black", "Rust"]}])),

        ("Travel Duffel Bag",
         "Military-grade 1000D Cordura duffel with lockable zips, removable shoulder strap, shoe compartment, and grab handles. TSA carry-on compliant.",
         89.99, "Bags", "🧳", 70,
         opts([{"name": "Capacity", "values": ["40L (Weekend)", "60L (Week)", "80L (Expedition)"]},
               {"name": "Color", "values": ["Black", "Olive Drab", "Navy"]}])),

        # ── Electronics ───────────────────────────────────────────────────
        ("Wireless Bluetooth Headphones",
         "ANC headphones with 40mm custom drivers, 30-hour battery, multipoint pairing, and foldable design. Premium leatherette ear cups for all-day comfort.",
         79.99, "Electronics", "🎧", 60,
         opts([{"name": "Color", "values": ["Midnight Black", "Pearl White", "Rose Gold"]}])),

        ("Mechanical Keyboard",
         "TKL layout with hot-swap sockets, per-key RGB, gasket-mount for typing feel, and braided USB-C cable. South-facing LEDs eliminate shine-through.",
         129.99, "Electronics", "⌨️", 75,
         opts([{"name": "Switch", "values": ["Cherry MX Red (Linear)", "Cherry MX Brown (Tactile)", "Cherry MX Blue (Clicky)", "Silent Red"]},
               {"name": "Color", "values": ["Space Gray", "Arctic White"]}])),

        ("Smart Watch",
         "1.4\" AMOLED always-on display, GPS, heart-rate, SpO2, sleep tracking, 7-day battery. 5ATM water-resistant. iOS & Android compatible.",
         149.99, "Electronics", "⌚", 50,
         opts([{"name": "Case Size", "values": ["41mm", "45mm"]},
               {"name": "Band Color", "values": ["Midnight Black", "Starlight White", "Pacific Blue", "Product Red", "Sand"]}])),

        ("Portable Charger",
         "Fast-charge power bank with 65W USB-C PD, dual USB-A, and simultaneous 3-device charging. Compact matte finish with LED charge indicator.",
         44.99, "Electronics", "🔋", 130,
         opts([{"name": "Capacity", "values": ["10,000mAh", "20,000mAh", "30,000mAh"]},
               {"name": "Color", "values": ["Matte Black", "Slate Gray", "Midnight Blue"]}])),

        ("Wireless Mouse",
         "Ergonomic wireless mouse with silent Omron switches, 4000 DPI optical sensor, and dual-mode USB/Bluetooth. 60-day battery life.",
         34.99, "Electronics", "🖱️", 95,
         opts([{"name": "Color", "values": ["Graphite Black", "Pearl White", "Rose Blush"]},
               {"name": "Hand", "values": ["Right-handed", "Ambidextrous"]}])),

        ("Bluetooth Speaker",
         "360° surround sound with dual passive radiators. IP67 waterproof, 20-hour battery, speakerphone, and USB-C charging. Floats in water.",
         59.99, "Electronics", "🔊", 85,
         opts([{"name": "Size", "values": ["Mini (10W)", "Standard (20W)", "Max (40W)"]},
               {"name": "Color", "values": ["Black", "Blue", "Teal", "Red"]}])),

        # ── Home & Kitchen ─────────────────────────────────────────────────
        ("Ceramic Coffee Mug Set",
         "Set of 4 handthrown stoneware mugs with reactive glaze finish. 12oz capacity, dishwasher safe, microwave safe. Each piece unique.",
         39.99, "Home & Kitchen", "☕", 65,
         opts([{"name": "Style", "values": ["Classic Latte", "Rustic Earth", "Coastal Blue", "Monochrome"]},
               {"name": "Set Size", "values": ["Set of 2", "Set of 4", "Set of 6"]}])),

        ("Stainless Steel Water Bottle",
         "Triple-wall vacuum insulated 18/8 stainless steel bottle. Keeps cold 48h, hot 24h. Powder-coated finish, leak-proof cap, dishwasher safe.",
         29.99, "Home & Kitchen", "🍶", 180,
         opts([{"name": "Size", "values": ["500ml", "750ml", "1 Litre"]},
               {"name": "Color", "values": ["Midnight Black", "Matte White", "Sage Green", "Terracotta", "Slate Blue"]}])),

        ("Bamboo Cutting Board Set",
         "3-piece organic bamboo board set (S/M/L). Juice grooves, non-slip feet, easy-grip handles. Naturally antimicrobial. Oiled finish ready to use.",
         34.99, "Home & Kitchen", "🍽️", 75,
         opts([{"name": "Set", "values": ["Small Only", "Medium Only", "Large Only", "3-Piece Set"]},
               {"name": "Finish", "values": ["Natural", "Deep Oiled"]}])),

        ("Scented Soy Candle",
         "Hand-poured 100% natural soy wax candle with cotton wick. Up to 60-hour burn time. Fragrance-oil free, phthalate-free.",
         22.99, "Home & Kitchen", "🕯️", 140,
         opts([{"name": "Scent", "values": ["Lavender & Eucalyptus", "Sandalwood & Cedar", "Vanilla & Amber", "Citrus & Basil", "Sea Salt & Sage"]},
               {"name": "Size", "values": ["4oz (20hrs)", "8oz (40hrs)", "16oz (60hrs)"]}])),

        ("Throw Pillow Cover",
         "Stonewashed linen-cotton blend pillow cover with invisible zip. Pre-washed for softness. Sold as cover only; insert sold separately.",
         18.99, "Home & Kitchen", "🛋️", 200,
         opts([{"name": "Size", "values": ["45×45cm", "50×50cm", "55×55cm", "60×40cm (Lumbar)"]},
               {"name": "Color", "values": ["Natural Linen", "Dusty Rose", "Sage Green", "Slate Blue", "Charcoal"]}])),

        ("Indoor Plant Pot Set",
         "Set of 3 minimalist pots with drainage holes and matching saucers. Frost-resistant ceramic with matte glaze. Suitable for herbs, succulents, and small plants.",
         32.99, "Home & Kitchen", "🪴", 90,
         opts([{"name": "Size", "values": ["3-piece S/M/L", "3-piece M/L/XL"]},
               {"name": "Color", "values": ["Terracotta", "Matte White", "Slate Black", "Sage Green"]}])),

        # ── Wellness ──────────────────────────────────────────────────────
        ("Essential Oil Diffuser",
         "Ultrasonic cool-mist aromatherapy diffuser with 7-colour LED ambient light, auto shut-off, and whisper-quiet operation. BPA-free tank.",
         38.99, "Wellness", "💆", 75,
         opts([{"name": "Capacity", "values": ["100ml (3hrs)", "300ml (8hrs)", "500ml (12hrs)"]},
               {"name": "Color", "values": ["Pure White", "Natural Wood Grain", "Matte Black"]}])),
    ]

    cursor.executemany(
        "INSERT INTO products (name, description, price, category, image_url, stock, options) VALUES (?, ?, ?, ?, ?, ?, ?)",
        products,
    )

    conn.commit()
    conn.close()
    logger.info(f"Seeded {len(products)} products")

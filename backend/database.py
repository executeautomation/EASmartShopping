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
            rating REAL DEFAULT 0.0,
            review_count INTEGER DEFAULT 0,
            specs TEXT DEFAULT '{}',
            manufacturer TEXT DEFAULT '',
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

    # Migration: add new columns to existing databases that predate this schema
    for migration in [
        "ALTER TABLE products ADD COLUMN rating REAL DEFAULT 0.0",
        "ALTER TABLE products ADD COLUMN review_count INTEGER DEFAULT 0",
        "ALTER TABLE products ADD COLUMN specs TEXT DEFAULT '{}'",
        "ALTER TABLE products ADD COLUMN manufacturer TEXT DEFAULT ''",
    ]:
        try:
            cursor.execute(migration)
        except Exception:
            pass  # column already exists
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


def seed_products():
    conn = get_connection()
    cursor = conn.cursor()

    # Re-seed if no products have rating data yet (handles fresh DB and schema upgrades)
    cursor.execute("SELECT COUNT(*) FROM products WHERE review_count > 0")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Clear any existing products that lack rating data so we start clean
    cursor.execute("DELETE FROM products")

    def opts(o): return json.dumps(o)
    def spec(d): return json.dumps(d)

    SIZE_COLOR_CLOTHES = [
        {"name": "Size", "values": ["XS", "S", "M", "L", "XL", "XXL"]},
        {"name": "Color", "values": ["Black", "White", "Navy", "Gray", "Burgundy"]},
    ]
    SHOE_OPTS = [
        {"name": "Size", "values": ["UK 6", "UK 7", "UK 8", "UK 9", "UK 10", "UK 11", "UK 12"]},
        {"name": "Color", "values": ["Black/White", "All White", "Navy/Red", "Gray/Lime"]},
    ]

    # Each tuple: (name, description, price, category, image_url, stock, options,
    #              rating, review_count, specs_json, manufacturer)
    products = [

        # ════════════════════════════════════════════════════════════════
        # CLOTHING
        # ════════════════════════════════════════════════════════════════
        (
            "Organic Cotton T-Shirt",
            "Ultra-soft 200gsm 100% GOTS-certified organic cotton tee. Pre-shrunk, reinforced collar, side-seamed for a tailored fit. Sustainably dyed with low-impact reactive dyes. Ethically made in Portugal. Rated excellent for breathability and all-day comfort. Highly durable — holds shape after 100+ washes with zero pilling.",
            24.99, "Clothing", "👕", 300, opts(SIZE_COLOR_CLOTHES),
            4.5, 1243,
            spec({"fabric": "200gsm GOTS organic cotton", "fit": "Regular", "care": "Machine wash 30°C", "origin": "Portugal", "certification": "GOTS, Fair Wear", "durability": "Holds shape after 100+ washes, zero pilling", "breathability": "Excellent"}),
            "EcoThreads Co.",
        ),
        (
            "Premium Hoodie Sweatshirt",
            "Heavyweight 380gsm fleece-lined hoodie with kangaroo pocket, adjustable drawcord, and ribbed cuffs. Brushed interior for exceptional warmth. Reinforced seams rated for 5+ years of regular wear. Manufacturer: NorthKnit Industries. Customer reviews praise the warmth-to-weight ratio and colour fastness.",
            59.99, "Clothing", "🧥", 150, opts(SIZE_COLOR_CLOTHES),
            4.7, 892,
            spec({"fabric": "380gsm 80% cotton 20% polyester fleece", "lining": "Brushed fleece interior", "pockets": "Kangaroo + 2 side zip", "care": "Machine wash 40°C", "durability": "Rated 5+ years regular wear", "warmth_rating": "High", "origin": "Bangladesh (Fair Trade certified)"}),
            "NorthKnit Industries",
        ),
        (
            "Classic Denim Jeans",
            "Straight-cut 12oz selvedge denim with stretch comfort waistband. Five-pocket styling, double-stitched seams, and antique brass hardware. Made with Cone Mills USA denim — same mill used by premium heritage brands. Exceptionally durable: reinforced at stress points, rated for 3–5 years daily wear.",
            69.99, "Clothing", "👖", 200,
            opts([{"name": "Waist", "values": ["28", "30", "32", "34", "36", "38"]},
                  {"name": "Wash", "values": ["Light Wash", "Mid Wash", "Dark Wash", "Black"]}]),
            4.3, 654,
            spec({"fabric": "12oz selvedge denim, 98% cotton 2% elastane", "hardware": "Antique brass YKK", "denim_mill": "Cone Mills USA", "durability": "Reinforced at belt loops and pocket corners, rated 3–5 years daily wear", "rise": "Mid-rise", "leg": "Straight"}),
            "Heritage Denim Co.",
        ),
        (
            "Linen Button-Down Shirt",
            "Lightweight summer linen shirt with mother-of-pearl buttons. Breathable open weave, relaxed fit, single chest pocket. Stone-washed for instant softness. Made from Belgian linen — the gold standard for fibre quality. Breathability rated 9/10 by testers. Gets softer with every wash.",
            44.99, "Clothing", "👔", 120,
            opts([{"name": "Size", "values": ["XS", "S", "M", "L", "XL", "XXL"]},
                  {"name": "Color", "values": ["White", "Sky Blue", "Sage Green", "Sand"]}]),
            4.4, 421,
            spec({"fabric": "100% Belgian linen", "weight": "Lightweight 135gsm", "buttons": "Mother-of-pearl", "care": "Machine wash 30°C or dry clean", "breathability": "9/10 — excellent for warm climates", "softness": "Improves with each wash"}),
            "Maison Lino",
        ),
        (
            "High-Waist Yoga Leggings",
            "Four-way stretch 78% nylon 22% spandex fabric with moisture-wicking and squat-proof properties. Wide waistband, hidden pocket, flatlock seams. UPF 50+ sun protection. Customer favourite — rated #1 legging for comfort and squat-proof guarantee. Manufacturer: FlexForm Athletic. Durable up to 200 wash cycles.",
            42.99, "Clothing", "🩱", 180,
            opts([{"name": "Size", "values": ["XS", "S", "M", "L", "XL"]},
                  {"name": "Color", "values": ["Black", "Midnight Navy", "Heather Gray", "Deep Plum"]}]),
            4.8, 2107,
            spec({"fabric": "78% nylon, 22% spandex", "technology": "Moisture-wicking, squat-proof, 4-way stretch", "UPF": "UPF 50+", "pockets": "Hidden waistband pocket", "seams": "Flatlock (no chafing)", "durability": "Rated 200 wash cycles, colour-fast", "compression": "Medium"}),
            "FlexForm Athletic",
        ),
        (
            "Merino Wool Sweater",
            "Fine-knit 18.5 micron Merino wool sweater. Naturally temperature-regulating — warm in winter, cool in summer. Odour-resistant, itch-free, machine washable. Made by PureWool NZ from New Zealand Merino. Rated excellent for travel: resists wrinkles and refreshes overnight. Lasts 10+ years with proper care.",
            89.99, "Clothing", "🧶", 80,
            opts([{"name": "Size", "values": ["XS", "S", "M", "L", "XL", "XXL"]},
                  {"name": "Color", "values": ["Oatmeal", "Charcoal", "Forest Green", "Dusty Rose", "Navy"]}]),
            4.6, 389,
            spec({"fabric": "100% 18.5 micron Merino wool", "origin": "New Zealand Merino, knitted in Italy", "weight": "Midweight 300gsm", "care": "Machine wash wool cycle 30°C", "odour_resistance": "Excellent — natural lanolin", "temperature_regulation": "Warm in winter, cool in summer", "durability": "10+ years with proper care", "itch_free": True}),
            "PureWool NZ",
        ),
        (
            "Waterproof Windbreaker Jacket",
            "Lightweight packable windbreaker with 10,000mm hydrostatic head rating and 8,000g/m² breathability. Taped seams, adjustable hood, pit-zips. Packs into its own chest pocket. Made by StormShield Outdoor. Rated excellent by hikers and cyclists for weight-to-protection ratio.",
            74.99, "Clothing", "🧥", 95,
            opts([{"name": "Size", "values": ["XS", "S", "M", "L", "XL", "XXL"]},
                  {"name": "Color", "values": ["Electric Blue", "Olive", "Black", "Flame Orange"]}]),
            4.5, 567,
            spec({"fabric": "20D nylon ripstop", "waterproofing": "10,000mm hydrostatic head", "breathability": "8,000g/m²/24hrs", "seams": "Fully taped", "packability": "Packs into chest pocket (380g)", "hood": "Adjustable with peak", "vents": "Underarm pit-zips", "warranty": "Lifetime manufacturer warranty"}),
            "StormShield Outdoor",
        ),
        (
            "Compression Running Tights",
            "Graduated compression running tights (15–20 mmHg) for improved circulation and faster recovery. Four-way stretch, moisture-wicking, reflective details for night running. Made by KineticFit. Tested with 50 competitive runners — 92% reported less muscle fatigue. Durable up to 150 wash cycles.",
            54.99, "Clothing", "🏃", 120,
            opts([{"name": "Size", "values": ["XS", "S", "M", "L", "XL"]},
                  {"name": "Length", "values": ["Full Length", "3/4 Length", "Shorts"]}]),
            4.4, 712,
            spec({"compression": "15–20 mmHg graduated", "fabric": "80% nylon 20% spandex", "moisture_wicking": True, "reflective": "360° reflective strips", "pockets": "Rear zip pocket + phone pocket", "durability": "150 wash cycles colour-fast", "clinical_testing": "92% of testers reported reduced muscle fatigue"}),
            "KineticFit",
        ),

        # ════════════════════════════════════════════════════════════════
        # SPORTS & FOOTWEAR
        # ════════════════════════════════════════════════════════════════
        (
            "AeroStride Pro Running Shoes",
            "Lightweight road-running shoes featuring AeroFoam+ responsive midsole (30% more energy return than standard EVA) and breathable engineered mesh upper. Carbon rubber outsole rated for 800km. Manufacturer: PaceForge Athletics. Customer rating 4.6/5 from 1,843 verified runners. Drop: 8mm. Best for: neutral runners, road and treadmill.",
            89.99, "Sports", "👟", 120, opts(SHOE_OPTS),
            4.6, 1843,
            spec({"midsole": "AeroFoam+ (30% more energy return vs standard EVA)", "outsole": "Carbon rubber, rated 800km durability", "upper": "Engineered mesh, seamless construction", "drop": "8mm heel-to-toe", "weight": "265g (UK9)", "waterproof": False, "terrain": "Road, treadmill", "runner_type": "Neutral", "warranty": "12 months manufacturer defects", "stack_height": "36mm heel / 28mm forefoot"}),
            "PaceForge Athletics",
        ),
        (
            "TerraTrek XT Trail Running Shoes",
            "Aggressive 5mm multi-directional lugged outsole for off-road grip on mud, gravel and rock. Protective rock-plate in forefoot, reinforced toe cap, Gore-Tex waterproof membrane. Rated 4.8/5 from 976 trail runners — top pick for durability on technical terrain. Outsole rated 600km off-road. Manufacturer: TerraTrek.",
            109.99, "Sports", "🥾", 90, opts(SHOE_OPTS),
            4.8, 976,
            spec({"midsole": "Dual-density TrailPro foam", "outsole": "5mm multi-directional lugs, Vibram MegaGrip, rated 600km off-road", "upper": "Reinforced TPU overlays + Gore-Tex membrane", "protection": "Rock-plate forefoot, TPU toe cap", "drop": "6mm", "weight": "320g (UK9)", "waterproof": True, "terrain": "Trail, mountain, mud, gravel", "runner_type": "Neutral to mild overpronation", "warranty": "24 months"}),
            "TerraTrek",
        ),
        (
            "ComfortStep Daily Walking Shoes",
            "Everyday walking shoes engineered for all-day comfort with CloudCushion memory foam insole and wide toe-box design. Rated 4.9/5 from 2,187 verified buyers — the highest rated shoe in our entire catalogue. Podiatrist recommended. Slip-resistant outsole. Manufacturer: StepEasy. Ideal for standing jobs, city walking, travel. Lightweight at 220g.",
            79.99, "Sports", "👟", 160,
            opts([{"name": "Size", "values": ["UK 4", "UK 5", "UK 6", "UK 7", "UK 8", "UK 9", "UK 10", "UK 11", "UK 12"]},
                  {"name": "Width", "values": ["Standard (D)", "Wide (2E)", "Extra Wide (4E)"]},
                  {"name": "Color", "values": ["Classic White", "All Black", "Navy/Grey", "Beige/Tan"]}]),
            4.9, 2187,
            spec({"midsole": "CloudCushion memory foam + EVA base", "outsole": "Slip-resistant rubber, rated 1200km walking", "upper": "Breathable knit mesh, seamless", "toe_box": "Wide anatomical shape", "insole": "Removable memory foam, podiatrist-designed", "drop": "6mm", "weight": "220g (UK8)", "waterproof": False, "endorsement": "Podiatrist recommended", "terrain": "Urban, casual, travel", "warranty": "12 months"}),
            "StepEasy",
        ),
        (
            "CourtKing Elite Basketball Shoes",
            "High-top basketball shoes with full-length Zoom Air cushioning, herringbone outsole for multi-directional court grip, and ankle lockdown strap. Carbon fibre torsion shank for lateral support. Manufacturer: CourtKing. Rated 4.4/5 from 654 players. Durable outsole rated for 2 full NBA-length seasons. Non-marking sole.",
            129.99, "Sports", "🏀", 75,
            opts([{"name": "Size", "values": ["UK 6", "UK 7", "UK 8", "UK 9", "UK 10", "UK 11", "UK 12", "UK 13"]},
                  {"name": "Color", "values": ["Black/Gold", "White/Red", "University Blue", "All Black"]}]),
            4.4, 654,
            spec({"midsole": "Full-length Zoom Air unit", "outsole": "Herringbone rubber, non-marking, rated 2 seasons", "upper": "Fuse + mesh hybrid", "support": "Carbon fibre torsion shank, ankle lockdown strap", "height": "High-top", "weight": "410g (UK9)", "terrain": "Indoor and outdoor courts", "warranty": "6 months", "grip": "Multi-directional herringbone pattern"}),
            "CourtKing",
        ),
        (
            "SummitGuard Pro Hiking Boots",
            "Full-grain leather and Cordura nylon hiking boot with GORE-TEX Extended Comfort waterproof lining. Vibram Megagrip sole rated for 1,200km on mixed terrain. Torsion-control midsole, padded ankle cuff. Rated 4.7/5 from 789 hikers. Manufacturer: SummitGuard. Break-in period: minimal (2–3 outings). Last: anatomical wide fit.",
            149.99, "Sports", "🥾", 60,
            opts([{"name": "Size", "values": ["UK 5", "UK 6", "UK 7", "UK 8", "UK 9", "UK 10", "UK 11", "UK 12"]},
                  {"name": "Color", "values": ["Brown/Tan", "Dark Grey/Black", "Olive/Orange"]}]),
            4.7, 789,
            spec({"upper": "Full-grain leather + 500D Cordura nylon", "waterproofing": "GORE-TEX Extended Comfort lining", "outsole": "Vibram Megagrip, rated 1200km mixed terrain", "midsole": "Dual-density EVA with torsion shank", "ankle": "Padded cuff, 6mm lug height", "weight": "680g (UK9, pair)", "drop": "12mm", "terrain": "Hiking, backpacking, scrambling", "break_in": "Minimal — 2-3 outings", "warranty": "24 months manufacturer defects"}),
            "SummitGuard",
        ),
        (
            "FlexForce X3 Cross Training Shoes",
            "Versatile cross-training shoes engineered for weightlifting, HIIT, box jumps, and short runs. Low 4mm drop for squat stability, wide toe-box, rope-climb guard. Breathable Plyoknit upper. Rated 4.5/5 from 1,234 athletes. Manufacturer: FlexForce. Outsole rated 500km gym use. Pivot point heel for lateral drills.",
            99.99, "Sports", "💪", 85,
            opts([{"name": "Size", "values": ["UK 5", "UK 6", "UK 7", "UK 8", "UK 9", "UK 10", "UK 11", "UK 12"]},
                  {"name": "Color", "values": ["Black/Volt", "White/Cyan", "Stealth Grey", "Red/Black"]}]),
            4.5, 1234,
            spec({"midsole": "Dual-compound — firm heel for lifting, cushioned forefoot for cardio", "outsole": "Multi-surface rubber, pivot point heel, rope-climb guard", "upper": "Plyoknit breathable mesh", "drop": "4mm", "weight": "295g (UK9)", "toe_box": "Wide anatomical", "best_for": "Weightlifting, HIIT, CrossFit, short runs", "waterproof": False, "warranty": "12 months"}),
            "FlexForce",
        ),
        (
            "SpeedClip Carbon Cycling Shoes",
            "Stiff carbon fibre sole cycling shoes (9/10 stiffness index) for road cycling and indoor training. Compatible with 3-bolt SPD-SL and Look KEO cleats. Micro-adjust BOA dial closure for precise fit. Rated 4.3/5 from 445 cyclists. Manufacturer: VeloCarbon. Aerodynamic vented upper. Weight: 240g/shoe.",
            139.99, "Sports", "🚴", 45,
            opts([{"name": "Size", "values": ["EU 38", "EU 39", "EU 40", "EU 41", "EU 42", "EU 43", "EU 44", "EU 45", "EU 46"]},
                  {"name": "Color", "values": ["Gloss White", "Matte Black", "Team Blue"]}]),
            4.3, 445,
            spec({"sole": "Unidirectional carbon fibre, stiffness index 9/10", "closure": "BOA L6 micro-adjust dial", "cleat_compatibility": "3-bolt SPD-SL, Look KEO", "upper": "Microfibre + aero mesh vents", "weight": "240g per shoe (EU42)", "stack_height": "8mm", "best_for": "Road cycling, indoor training, sportive", "warranty": "24 months"}),
            "VeloCarbon",
        ),
        (
            "Yoga Mat",
            "Extra-thick eco-friendly TPE mat with dual-layer non-slip texture and alignment guide lines. Closed-cell surface repels sweat and bacteria. Includes microfibre towel and carry strap. Manufacturer: ZenBase. Rated 4.7/5 from 1,543 yogis. Odour-free, free of PVC, latex, and phthalates. Durable: rated 5 years regular use.",
            39.99, "Sports", "🧘", 100,
            opts([{"name": "Thickness", "values": ["4mm", "6mm", "8mm"]},
                  {"name": "Color", "values": ["Purple", "Teal", "Slate Blue", "Coral", "Black"]}]),
            4.7, 1543,
            spec({"material": "Eco-TPE (PVC/latex/phthalate-free)", "texture": "Dual-layer non-slip", "alignment": "Printed guide lines", "extras": "Microfibre towel + carry strap", "care": "Wipe with damp cloth or hand wash", "durability": "Rated 5 years regular use", "certifications": "REACH, RoHS, SGS tested"}),
            "ZenBase",
        ),
        (
            "Resistance Bands Set",
            "Set of 5 latex-free TPE resistance bands (5–40 lbs). Door anchor, foam handles, ankle straps, and carry bag included. Full-body workout anywhere. Manufacturer: PowerBand. Rated 4.5/5 from 2,341 users. Each band tested to 10,000 stretch cycles. Snap-resistant layered construction.",
            27.99, "Sports", "💪", 200,
            opts([{"name": "Pack", "values": ["Starter (5–15 lbs)", "Intermediate (10–25 lbs)", "Pro (15–40 lbs)", "Complete Set"]}]),
            4.5, 2341,
            spec({"material": "Latex-free TPE layered construction", "resistance_range": "5 lbs, 10 lbs, 15 lbs, 25 lbs, 40 lbs", "tested_to": "10,000 stretch cycles per band", "accessories": "Door anchor, foam handles, ankle straps, carry bag", "snap_resistance": "Layered tube construction", "certifications": "SGS latex-free certified"}),
            "PowerBand",
        ),
        (
            "Sports Water Bottle",
            "Insulated double-wall stainless steel sports bottle. Keeps cold 24h, hot 12h. Leak-proof flip lid with carry loop. BPA/BPS-free. Manufacturer: HydroCore. Rated 4.6/5 from 3,210 athletes. Scratch-resistant powder coat. Fits all standard cup holders. Dishwasher safe lid.",
            24.99, "Sports", "🥤", 250,
            opts([{"name": "Size", "values": ["500ml", "750ml", "1 Litre"]},
                  {"name": "Color", "values": ["Midnight Black", "Ocean Blue", "Forest Green", "Coral", "White"]}]),
            4.6, 3210,
            spec({"material": "18/8 food-grade stainless steel", "insulation": "Double-wall vacuum, cold 24h hot 12h", "lid": "Leak-proof flip lid, dishwasher safe", "coating": "Scratch-resistant powder coat", "certifications": "BPA/BPS-free, FDA approved", "width": "Fits standard cup holders"}),
            "HydroCore",
        ),

        # ════════════════════════════════════════════════════════════════
        # BAGS
        # ════════════════════════════════════════════════════════════════
        (
            "Laptop Backpack",
            "Water-resistant 600D polyester backpack with padded 15.6\" laptop sleeve, anti-theft hidden back pocket, USB-A charging pass-through, and ventilated back panel. Manufacturer: PackPro. Rated 4.5/5 from 1,876 users. YKK zips throughout. Luggage pass-through sleeve. Lifetime warranty on zips and seams.",
            54.99, "Bags", "🎒", 110,
            opts([{"name": "Size", "values": ["13\" (22L)", "15.6\" (30L)", "17\" (38L)"]},
                  {"name": "Color", "values": ["Charcoal Black", "Navy Blue", "Slate Gray"]}]),
            4.5, 1876,
            spec({"material": "600D water-resistant polyester", "laptop_sleeve": "Padded, up to 15.6\"", "pockets": "Anti-theft hidden back, 3 front organiser, side bottle pockets", "pass_through": "USB-A charging pass-through", "back_panel": "Ventilated airflow", "zips": "YKK throughout", "extras": "Luggage trolley sleeve", "warranty": "Lifetime on zips and seams"}),
            "PackPro",
        ),
        (
            "Leather Tote Bag",
            "Full-grain vegetable-tanned leather tote. Reinforced stitching, magnetic snap closure, interior zip pocket, and cross-body strap included. Manufacturer: Artisan & Co., handcrafted in Italy. Rated 4.6/5 from 543 buyers. Ages beautifully — develops natural patina over years. Estimated 10+ year lifespan with conditioning.",
            129.99, "Bags", "👜", 60,
            opts([{"name": "Size", "values": ["Small (30cm)", "Medium (38cm)", "Large (45cm)"]},
                  {"name": "Color", "values": ["Black", "Cognac Brown", "Tan", "Burgundy"]}]),
            4.6, 543,
            spec({"leather": "Full-grain vegetable-tanned cowhide", "hardware": "Solid brass", "lining": "Cotton canvas", "pockets": "Interior zip + 2 open slip", "closure": "Magnetic snap", "strap": "Removable cross-body strap included", "origin": "Handcrafted in Italy", "durability": "10+ years — develops natural patina", "care": "Condition with leather balm every 3–6 months"}),
            "Artisan & Co.",
        ),
        (
            "Canvas Crossbody Bag",
            "Waxed canvas crossbody with antique brass hardware, adjustable webbing strap, and YKK zip. Three external pockets. Compact yet capacious. Manufacturer: Fieldwork Goods. Rated 4.4/5 from 678 buyers. Wax coating is renewable — re-wax every 2 years to maintain water resistance. Robust cotton canvas rated 5+ years.",
            49.99, "Bags", "👝", 80,
            opts([{"name": "Size", "values": ["Mini (18cm)", "Regular (24cm)", "Large (30cm)"]},
                  {"name": "Color", "values": ["Natural Canvas", "Olive", "Black", "Rust"]}]),
            4.4, 678,
            spec({"material": "10oz waxed cotton canvas", "hardware": "Antique solid brass", "zip": "YKK", "pockets": "3 external + 1 internal zip", "strap": "Adjustable 60–120cm webbing", "water_resistance": "Wax coating — re-waxable every 2 years", "durability": "5+ years with re-waxing", "weight": "480g"}),
            "Fieldwork Goods",
        ),
        (
            "Travel Duffel Bag",
            "Military-grade 1000D Cordura nylon duffel with lockable zips, removable padded shoulder strap, waterproof base, and internal shoe compartment. TSA carry-on compliant. Manufacturer: ExpeditionGear. Rated 4.7/5 from 892 travellers. Rated for 500+ flights with airline overhead bins. Lifetime warranty.",
            89.99, "Bags", "🧳", 70,
            opts([{"name": "Capacity", "values": ["40L (Weekend)", "60L (Week)", "80L (Expedition)"]},
                  {"name": "Color", "values": ["Black", "Olive Drab", "Navy"]}]),
            4.7, 892,
            spec({"material": "1000D Cordura nylon", "base": "Waterproof PVC base panel", "zips": "Lockable YKK zips", "pockets": "Shoe compartment + 3 internal organiser pockets", "strap": "Removable padded shoulder strap + grab handles", "tsa": "Carry-on compliant (40L)", "durability": "Rated 500+ flights", "warranty": "Lifetime"}),
            "ExpeditionGear",
        ),
        (
            "Gym Duffle Bag",
            "Dedicated gym bag with ventilated wet/dry shoe pocket, interior laundry bag, and ergonomic padded shoulder strap. Made from 420D ripstop nylon. Manufacturer: IronGrip. Rated 4.3/5 from 1,123 gym-goers. Quick-access water bottle sleeve. Anti-odour lining. Perfect for daily gym use.",
            44.99, "Bags", "🏋️", 95,
            opts([{"name": "Size", "values": ["30L (Daily)", "45L (Heavy Training)"]},
                  {"name": "Color", "values": ["All Black", "Charcoal/Red", "Navy/White"]}]),
            4.3, 1123,
            spec({"material": "420D ripstop nylon", "shoe_pocket": "Ventilated wet/dry compartment", "lining": "Anti-odour treated", "extras": "Interior laundry bag, side water bottle sleeve", "strap": "Padded ergonomic shoulder strap + handles", "volume": "30L or 45L", "weight": "600g (30L)"}),
            "IronGrip",
        ),

        # ════════════════════════════════════════════════════════════════
        # ELECTRONICS
        # ════════════════════════════════════════════════════════════════
        (
            "Wireless Bluetooth Headphones",
            "Active Noise Cancelling headphones with 40mm custom-tuned drivers, 30-hour battery, multipoint pairing (2 devices), and foldable design. Premium memory-foam leatherette ear cups. Manufacturer: SoundCraft. Rated 4.5/5 from 3,421 users. ANC rated class-leading at 35dB attenuation. Hi-Res Audio certified. 2-year warranty.",
            79.99, "Electronics", "🎧", 60,
            opts([{"name": "Color", "values": ["Midnight Black", "Pearl White", "Rose Gold"]}]),
            4.5, 3421,
            spec({"drivers": "40mm custom neodymium", "anc": "Hybrid ANC, 35dB attenuation", "battery": "30 hrs ANC on / 40 hrs ANC off", "charging": "USB-C, 10 min = 3 hrs", "connectivity": "Bluetooth 5.3, multipoint 2 devices", "audio_certified": "Hi-Res Audio, AAC/aptX/LDAC", "weight": "250g", "foldable": True, "warranty": "24 months", "microphone": "4-mic array, cVc 8.0 noise cancelling"}),
            "SoundCraft",
        ),
        (
            "Mechanical Keyboard",
            "TKL (87-key) layout with hot-swap PCB sockets, per-key RGB backlight, gasket-mount isolation for soft typing feel, and braided USB-C detachable cable. South-facing LEDs. Manufacturer: KeyLab. Rated 4.7/5 from 1,234 users. Aluminium top frame. PBT double-shot keycaps — legends last forever.",
            129.99, "Electronics", "⌨️", 75,
            opts([{"name": "Switch", "values": ["Cherry MX Red (Linear)", "Cherry MX Brown (Tactile)", "Cherry MX Blue (Clicky)", "Silent Red"]},
                  {"name": "Color", "values": ["Space Gray", "Arctic White"]}]),
            4.7, 1234,
            spec({"layout": "TKL 87-key", "mount": "Gasket-mount (reduced vibration)", "pcb": "Hot-swap socket (5-pin compatible)", "keycaps": "PBT double-shot, legends never fade", "backlight": "Per-key RGB, south-facing", "frame": "Aluminium top + polycarbonate bottom", "cable": "Detachable 1.8m braided USB-C", "actuation": "Switch dependent (2.0mm Cherry / 4.0mm total travel)", "warranty": "12 months PCB, 6 months switches"}),
            "KeyLab",
        ),
        (
            "Smart Watch",
            "1.4\" AMOLED always-on display, built-in GPS + GLONASS, optical heart-rate + SpO2 sensor, sleep tracking, stress monitoring, 7-day battery. 5ATM water-resistant. iOS & Android. Manufacturer: ChronoTech. Rated 4.4/5 from 2,187 users. Over 100 workout modes. ECG app included.",
            149.99, "Electronics", "⌚", 50,
            opts([{"name": "Case Size", "values": ["41mm", "45mm"]},
                  {"name": "Band Color", "values": ["Midnight Black", "Starlight White", "Pacific Blue", "Product Red", "Sand"]}]),
            4.4, 2187,
            spec({"display": "1.4\" AMOLED, 454×454px, always-on", "sensors": "GPS/GLONASS, HR, SpO2, ECG, barometer, accelerometer", "battery": "7 days typical, 14 days basic mode", "water_resistance": "5ATM (50m)", "workout_modes": "100+", "connectivity": "Bluetooth 5.0, NFC payments", "compatibility": "iOS 12+ / Android 6+", "warranty": "12 months"}),
            "ChronoTech",
        ),
        (
            "Portable Charger",
            "Fast-charge power bank with 65W GaN USB-C PD output, dual USB-A 18W QC3.0, simultaneous 3-device charging. Compact matte finish with LED fuel gauge. Manufacturer: ChargePro. Rated 4.6/5 from 4,521 users. TSA airline approved (all capacities). Charges a 13\" MacBook from 0–100% in under 90 mins.",
            44.99, "Electronics", "🔋", 130,
            opts([{"name": "Capacity", "values": ["10,000mAh", "20,000mAh", "30,000mAh"]},
                  {"name": "Color", "values": ["Matte Black", "Slate Gray", "Midnight Blue"]}]),
            4.6, 4521,
            spec({"usb_c_output": "65W GaN USB-C PD", "usb_a_output": "18W QC3.0 x2", "simultaneous": "3 devices at once", "indicator": "LED fuel gauge (4-level)", "tsa": "Approved for carry-on all sizes", "charging_speed": "0-100% MacBook 13\" in 90 mins", "safety": "UL certified, over-voltage/temperature protection", "warranty": "18 months"}),
            "ChargePro",
        ),
        (
            "Wireless Mouse",
            "Ergonomic wireless mouse with silent Omron switches rated 10 million clicks, 4000 DPI optical sensor, dual-mode 2.4GHz USB + Bluetooth 5.0. 60-day battery life. Manufacturer: ClickMaster. Rated 4.5/5 from 2,876 users. Sculpted right-hand ergonomic grip reduces wrist strain. Works on all surfaces including glass.",
            34.99, "Electronics", "🖱️", 95,
            opts([{"name": "Color", "values": ["Graphite Black", "Pearl White", "Rose Blush"]},
                  {"name": "Hand", "values": ["Right-handed", "Ambidextrous"]}]),
            4.5, 2876,
            spec({"sensor": "4000 DPI optical, works on glass", "switches": "Silent Omron rated 10M clicks", "connectivity": "2.4GHz USB dongle + Bluetooth 5.0", "battery": "2× AA, 60-day life", "ergonomics": "Sculpted grip, reduces wrist strain", "dpi_steps": "400 / 800 / 1600 / 4000 DPI", "weight": "101g", "warranty": "12 months"}),
            "ClickMaster",
        ),
        (
            "Bluetooth Speaker",
            "360° surround sound with dual passive radiators and 2-tweeter + 1-woofer setup. IP67 waterproof and dustproof, floats in water, 20-hour battery, USB-C charging, built-in speakerphone. Manufacturer: BassField. Rated 4.6/5 from 1,987 users. TWS pairing — link 2 speakers for stereo. Drop-proof from 1.5m.",
            59.99, "Electronics", "🔊", 85,
            opts([{"name": "Size", "values": ["Mini (10W)", "Standard (20W)", "Max (40W)"]},
                  {"name": "Color", "values": ["Black", "Blue", "Teal", "Red"]}]),
            4.6, 1987,
            spec({"drivers": "2 tweeters + 1 subwoofer + 2 passive radiators", "waterproof": "IP67 — floats in water", "battery": "20 hours at 50% volume", "charging": "USB-C, 3hr full charge", "connectivity": "Bluetooth 5.1, TWS stereo pairing", "speakerphone": True, "drop_proof": "1.5m", "warranty": "12 months"}),
            "BassField",
        ),
        (
            "True Wireless Earbuds",
            "True wireless earbuds with 10mm graphene drivers for Hi-Res audio, hybrid ANC (28dB), 8hrs + 32hrs case battery, IPX5 sweat resistant, Bluetooth 5.3 multipoint. Manufacturer: SoundPods. Rated 4.8/5 from 5,632 users — highest rated electronics in our catalogue. Transparency mode, wear detection, wireless charging case.",
            69.99, "Electronics", "🎵", 110,
            opts([{"name": "Color", "values": ["Gloss White", "Matte Black", "Sage Green", "Lavender"]}]),
            4.8, 5632,
            spec({"drivers": "10mm graphene dynamic drivers", "anc": "Hybrid ANC, 28dB attenuation", "battery": "8hrs buds + 32hrs case (ANC on)", "case_charging": "Wireless Qi + USB-C", "water_resistance": "IPX5 sweat resistant", "connectivity": "Bluetooth 5.3, multipoint 2 devices", "features": "Transparency mode, wear detection, EQ app", "codec": "AAC, SBC, aptX Adaptive", "warranty": "12 months"}),
            "SoundPods",
        ),
        (
            "Ergonomic Laptop Stand",
            "Adjustable aluminium laptop stand with 6 height levels (11–22cm) and 360° rotation. Fits laptops 10–17\". Ventilated base prevents overheating. Foldable for travel. Manufacturer: DeskPro. Rated 4.7/5 from 987 users. Anti-slip pads on all feet and saddle. Tested to hold 10kg. Pairs perfectly with an external keyboard and mouse.",
            34.99, "Electronics", "💻", 140,
            opts([{"name": "Color", "values": ["Space Grey", "Silver", "Matte Black"]}]),
            4.7, 987,
            spec({"material": "Aircraft-grade aluminium 6061", "height_range": "11–22cm, 6 levels", "rotation": "360°", "laptop_fit": "10–17\" laptops", "max_load": "10kg tested", "weight": "580g", "foldable": True, "anti_slip": "Silicone pads on feet and saddle", "ventilation": "Open lattice base", "warranty": "24 months"}),
            "DeskPro",
        ),

        # ════════════════════════════════════════════════════════════════
        # HOME & KITCHEN
        # ════════════════════════════════════════════════════════════════
        (
            "Ceramic Coffee Mug Set",
            "Set of handthrown stoneware mugs with reactive glaze finish. 12oz capacity, dishwasher safe, microwave safe, oven safe to 200°C. Each piece unique. Manufacturer: Clayworks Studio. Rated 4.6/5 from 876 buyers. Lead-free and cadmium-free glazes certified. Chip-resistant rim. Made in Portugal.",
            39.99, "Home & Kitchen", "☕", 65,
            opts([{"name": "Style", "values": ["Classic Latte", "Rustic Earth", "Coastal Blue", "Monochrome"]},
                  {"name": "Set Size", "values": ["Set of 2", "Set of 4", "Set of 6"]}]),
            4.6, 876,
            spec({"material": "High-fired stoneware ceramic", "capacity": "12oz (350ml)", "glaze": "Reactive glaze — each piece unique", "safe": "Dishwasher, microwave, oven to 200°C", "certifications": "Lead-free and cadmium-free (FDA/EU compliant)", "origin": "Handthrown in Portugal", "chip_resistance": "Reinforced rim"}),
            "Clayworks Studio",
        ),
        (
            "Stainless Steel Water Bottle",
            "Triple-wall vacuum insulated 18/8 stainless steel bottle. Keeps cold 48h, hot 24h. Powder-coated finish, leak-proof twist cap, dishwasher-safe lid. Manufacturer: PureVessel. Rated 4.5/5 from 2,341 users. BPA/BPS-free. Scratch-resistant. Never sweats on outside. Wide-mouth version fits standard ice cubes.",
            29.99, "Home & Kitchen", "🍶", 180,
            opts([{"name": "Size", "values": ["500ml", "750ml", "1 Litre"]},
                  {"name": "Color", "values": ["Midnight Black", "Matte White", "Sage Green", "Terracotta", "Slate Blue"]}]),
            4.5, 2341,
            spec({"material": "18/8 food-grade stainless steel", "insulation": "Triple-wall vacuum, cold 48h hot 24h", "coating": "Scratch-resistant powder coat", "lid": "Leak-proof twist cap, dishwasher safe", "certifications": "BPA/BPS-free, FDA approved", "mouth": "Wide-mouth, fits standard ice cubes", "condensation": "None — never sweats"}),
            "PureVessel",
        ),
        (
            "Bamboo Cutting Board Set",
            "3-piece organic bamboo board set (S/M/L). Juice grooves, non-slip silicone feet, easy-grip side handles. Naturally antimicrobial without chemical treatment. Manufacturer: GreenChop. Rated 4.7/5 from 654 buyers. FSC-certified sustainable bamboo. Oiled finish ready to use. Harder than maple yet gentle on knives.",
            34.99, "Home & Kitchen", "🍽️", 75,
            opts([{"name": "Set", "values": ["Small Only", "Medium Only", "Large Only", "3-Piece Set"]},
                  {"name": "Finish", "values": ["Natural", "Deep Oiled"]}]),
            4.7, 654,
            spec({"material": "Moso bamboo (FSC certified)", "antimicrobial": "Natural — no chemical treatment needed", "features": "Juice grooves, non-slip silicone feet, side handles", "hardness": "Harder than maple, gentle on knife edges", "care": "Hand wash + re-oil every 2–3 months", "sizes": "Small 25×18cm, Medium 35×25cm, Large 45×30cm", "certifications": "FSC sustainable bamboo"}),
            "GreenChop",
        ),
        (
            "Scented Soy Candle",
            "Hand-poured 100% natural soy wax candle with unbleached cotton wick. Up to 60-hour burn time. No synthetic fragrance oils — scented with pure essential oils only. Phthalate-free. Manufacturer: WickCraft. Rated 4.5/5 from 1,123 buyers. Clean burn — no soot. Reusable glass jar.",
            22.99, "Home & Kitchen", "🕯️", 140,
            opts([{"name": "Scent", "values": ["Lavender & Eucalyptus", "Sandalwood & Cedar", "Vanilla & Amber", "Citrus & Basil", "Sea Salt & Sage"]},
                  {"name": "Size", "values": ["4oz (20hrs)", "8oz (40hrs)", "16oz (60hrs)"]}]),
            4.5, 1123,
            spec({"wax": "100% natural soy wax", "wick": "Unbleached cotton (no lead/zinc)", "scent": "Pure essential oils only — no synthetic fragrance", "certifications": "Phthalate-free, vegan", "burn_time": "Up to 60 hours (16oz)", "soot": "Clean burn — zero soot", "vessel": "Reusable borosilicate glass jar", "made_in": "Handpoured in small batches, UK"}),
            "WickCraft",
        ),
        (
            "Throw Pillow Cover",
            "Stonewashed linen-cotton blend pillow cover with invisible zip. Pre-washed for instant softness. Sold as cover only. Manufacturer: HavenTextiles. Rated 4.3/5 from 543 buyers. Machine washable at 40°C. Colour-fast — 50-wash test certified. Gets softer with each wash. GSM: 200.",
            18.99, "Home & Kitchen", "🛋️", 200,
            opts([{"name": "Size", "values": ["45×45cm", "50×50cm", "55×55cm", "60×40cm (Lumbar)"]},
                  {"name": "Color", "values": ["Natural Linen", "Dusty Rose", "Sage Green", "Slate Blue", "Charcoal"]}]),
            4.3, 543,
            spec({"fabric": "55% linen 45% cotton, 200gsm stonewashed", "zip": "Invisible zip", "care": "Machine wash 40°C, colour-fast 50-wash certified", "softness": "Stonewashed — improves with each wash", "insert_sold": "Separately"}),
            "HavenTextiles",
        ),
        (
            "Indoor Plant Pot Set",
            "Set of 3 minimalist pots with drainage holes and matching saucers. Frost-resistant stoneware ceramic with matte reactive glaze. Suitable for herbs, succulents, ferns, and small tropical plants. Manufacturer: TerraForm Studio. Rated 4.4/5 from 432 buyers. Made in Portugal. Lead-free glazes.",
            32.99, "Home & Kitchen", "🪴", 90,
            opts([{"name": "Size", "values": ["3-piece S/M/L", "3-piece M/L/XL"]},
                  {"name": "Color", "values": ["Terracotta", "Matte White", "Slate Black", "Sage Green"]}]),
            4.4, 432,
            spec({"material": "Frost-resistant stoneware ceramic", "drainage": "Drainage holes + matching saucers", "glaze": "Matte reactive — lead-free", "sizes": "S: 8cm, M: 12cm, L: 16cm (or M/L/XL 12/16/20cm)", "suitable_for": "Herbs, succulents, ferns, small tropicals", "origin": "Portugal", "frost_resistant": True}),
            "TerraForm Studio",
        ),

        # ════════════════════════════════════════════════════════════════
        # WELLNESS
        # ════════════════════════════════════════════════════════════════
        (
            "Essential Oil Diffuser",
            "Ultrasonic cool-mist aromatherapy diffuser with 7-colour LED ambient light, 4 timer settings, auto shut-off, and whisper-quiet operation (<25dB). BPA-free tank. Manufacturer: AromaZen. Rated 4.5/5 from 876 users. Ultrasonic technology preserves therapeutic properties of essential oils. Coverage up to 30m².",
            38.99, "Wellness", "💆", 75,
            opts([{"name": "Capacity", "values": ["100ml (3hrs)", "300ml (8hrs)", "500ml (12hrs)"]},
                  {"name": "Color", "values": ["Pure White", "Natural Wood Grain", "Matte Black"]}]),
            4.5, 876,
            spec({"technology": "Ultrasonic (preserves oil therapeutic properties)", "noise": "<25dB whisper-quiet", "led": "7-colour RGB ambient light", "coverage": "Up to 30m²", "timer": "1h, 3h, 6h, continuous", "auto_shutoff": True, "tank": "BPA-free food-grade plastic", "mist_output": "25–35ml/hr", "certifications": "CE, RoHS, FCC"}),
            "AromaZen",
        ),
        (
            "High-Density Foam Roller",
            "Professional-grade EPP high-density foam roller for myofascial release, post-workout recovery, and injury prevention. Manufacturer: RecoverPro. Rated 4.6/5 from 1,543 users — widely used by physiotherapists. Textured surface targets deep muscle tissue. Hollow-core construction: firm yet lightweight. Does not lose shape after 2+ years of daily use.",
            29.99, "Wellness", "🧘", 110,
            opts([{"name": "Length", "values": ["30cm (Travel)", "45cm (Standard)", "90cm (Full Body)"]},
                  {"name": "Density", "values": ["Medium (Blue)", "Firm (Black)", "Extra Firm (Grey)"]}]),
            4.6, 1543,
            spec({"material": "Expanded polypropylene (EPP) — superior to EVA foam", "surface": "Textured grid pattern for deep tissue targeting", "core": "Hollow — firm yet lightweight", "density_options": "Medium, Firm, Extra Firm", "durability": "Retains shape after 2+ years daily use", "use_cases": "Myofascial release, physio, yoga, post-workout recovery", "physiotherapist_recommended": True, "weight": "350g (45cm standard)"}),
            "RecoverPro",
        ),

        # ════════════════════════════════════════════════════════════════
        # ELECTRONICS — PC COMPONENTS & STORAGE
        # ════════════════════════════════════════════════════════════════
        (
            "DDR4 RAM Kit",
            "High-performance DDR4 desktop memory kit with XMP 2.0 profile support for one-click overclocking. Low-profile aluminium heat spreader fits most CPU coolers. Dual-channel ready — buy two kits for maximum bandwidth. Manufacturer: Corsair. Rated 4.7/5 from 3,842 verified builders. Compatible with Intel 10th/11th/12th Gen and AMD Ryzen 3000/5000. Lifetime warranty.",
            49.99, "Electronics", "🖥️", 150,
            opts([
                {"name": "Capacity", "values": ["8GB (1×8GB)", "16GB (2×8GB)", "32GB (2×16GB)", "64GB (2×32GB)"]},
                {"name": "Speed", "values": ["DDR4-2666MHz", "DDR4-3200MHz", "DDR4-3600MHz"]},
            ]),
            4.7, 3842,
            spec({"type": "DDR4 SDRAM", "form_factor": "DIMM (288-pin)", "voltage": "1.35V (XMP) / 1.2V (JEDEC)", "latency": "CL16-20 depending on speed", "xmp_profile": "XMP 2.0 one-click OC", "heat_spreader": "Low-profile aluminium", "compatibility": "Intel LGA1200/1700, AMD AM4 (Ryzen 3000/5000)", "ecc": False, "dual_channel": "Buy two for dual-channel", "warranty": "Lifetime manufacturer warranty"}),
            "Corsair",
        ),
        (
            "DDR5 RAM Kit",
            "Next-gen DDR5 desktop memory with on-die ECC for data integrity, XMP 3.0 and EXPO profiles, and integrated PMIC for cleaner power delivery. Up to 2× the bandwidth of DDR4. Manufacturer: Kingston Fury. Rated 4.6/5 from 1,987 verified builders. Compatible with Intel 12th/13th/14th Gen (LGA1700) and AMD Ryzen 7000 (AM5). Best for AI workloads, gaming, and content creation.",
            89.99, "Electronics", "🖥️", 120,
            opts([
                {"name": "Capacity", "values": ["16GB (2×8GB)", "32GB (2×16GB)", "64GB (2×32GB)", "96GB (2×48GB)"]},
                {"name": "Speed", "values": ["DDR5-4800MHz", "DDR5-5600MHz", "DDR5-6000MHz", "DDR5-6400MHz"]},
            ]),
            4.6, 1987,
            spec({"type": "DDR5 SDRAM", "form_factor": "DIMM (288-pin)", "voltage": "1.1V (JEDEC) / 1.35V (XMP)", "on_die_ecc": True, "xmp_profile": "XMP 3.0 + AMD EXPO", "bandwidth": "Up to 2× DDR4 bandwidth", "pmic": "Integrated PMIC for stable power", "compatibility": "Intel LGA1700 (12th/13th/14th Gen), AMD AM5 (Ryzen 7000)", "best_for": "Gaming, AI workloads, content creation", "warranty": "Lifetime manufacturer warranty"}),
            "Kingston Fury",
        ),
        (
            "NVMe PCIe SSD",
            "High-speed PCIe 4.0 NVMe M.2 solid state drive delivering up to 7,450 MB/s sequential read and 6,900 MB/s sequential write — ideal for OS drives, game libraries, and video editing scratch disks. Dynamic Thermal Guard prevents throttling. Manufacturer: Samsung (990 Pro series). Rated 4.8/5 from 5,231 users. Includes heatsink. 5-year warranty. TBW: up to 1,200TB (2TB).",
            89.99, "Electronics", "💾", 130,
            opts([
                {"name": "Capacity", "values": ["500GB", "1TB", "2TB"]},
                {"name": "Heatsink", "values": ["Without Heatsink", "With Heatsink"]},
            ]),
            4.8, 5231,
            spec({"interface": "PCIe 4.0 x4, NVMe 2.0", "form_factor": "M.2 2280", "seq_read": "7,450 MB/s", "seq_write": "6,900 MB/s", "rand_read_iops": "1,400K IOPS", "rand_write_iops": "1,550K IOPS", "nand": "V-NAND TLC (Samsung)", "dram_cache": True, "thermal_guard": "Dynamic Thermal Guard", "tbw_2tb": "1,200 TB", "warranty": "5 years", "compatibility": "PS5, PC with M.2 PCIe 4.0/3.0 slot"}),
            "Samsung",
        ),
        (
            "SATA SSD",
            "Reliable SATA III 6Gb/s solid state drive — the perfect upgrade from a spinning hard drive. Up to 560 MB/s read and 530 MB/s write. 3D NAND for consistent performance and endurance. Ideal for laptops, desktops, and NAS. Manufacturer: Crucial (MX500 series). Rated 4.7/5 from 8,432 users. Drop-shock resistant. 5-year warranty. TBW: 360TB (1TB).",
            54.99, "Electronics", "💾", 160,
            opts([
                {"name": "Capacity", "values": ["250GB", "500GB", "1TB", "2TB", "4TB"]},
            ]),
            4.7, 8432,
            spec({"interface": "SATA III 6Gb/s", "form_factor": "2.5\" 7mm", "seq_read": "560 MB/s", "seq_write": "530 MB/s", "nand": "3D NAND TLC (Micron)", "dram_cache": True, "shock_resistance": "1,500G/0.5ms", "tbw_1tb": "360 TB", "warranty": "5 years", "compatibility": "Laptops, desktops, NAS, PS4/PS3", "idle_power": "0.075W"}),
            "Crucial",
        ),
        (
            "Hard Disk Drive (HDD)",
            "High-capacity 3.5\" desktop hard drive for bulk storage, NAS arrays, and surveillance systems. 7200 RPM with 256MB cache for fast sustained transfers. CMR (Conventional Magnetic Recording) for full compatibility with RAID and NAS. Manufacturer: Seagate (BarraCuda series). Rated 4.5/5 from 6,123 users. MTBF: 1,000,000 hours. 2-year warranty.",
            44.99, "Electronics", "🖴", 110,
            opts([
                {"name": "Capacity", "values": ["1TB", "2TB", "4TB", "6TB", "8TB"]},
            ]),
            4.5, 6123,
            spec({"interface": "SATA III 6Gb/s", "form_factor": "3.5\"", "rpm": "7200 RPM", "cache": "256MB", "recording": "CMR (Conventional Magnetic Recording)", "mtbf": "1,000,000 hours", "warranty": "2 years", "workload_rate": "180 TB/year", "noise": "20dB idle / 28dB seek", "compatibility": "Desktop, NAS (CMR compatible), RAID"}),
            "Seagate",
        ),
        (
            "80+ Gold Modular PSU",
            "Fully modular ATX power supply with 80 Plus Gold efficiency (90% at 50% load). All-Japanese 105°C capacitors rated for 10-year life. Zero RPM fan mode below 30% load for silent operation. Over-voltage, over-current, over-temperature, and short-circuit protection. Manufacturer: Corsair (RM Series). Rated 4.8/5 from 4,231 PC builders. 10-year warranty. ATX 3.0 compliant (PCIe 5.0 connector included).",
            89.99, "Electronics", "⚡", 95,
            opts([
                {"name": "Wattage", "values": ["550W", "650W", "750W", "850W", "1000W", "1200W"]},
                {"name": "Modular", "values": ["Semi-Modular", "Fully Modular"]},
            ]),
            4.8, 4231,
            spec({"efficiency": "80 Plus Gold (90% at 50% load)", "atx_version": "ATX 3.0 compliant", "pcie_connector": "PCIe 5.0 (600W) included", "capacitors": "All-Japanese 105°C rated", "fan_mode": "Zero RPM below 30% load", "protections": "OVP, OCP, OTP, SCP, UVP", "modular": "Fully or Semi-Modular options", "warranty": "10 years", "rails": "Single +12V rail", "certifications": "80+ Gold, UL, CE, TÜV"}),
            "Corsair",
        ),
        (
            "High-Capacity Power Bank",
            "Laptop-grade power bank with 140W USB-C bidirectional charging — fast enough to charge a MacBook Pro or gaming laptop. 20,000mAh capacity charges a phone 5× and a laptop once. Dual USB-C PD + USB-A QC3.0. Smart power allocation automatically splits output. Manufacturer: Anker (737 series). Rated 4.7/5 from 3,109 users. TSA approved. 18-month warranty.",
            79.99, "Electronics", "🔋", 80,
            opts([
                {"name": "Capacity", "values": ["20,000mAh", "26,800mAh", "40,000mAh"]},
                {"name": "Color", "values": ["Black", "Dark Blue"]},
            ]),
            4.7, 3109,
            spec({"capacity": "20,000 / 26,800 / 40,000mAh", "usb_c_output": "140W USB-C PD (bidirectional)", "usb_a_output": "18W QC3.0 x1", "simultaneous": "3 devices at once", "phone_charges": "5× phone charges (20,000mAh)", "laptop_compatible": True, "display": "Digital LED power indicator", "tsa": "TSA carry-on approved (20,000mAh)", "weight": "449g (20,000mAh)", "warranty": "18 months", "certifications": "CE, FCC, RoHS"}),
            "Anker",
        ),
        (
            "Intel ATX Motherboard",
            "ATX form-factor motherboard for Intel 12th/13th/14th Gen processors (LGA1700 socket). Supports DDR5 up to 7200MHz OC, PCIe 5.0 x16 for GPU, dual M.2 PCIe 4.0 slots, 2.5GbE LAN, Wi-Fi 6E, and USB 3.2 Gen 2×2 (20Gbps). VRM: 16+1 phase 90A for stable overclocking. Manufacturer: ASUS (PRIME Z790-P). Rated 4.7/5 from 1,892 builders. AURA Sync RGB. 3-year warranty.",
            189.99, "Electronics", "🖥️", 60,
            opts([
                {"name": "Chipset", "values": ["Intel Z790 (OC Support)", "Intel B760 (Standard)"]},
                {"name": "Form Factor", "values": ["ATX (30.5×24.4cm)", "mATX (24.4×24.4cm)"]},
            ]),
            4.7, 1892,
            spec({"socket": "Intel LGA1700", "cpu_support": "Intel 12th / 13th / 14th Gen (Alder/Raptor Lake)", "memory_type": "DDR5, 4 slots, up to 192GB, 7200MHz OC", "pcie_slots": "PCIe 5.0 x16 (GPU) + PCIe 3.0 x1 ×2", "m2_slots": "2× M.2 PCIe 4.0 (up to 80mm)", "usb": "USB 3.2 Gen 2×2 20Gbps, USB-C, USB-A", "networking": "2.5GbE LAN + Wi-Fi 6E + Bluetooth 5.3", "vrm": "16+1 phase 90A per phase", "rgb": "AURA Sync ARGB headers", "warranty": "3 years"}),
            "ASUS",
        ),
        (
            "AMD ATX Motherboard",
            "ATX form-factor motherboard for AMD Ryzen 7000 series processors (AM5 socket). Supports DDR5 up to 6600MHz OC, PCIe 5.0 x16 for GPU, dual M.2 PCIe 5.0 slots, 2.5GbE LAN, Wi-Fi 6E, and USB4 40Gbps. VRM: 14+2+1 phase 110A for extreme overclocking headroom. Manufacturer: MSI (MAG X670E Tomahawk). Rated 4.6/5 from 1,432 builders. Excellent AM5 platform longevity — AMD confirmed socket support through 2027+.",
            219.99, "Electronics", "🖥️", 50,
            opts([
                {"name": "Chipset", "values": ["AMD X670E (OC + PCIe 5.0)", "AMD B650 (Standard)"]},
                {"name": "Form Factor", "values": ["ATX (30.5×24.4cm)", "mATX (24.4×24.4cm)"]},
            ]),
            4.6, 1432,
            spec({"socket": "AMD AM5", "cpu_support": "AMD Ryzen 7000 series (Zen 4, Zen 4c)", "memory_type": "DDR5, 4 slots, up to 192GB, 6600MHz OC with EXPO", "pcie_slots": "PCIe 5.0 x16 (GPU) + PCIe 4.0 x16 + PCIe 3.0 x1", "m2_slots": "3× M.2 (2× PCIe 5.0, 1× PCIe 4.0)", "usb": "USB4 40Gbps, USB 3.2 Gen 2×2, USB-C", "networking": "2.5GbE LAN + Wi-Fi 6E + Bluetooth 5.3", "vrm": "14+2+1 phase 110A per phase", "platform_longevity": "AMD confirmed AM5 support through 2027+", "warranty": "3 years"}),
            "MSI",
        ),
    ]

    cursor.executemany(
        """INSERT INTO products
           (name, description, price, category, image_url, stock, options,
            rating, review_count, specs, manufacturer)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        products,
    )

    conn.commit()
    conn.close()
    logger.info(f"Seeded {len(products)} products with full specs, ratings and manufacturer info")

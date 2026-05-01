"""
One-time migration: insert PC-component products into the live database
and rebuild the ChromaDB vector store so the chatbot can find them.

Run from the backend directory:
    python add_pc_components.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from database import get_connection

def opts(o): return json.dumps(o)
def spec(d): return json.dumps(d)

NEW_PRODUCTS = [
    (
        "DDR4 RAM Kit",
        "High-performance DDR4 desktop memory kit with XMP 2.0 profile support for one-click overclocking. Low-profile aluminium heat spreader fits most CPU coolers. Dual-channel ready — buy two kits for maximum bandwidth. Manufacturer: Corsair. Rated 4.7/5 from 3,842 verified builders. Compatible with Intel 10th/11th/12th Gen and AMD Ryzen 3000/5000. Lifetime warranty.",
        49.99, "Electronics", "🖥️", 150,
        opts([
            {"name": "Capacity", "values": ["8GB (1×8GB)", "16GB (2×8GB)", "32GB (2×16GB)", "64GB (2×32GB)"]},
            {"name": "Speed",    "values": ["DDR4-2666MHz", "DDR4-3200MHz", "DDR4-3600MHz"]},
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
            {"name": "Speed",    "values": ["DDR5-4800MHz", "DDR5-5600MHz", "DDR5-6000MHz", "DDR5-6400MHz"]},
        ]),
        4.6, 1987,
        spec({"type": "DDR5 SDRAM", "form_factor": "DIMM (288-pin)", "voltage": "1.1V (JEDEC) / 1.35V (XMP)", "on_die_ecc": True, "xmp_profile": "XMP 3.0 + AMD EXPO", "bandwidth": "Up to 2× DDR4 bandwidth", "pmic": "Integrated PMIC for stable power", "compatibility": "Intel LGA1700 (12th/13th/14th Gen), AMD AM5 (Ryzen 7000)", "best_for": "Gaming, AI workloads, content creation", "warranty": "Lifetime manufacturer warranty"}),
        "Kingston Fury",
    ),
    (
        "NVMe PCIe SSD",
        "High-speed PCIe 4.0 NVMe M.2 solid state drive delivering up to 7,450 MB/s sequential read and 6,900 MB/s sequential write — ideal for OS drives, game libraries, and video editing scratch disks. Dynamic Thermal Guard prevents throttling. Manufacturer: Samsung (990 Pro series). Rated 4.8/5 from 5,231 users. Includes heatsink option. 5-year warranty. TBW: up to 1,200TB (2TB).",
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
        "Fully modular ATX power supply with 80 Plus Gold efficiency (90% at 50% load). All-Japanese 105°C capacitors rated for 10-year life. Zero RPM fan mode below 30% load for silent operation. Over-voltage, over-current, over-temperature, and short-circuit protection. Manufacturer: Corsair (RM Series). Rated 4.8/5 from 4,231 PC builders. 10-year warranty. ATX 3.0 compliant with PCIe 5.0 connector included.",
        89.99, "Electronics", "⚡", 95,
        opts([
            {"name": "Wattage",  "values": ["550W", "650W", "750W", "850W", "1000W", "1200W"]},
            {"name": "Modular",  "values": ["Semi-Modular", "Fully Modular"]},
        ]),
        4.8, 4231,
        spec({"efficiency": "80 Plus Gold (90% at 50% load)", "atx_version": "ATX 3.0 compliant", "pcie_connector": "PCIe 5.0 (600W) included", "capacitors": "All-Japanese 105°C rated", "fan_mode": "Zero RPM below 30% load", "protections": "OVP, OCP, OTP, SCP, UVP", "modular": "Fully or Semi-Modular options", "warranty": "10 years", "rails": "Single +12V rail", "certifications": "80+ Gold, UL, CE, TÜV"}),
        "Corsair",
    ),
    (
        "High-Capacity Power Bank",
        "Laptop-grade power bank with 140W USB-C bidirectional charging — fast enough to charge a MacBook Pro or gaming laptop. Dual USB-C PD + USB-A QC3.0. Smart power allocation automatically splits output across 3 devices. Manufacturer: Anker (737 series). Rated 4.7/5 from 3,109 users. TSA approved. Digital LED display. 18-month warranty.",
        79.99, "Electronics", "🔋", 80,
        opts([
            {"name": "Capacity", "values": ["20,000mAh", "26,800mAh", "40,000mAh"]},
            {"name": "Color",    "values": ["Black", "Dark Blue"]},
        ]),
        4.7, 3109,
        spec({"capacity_options": "20,000 / 26,800 / 40,000mAh", "usb_c_output": "140W USB-C PD (bidirectional)", "usb_a_output": "18W QC3.0", "simultaneous": "3 devices at once", "laptop_compatible": True, "display": "Digital LED power indicator", "tsa": "TSA carry-on approved (20,000mAh)", "weight": "449g (20,000mAh)", "warranty": "18 months", "certifications": "CE, FCC, RoHS"}),
        "Anker",
    ),
    (
        "Intel ATX Motherboard",
        "ATX form-factor motherboard for Intel 12th/13th/14th Gen processors (LGA1700 socket). Supports DDR5 up to 7200MHz OC, PCIe 5.0 x16 for GPU, dual M.2 PCIe 4.0 slots, 2.5GbE LAN, Wi-Fi 6E, and USB 3.2 Gen 2×2 (20Gbps). VRM: 16+1 phase 90A for stable overclocking. Manufacturer: ASUS (PRIME Z790-P). Rated 4.7/5 from 1,892 builders. AURA Sync RGB headers. 3-year warranty.",
        189.99, "Electronics", "🖥️", 60,
        opts([
            {"name": "Chipset",     "values": ["Intel Z790 (OC Support)", "Intel B760 (Standard)"]},
            {"name": "Form Factor", "values": ["ATX (30.5×24.4cm)", "mATX (24.4×24.4cm)"]},
        ]),
        4.7, 1892,
        spec({"socket": "Intel LGA1700", "cpu_support": "Intel 12th/13th/14th Gen (Alder/Raptor Lake)", "memory_type": "DDR5, 4 slots, up to 192GB, 7200MHz OC", "pcie_slots": "PCIe 5.0 x16 (GPU) + PCIe 3.0 x1 ×2", "m2_slots": "2× M.2 PCIe 4.0 (up to 80mm)", "usb": "USB 3.2 Gen 2×2 20Gbps, USB-C, USB-A", "networking": "2.5GbE LAN + Wi-Fi 6E + Bluetooth 5.3", "vrm": "16+1 phase 90A per phase", "rgb": "AURA Sync ARGB headers", "warranty": "3 years"}),
        "ASUS",
    ),
    (
        "AMD ATX Motherboard",
        "ATX form-factor motherboard for AMD Ryzen 7000 series processors (AM5 socket). Supports DDR5 up to 6600MHz OC with EXPO, PCIe 5.0 x16 for GPU, dual M.2 PCIe 5.0 slots, 2.5GbE LAN, Wi-Fi 6E, and USB4 40Gbps. VRM: 14+2+1 phase 110A for extreme overclocking. Manufacturer: MSI (MAG X670E Tomahawk). Rated 4.6/5 from 1,432 builders. AMD confirmed AM5 socket support through 2027+. 3-year warranty.",
        219.99, "Electronics", "🖥️", 50,
        opts([
            {"name": "Chipset",     "values": ["AMD X670E (OC + PCIe 5.0)", "AMD B650 (Standard)"]},
            {"name": "Form Factor", "values": ["ATX (30.5×24.4cm)", "mATX (24.4×24.4cm)"]},
        ]),
        4.6, 1432,
        spec({"socket": "AMD AM5", "cpu_support": "AMD Ryzen 7000 series (Zen 4)", "memory_type": "DDR5, 4 slots, up to 192GB, 6600MHz OC with EXPO", "pcie_slots": "PCIe 5.0 x16 (GPU) + PCIe 4.0 x16 + PCIe 3.0 x1", "m2_slots": "3× M.2 (2× PCIe 5.0, 1× PCIe 4.0)", "usb": "USB4 40Gbps, USB 3.2 Gen 2×2, USB-C", "networking": "2.5GbE LAN + Wi-Fi 6E + Bluetooth 5.3", "vrm": "14+2+1 phase 110A per phase", "platform_longevity": "AMD confirmed AM5 support through 2027+", "warranty": "3 years"}),
        "MSI",
    ),
]


def insert_products():
    conn = get_connection()
    cursor = conn.cursor()

    # Get existing names to avoid duplicates
    cursor.execute("SELECT name FROM products")
    existing = {row[0] for row in cursor.fetchall()}

    to_insert = [p for p in NEW_PRODUCTS if p[0] not in existing]
    if not to_insert:
        print("All products already exist — nothing to insert.")
        conn.close()
        return 0

    cursor.executemany(
        """INSERT INTO products
           (name, description, price, category, image_url, stock, options,
            rating, review_count, specs, manufacturer)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        to_insert,
    )
    conn.commit()
    conn.close()
    print(f"Inserted {len(to_insert)} new products.")
    return len(to_insert)


if __name__ == "__main__":
    inserted = insert_products()
    if inserted > 0:
        print("Rebuilding ChromaDB vector store...")
        from rag import build_vector_store
        build_vector_store()
        print("Done! Vector store rebuilt with all products.")
    else:
        print("No rebuild needed.")

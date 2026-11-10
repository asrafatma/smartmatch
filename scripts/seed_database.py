import os
import sys
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.repositories.user_repository import UserRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.claim_repository import ClaimRepository
from app.repositories.db import get_db
from app.utils.security import hash_password
from app.services.matching_service import MatchingEngine

def create_synthetic_image(dest_path: str, bg_color: tuple, text: str):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    img = Image.new("RGB", (400, 300), color=bg_color)
    draw = ImageDraw.Draw(img)
    # Draw border
    draw.rectangle([10, 10, 390, 290], outline=(255, 255, 255), width=3)
    # Simple label text
    draw.text((25, 130), text, fill=(255, 255, 255))
    img.save(dest_path)

def seed():
    app = create_app()
    with app.app_context():
        db = get_db()
        print("Clearing existing collections for fresh seed...")
        db.users.delete_many({})
        db.reports.delete_many({})
        db.matches.delete_many({})
        db.claims.delete_many({})
        db.ai_logs.delete_many({})

        upload_dir = app.config.get("UPLOAD_FOLDER", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        print("Generating synthetic item photographs...")
        img_wallet_lost = os.path.join(upload_dir, "seed_wallet_lost.jpg")
        img_wallet_found = os.path.join(upload_dir, "seed_wallet_found.jpg")
        img_bottle_lost = os.path.join(upload_dir, "seed_bottle_lost.jpg")
        img_bottle_found = os.path.join(upload_dir, "seed_bottle_found.jpg")
        img_backpack_lost = os.path.join(upload_dir, "seed_backpack_lost.jpg")
        img_bag_found = os.path.join(upload_dir, "seed_bag_found.jpg")
        img_notebook = os.path.join(upload_dir, "seed_notebook.jpg")
        img_keys = os.path.join(upload_dir, "seed_keys.jpg")

        create_synthetic_image(img_wallet_lost, (24, 24, 27), "LOST: Black Leather Wallet")
        create_synthetic_image(img_wallet_found, (39, 39, 42), "FOUND: Black Leather Bifold")
        create_synthetic_image(img_bottle_lost, (71, 85, 105), "LOST: Hydro Flask Bottle")
        create_synthetic_image(img_bottle_found, (148, 163, 184), "FOUND: Insulated Tumbler")
        create_synthetic_image(img_backpack_lost, (185, 28, 28), "LOST: Red North Face Backpack")
        create_synthetic_image(img_bag_found, (29, 78, 216), "FOUND: Blue Canvas Duffel")
        create_synthetic_image(img_notebook, (21, 128, 61), "LOST: Calculus Notebook")
        create_synthetic_image(img_keys, (100, 116, 139), "FOUND: Honda Keys with Carabiner")

        print("Creating synthetic judge & demo accounts...")
        alice = UserRepository.create(
            name="Alice Student",
            email="alice@campus.edu",
            password_hash=hash_password("student123"),
            role="student"
        )
        bob = UserRepository.create(
            name="Bob Finder",
            email="bob@campus.edu",
            password_hash=hash_password("finder123"),
            role="student"
        )
        admin = UserRepository.create(
            name="Campus Administrator",
            email="admin@campus.edu",
            password_hash=hash_password("admin123"),
            role="admin"
        )

        print(f"Users created: Alice ({alice['id']}), Bob ({bob['id']}), Admin ({admin['id']})")

        print("Seeding synthetic lost and found reports...")
        
        # 1. OBVIOUS MATCH PAIR: Black Leather Wallet
        rep_lost_wallet = ReportRepository.create({
            "user_id": alice["id"],
            "report_type": "lost",
            "title": "Black Leather Bifold Wallet",
            "description": "Lost my black leather wallet on 2nd floor library study desk. Contains university student card and silver stitched logo.",
            "category": "personal_accessory",
            "object_type": "wallet",
            "location": "Main Library 2nd Floor Study Desk",
            "incident_date": "2026-11-08",
            "image_path": "/uploads/seed_wallet_lost.jpg",
            "attributes": {
                "color": ["black"],
                "material": ["leather"],
                "shape": ["foldable"],
                "brand_or_logo": ["small_silver_logo"],
                "distinctive_features": ["stitched edge", "student id inside"]
            },
            "user_stated_details": ["University card inside", "Lost on 2nd floor library"],
            "visually_observed_details": ["Dark leather grain surface", "Foldable bifold design", "Silver corner accent"],
            "unknowns": ["Serial number not visible"],
            "image_quality": "high",
            "ai_status": "completed",
            "extraction_version": "1.0.0",
            "status": "active"
        })

        rep_found_wallet = ReportRepository.create({
            "user_id": bob["id"],
            "report_type": "found",
            "title": "Found Black Leather Wallet",
            "description": "Found a folded black leather wallet resting near the printing station on library second floor.",
            "category": "personal_accessory",
            "object_type": "wallet",
            "location": "Main Library 2nd Floor Near Printers",
            "incident_date": "2026-11-08",
            "image_path": "/uploads/seed_wallet_found.jpg",
            "attributes": {
                "color": ["black"],
                "material": ["leather"],
                "shape": ["foldable"],
                "brand_or_logo": ["small_silver_logo"],
                "distinctive_features": ["stitched edge"]
            },
            "user_stated_details": ["Found near printing station"],
            "visually_observed_details": ["Black textured leather", "Stitched border", "Silver emblem"],
            "unknowns": ["Internal cards not publicly checked"],
            "image_quality": "high",
            "ai_status": "completed",
            "extraction_version": "1.0.0",
            "status": "active"
        })

        # 2. PARTIAL MATCH PAIR: Water Bottle vs Tumbler
        rep_lost_bottle = ReportRepository.create({
            "user_id": alice["id"],
            "report_type": "lost",
            "title": "White Stainless Steel Hydro Flask",
            "description": "Lost my insulated white stainless steel water bottle at the campus recreation center gym bench.",
            "category": "bottle_container",
            "object_type": "water_bottle",
            "location": "Student Recreation Center Gym",
            "incident_date": "2026-11-07",
            "image_path": "/uploads/seed_bottle_lost.jpg",
            "attributes": {
                "color": ["white", "silver"],
                "material": ["stainless_steel"],
                "shape": ["cylindrical"],
                "brand_or_logo": ["hydro_flask"],
                "distinctive_features": ["national park sticker", "scratched bottom"]
            },
            "user_stated_details": ["Left near free weight bench"],
            "visually_observed_details": ["White cylindrical flask", "Black wide-mouth cap"],
            "unknowns": ["Capacity unknown"],
            "image_quality": "adequate",
            "ai_status": "completed",
            "extraction_version": "1.0.0",
            "status": "active"
        })

        rep_found_bottle = ReportRepository.create({
            "user_id": bob["id"],
            "report_type": "found",
            "title": "White Metal Drink Tumbler",
            "description": "Found an unbranded or worn white insulated drink tumbler in the recreation center locker room.",
            "category": "bottle_container",
            "object_type": "water_bottle",
            "location": "Student Recreation Center Locker Area",
            "incident_date": "2026-11-07",
            "image_path": "/uploads/seed_bottle_found.jpg",
            "attributes": {
                "color": ["white"],
                "material": ["stainless_steel"],
                "shape": ["cylindrical"],
                "brand_or_logo": [],
                "distinctive_features": ["scratched base"]
            },
            "user_stated_details": ["Turned in at desk"],
            "visually_observed_details": ["White cylinder bottle", "Minor abrasions on bottom"],
            "unknowns": ["Brand logo worn or absent"],
            "image_quality": "adequate",
            "ai_status": "completed",
            "extraction_version": "1.0.0",
            "status": "active"
        })

        # 3. CONFLICTING / NON-MATCH PAIR: Red Backpack vs Blue Duffel
        rep_lost_backpack = ReportRepository.create({
            "user_id": alice["id"],
            "report_type": "lost",
            "title": "Red The North Face Backpack",
            "description": "Bright red nylon backpack left in lecture hall after CS class.",
            "category": "bag_backpack",
            "object_type": "backpack",
            "location": "Engineering Hall Room 101",
            "incident_date": "2026-11-05",
            "image_path": "/uploads/seed_backpack_lost.jpg",
            "attributes": {
                "color": ["red"],
                "material": ["nylon"],
                "shape": ["rectangular"],
                "brand_or_logo": ["the_north_face"],
                "distinctive_features": ["reflective strip"]
            },
            "user_stated_details": ["CS textbook inside"],
            "visually_observed_details": ["Bright red pack"],
            "unknowns": ["Contents unknown"],
            "image_quality": "adequate",
            "ai_status": "completed",
            "extraction_version": "1.0.0",
            "status": "active"
        })

        rep_found_duffel = ReportRepository.create({
            "user_id": bob["id"],
            "report_type": "found",
            "title": "Blue Canvas Sports Duffel Bag",
            "description": "Blue athletic duffel bag left on outdoor bleachers.",
            "category": "bag_backpack",
            "object_type": "duffel_bag",
            "location": "Athletic Stadium Bleachers",
            "incident_date": "2026-10-15",
            "image_path": "/uploads/seed_bag_found.jpg",
            "attributes": {
                "color": ["blue"],
                "material": ["canvas"],
                "shape": ["cylindrical"],
                "brand_or_logo": ["nike"],
                "distinctive_features": ["athletic stripe"]
            },
            "user_stated_details": ["Found after track practice"],
            "visually_observed_details": ["Heavy blue canvas", "White swoosh"],
            "unknowns": ["Internal items not checked"],
            "image_quality": "adequate",
            "ai_status": "completed",
            "extraction_version": "1.0.0",
            "status": "active"
        })

        # 4. MANUAL FALLBACK REPORT: Calculus Notebook
        ReportRepository.create({
            "user_id": alice["id"],
            "report_type": "lost",
            "title": "Green Spiral Calculus Notebook",
            "description": "Green paper cover spiral bound notebook containing multivariable calculus class notes.",
            "category": "stationery",
            "object_type": "notebook",
            "location": "Mathematics Hall Room 304",
            "incident_date": "2026-11-09",
            "image_path": "/uploads/seed_notebook.jpg",
            "attributes": {
                "color": ["green"],
                "material": ["paper"],
                "shape": ["rectangular"],
                "brand_or_logo": [],
                "distinctive_features": ["formula scribbles on front"]
            },
            "user_stated_details": ["Math notes inside"],
            "visually_observed_details": ["Manual fallback mode: rule-based extraction active"],
            "unknowns": ["AI service unavailable: manual attribute confirmation enabled"],
            "image_quality": "adequate",
            "ai_status": "manual",
            "extraction_version": "1.0.0",
            "status": "active"
        })

        # 5. FOUND KEYS WITH PENDING CLAIM
        rep_found_keys = ReportRepository.create({
            "user_id": bob["id"],
            "report_type": "found",
            "title": "Honda Car Keys on Red Carabiner",
            "description": "Set of automotive keys with a black Honda electronic fob attached to a red aluminum carabiner.",
            "category": "key_id",
            "object_type": "keys",
            "location": "North Campus Parking Lot B",
            "incident_date": "2026-11-09",
            "image_path": "/uploads/seed_keys.jpg",
            "attributes": {
                "color": ["silver", "black", "red"],
                "material": ["metal", "plastic"],
                "shape": ["compact"],
                "brand_or_logo": ["honda"],
                "distinctive_features": ["red carabiner clip", "grooved brass key"]
            },
            "user_stated_details": ["Found near space 42"],
            "visually_observed_details": ["Electronic fob with 4 buttons", "Red carabiner"],
            "unknowns": ["License plate unlinked"],
            "image_quality": "high",
            "ai_status": "completed",
            "extraction_version": "1.0.0",
            "status": "claim_pending"
        })

        # Seed sample pending claim on Keys by Alice
        ClaimRepository.create(
            report_id=rep_found_keys["id"],
            claimant_id=alice["id"],
            verification_answers="There is a small circular bronze gym scan tag attached underneath the Honda fob, and the brass house key has the initial 'A' engraved."
        )

        print("Executing deterministic matching engine across synthetic seed reports...")
        matches_lost_wallet = MatchingEngine.find_matches_for_report(rep_lost_wallet["id"])
        print(f"Calculated {len(matches_lost_wallet)} candidate matches for Lost Wallet.")
        if matches_lost_wallet:
            top_match = matches_lost_wallet[0]
            print(f"Top match score: {top_match['score']}/100 ({top_match['label']}) -> Found Wallet ID {top_match['candidate_report']['id']}")

        matches_bottle = MatchingEngine.find_matches_for_report(rep_lost_bottle["id"])
        print(f"Calculated {len(matches_bottle)} candidate matches for Water Bottle.")

        matches_backpack = MatchingEngine.find_matches_for_report(rep_lost_backpack["id"])
        print(f"Calculated {len(matches_backpack)} candidate matches for Backpack.")

        print("\n==========================================")
        print("Database seed completed successfully!")
        print("Synthetic Judge Demo Accounts:")
        print("  1. Student: alice@campus.edu  / student123")
        print("  2. Finder:  bob@campus.edu    / finder123")
        print("  3. Admin:   admin@campus.edu  / admin123")
        print("==========================================")

if __name__ == "__main__":
    seed()

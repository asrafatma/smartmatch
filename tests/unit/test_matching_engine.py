import pytest
from app.services.matching_service import MatchingEngine
from app.config import Config

def test_weights_sum_to_100():
    total_weight = sum(Config.MATCHING_WEIGHTS.values())
    assert total_weight == 100

def test_matching_obvious_pair_high_score():
    lost_wallet = {
        "title": "Black Leather Wallet",
        "description": "Lost folded black leather wallet with silver stitched emblem",
        "category": "personal_accessory",
        "object_type": "wallet",
        "location": "Main Library 2nd Floor",
        "incident_date": "2026-11-08",
        "attributes": {
            "color": ["black"],
            "material": ["leather"],
            "shape": ["foldable"],
            "brand_or_logo": ["silver_emblem"],
            "distinctive_features": ["stitched"]
        }
    }

    found_wallet = {
        "title": "Found Black Leather Bifold Wallet",
        "description": "Black leather wallet found near library printers",
        "category": "personal_accessory",
        "object_type": "wallet",
        "location": "Main Library 2nd Floor",
        "incident_date": "2026-11-08",
        "attributes": {
            "color": ["black"],
            "material": ["leather"],
            "shape": ["foldable"],
            "brand_or_logo": ["silver_emblem"],
            "distinctive_features": ["stitched"]
        }
    }

    res = MatchingEngine.compare_reports(lost_wallet, found_wallet)
    assert res["score"] >= 85
    assert res["label"] == "Strong candidate"
    assert "category" in res["score_breakdown"]
    assert res["score_breakdown"]["category"] == 20
    assert len(res["matched_attributes"]) >= 5
    assert len(res["conflicts"]) == 0

def test_conflicting_attributes_low_score():
    lost_backpack = {
        "title": "Red Nylon Backpack",
        "description": "Bright red backpack",
        "category": "bag_backpack",
        "object_type": "backpack",
        "location": "Engineering Hall",
        "incident_date": "2026-11-01",
        "attributes": {
            "color": ["red"],
            "material": ["nylon"],
            "shape": ["rectangular"],
            "brand_or_logo": ["the_north_face"],
            "distinctive_features": []
        }
    }

    found_duffel = {
        "title": "Blue Canvas Duffel Bag",
        "description": "Blue cylindrical duffel sports bag",
        "category": "bag_backpack",
        "object_type": "duffel_bag",
        "location": "Athletic Stadium",
        "incident_date": "2026-09-01",  # 60 days apart
        "attributes": {
            "color": ["blue"],
            "material": ["canvas"],
            "shape": ["cylindrical"],
            "brand_or_logo": ["nike"],
            "distinctive_features": []
        }
    }

    res = MatchingEngine.compare_reports(lost_backpack, found_duffel)
    assert res["score"] < 40
    assert res["label"] == "Low similarity"
    assert len(res["conflicts"]) >= 2

def test_unknown_attributes_handled_neutrally():
    item_with_unknowns = {
        "title": "Lost Item",
        "description": "Lost an item somewhere",
        "category": "other",
        "object_type": "item",
        "location": "Campus",
        "incident_date": "2026-11-08",
        "attributes": {
            "color": [],
            "material": [],
            "shape": [],
            "brand_or_logo": [],
            "distinctive_features": []
        }
    }

    found_item = {
        "title": "Found Item",
        "description": "Found item on campus",
        "category": "other",
        "object_type": "item",
        "location": "Campus",
        "incident_date": "2026-11-08",
        "attributes": {
            "color": [],
            "material": [],
            "shape": [],
            "brand_or_logo": [],
            "distinctive_features": []
        }
    }

    res = MatchingEngine.compare_reports(item_with_unknowns, found_item)
    # Neutral scores without zeroing out or throwing exceptions
    assert 20 <= res["score"] <= 70
    assert len(res["unknowns"]) > 0

def test_known_pair_ranks_above_distractor():
    base_lost = {
        "title": "Black Leather Wallet",
        "description": "Black leather wallet with silver badge",
        "category": "personal_accessory",
        "object_type": "wallet",
        "location": "Library",
        "incident_date": "2026-11-08",
        "attributes": {"color": ["black"], "material": ["leather"], "brand_or_logo": ["silver_badge"]}
    }

    true_match = {
        "title": "Found Wallet",
        "description": "Black leather wallet with silver badge found in Library",
        "category": "personal_accessory",
        "object_type": "wallet",
        "location": "Library",
        "incident_date": "2026-11-08",
        "attributes": {"color": ["black"], "material": ["leather"], "brand_or_logo": ["silver_badge"]}
    }

    distractor = {
        "title": "Found Yellow Water Bottle",
        "description": "Yellow plastic bottle found in Gym",
        "category": "bottle_container",
        "object_type": "water_bottle",
        "location": "Gym",
        "incident_date": "2026-10-15",
        "attributes": {"color": ["yellow"], "material": ["plastic"]}
    }

    score_true = MatchingEngine.compare_reports(base_lost, true_match)["score"]
    score_distractor = MatchingEngine.compare_reports(base_lost, distractor)["score"]

    assert score_true > score_distractor
    assert score_true >= 80
    assert score_distractor < 30

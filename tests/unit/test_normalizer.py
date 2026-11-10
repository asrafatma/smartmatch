import pytest
from app.ai.normalizer import Normalizer

def test_normalize_color():
    assert Normalizer.normalize_color("Navy") == "dark_blue"
    assert Normalizer.normalize_color("dark blue") == "dark_blue"
    assert Normalizer.normalize_color("crimson") == "red"
    assert Normalizer.normalize_color("charcoal") == "dark_gray"
    assert Normalizer.normalize_color("Silver") == "silver"
    assert Normalizer.normalize_color("  BLACK  ") == "black"

def test_normalize_material():
    assert Normalizer.normalize_material("faux leather") == "synthetic_leather"
    assert Normalizer.normalize_material("Stainless Steel") == "stainless_steel"
    assert Normalizer.normalize_material("cloth") == "fabric"
    assert Normalizer.normalize_material("nylon") == "nylon"

def test_normalize_category():
    assert Normalizer.normalize_category("electronics") == "electronics"
    assert Normalizer.normalize_category("device") == "electronics"
    assert Normalizer.normalize_category("bag") == "bag_backpack"
    assert Normalizer.normalize_category("key") == "key_id"
    assert Normalizer.normalize_category("unrecognized_xyz") == "other"

def test_normalize_object_type():
    assert Normalizer.normalize_object_type("Card Holder") == "card_holder"
    assert Normalizer.normalize_object_type("wallet") == "wallet"
    assert Normalizer.normalize_object_type("iPhone") == "smartphone"
    assert Normalizer.normalize_object_type("hydro flask") == "water_bottle"
    assert Normalizer.normalize_object_type("bookbag") == "backpack"

def test_normalize_attributes_dict():
    raw = {
        "color": ["Navy Blue", "silver", "Navy"],
        "material": ["faux leather", "metal"],
        "shape": ["foldable", "Bifold"],
        "brand_or_logo": ["Apple, Inc.", "apple"],
        "distinctive_features": ["Scratch on corner!", "scratch on corner"]
    }
    norm = Normalizer.normalize_attributes(raw)
    # Deduplication and normalization
    assert "dark_blue" in norm["color"]
    assert "silver" in norm["color"]
    assert len([c for c in norm["color"] if c == "dark_blue"]) == 1
    assert "synthetic_leather" in norm["material"]
    assert "metal" in norm["material"]
    assert "foldable" in norm["shape"]

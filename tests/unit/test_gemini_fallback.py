import pytest
from app.ai.report_analyzer import ReportAnalyzer
from app.ai.schemas import ItemExtractionResult

def test_fallback_extract_detects_keywords():
    title = "Lost Black Leather Bifold Wallet"
    desc = "It is a rectangular wallet made of genuine black leather with stitched edges."
    cat = "personal_accessory"

    result = ReportAnalyzer.fallback_extract(title, desc, cat)
    
    # Must validate against ItemExtractionResult Pydantic schema
    validated = ItemExtractionResult.model_validate(result)
    assert validated.category == "personal_accessory"
    assert "black" in validated.attributes.color
    assert "leather" in validated.attributes.material
    assert "rectangular" in validated.attributes.shape or "foldable" in validated.attributes.shape
    assert len(validated.unknowns) > 0
    assert "AI service unavailable" in validated.unknowns[0]

def test_analyze_handles_missing_api_key_cleanly(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    
    res, status, err = ReportAnalyzer.analyze(
        title="Blue Hydro Flask Bottle",
        description="Blue stainless steel water bottle left at gym bench",
        category="bottle_container",
        image_path="non_existent_mock_image.jpg"
    )
    
    assert status == "manual"
    assert err == "API_KEY_NOT_CONFIGURED"
    assert res["category"] == "bottle_container"
    assert "blue" in res["attributes"]["color"]
    assert "stainless steel" in res["attributes"]["material"] or "steel" in res["attributes"]["material"]

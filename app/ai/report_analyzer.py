import logging
import re
from app.ai.gemini_client import GeminiClient
from app.ai.schemas import ItemExtractionResult, AttributeDetails
from app.ai.normalizer import Normalizer
from app.repositories.ai_log_repository import AILogRepository
from app.config import Config

logger = logging.getLogger(__name__)

class ReportAnalyzer:
    COMMON_COLORS = [
        "black", "white", "silver", "gray", "grey", "blue", "navy",
        "red", "green", "yellow", "brown", "tan", "orange", "purple", "pink", "gold"
    ]
    COMMON_MATERIALS = [
        "leather", "plastic", "metal", "aluminum", "steel", "stainless steel",
        "canvas", "nylon", "fabric", "cloth", "denim", "glass", "rubber", "silicone"
    ]
    COMMON_SHAPES = [
        "rectangular", "cylindrical", "round", "foldable", "flat", "square", "compact"
    ]

    @classmethod
    def fallback_extract(cls, title: str, description: str, category: str) -> dict:
        """
        Rule-based heuristic extractor used when Gemini AI is unavailable,
        ensuring zero disruption to report submission.
        """
        text = f"{title} {description}".lower()

        # Extract colors
        detected_colors = [c for c in cls.COMMON_COLORS if re.search(rf"\b{c}\b", text)]
        # Extract materials
        detected_materials = [m for m in cls.COMMON_MATERIALS if re.search(rf"\b{m}\b", text)]
        # Extract shapes
        detected_shapes = [s for s in cls.COMMON_SHAPES if re.search(rf"\b{s}\b", text)]

        # Object type heuristic
        normalized_obj = Normalizer.normalize_object_type(title)
        if not normalized_obj:
            normalized_obj = Normalizer.normalize_object_type(description)
        if not normalized_obj:
            normalized_obj = "item"

        attrs = AttributeDetails(
            color=detected_colors or ["unknown"],
            material=detected_materials,
            shape=detected_shapes,
            brand_or_logo=[],
            distinctive_features=[]
        )

        user_details = []
        if title:
            user_details.append(f"Title: {title}")
        if description:
            user_details.append(description[:100])

        result = ItemExtractionResult(
            object_type=normalized_obj.replace("_", " "),
            category=category or "other",
            attributes=attrs,
            user_stated_details=user_details,
            visually_observed_details=["Manual entry mode: image not processed by AI"],
            unknowns=["AI service unavailable: manual attribute confirmation enabled"],
            image_quality="adequate"
        )
        return result.model_dump()

    @classmethod
    def analyze(
        cls,
        title: str,
        description: str,
        category: str,
        image_path: str,
        report_id: str = None
    ) -> tuple[dict, str, str | None]:
        """
        Analyzes report with Gemini. Returns (extracted_attributes_dict, ai_status, error_type).
        Guarantees fallback when AI is unavailable.
        """
        gemini = GeminiClient()
        if not gemini.api_key:
            logger.info("GEMINI_API_KEY not configured. Using rule-based fallback attributes.")
            fallback = cls.fallback_extract(title, description, category)
            AILogRepository.log(
                report_id=report_id,
                model_name="none",
                prompt_version="v1",
                extraction_version=Config.EXTRACTION_VERSION,
                status="manual",
                error_type="API_KEY_NOT_CONFIGURED"
            )
            return fallback, "manual", "API_KEY_NOT_CONFIGURED"

        try:
            result = gemini.extract_item_attributes(
                description=f"Title: {title}. Description: {description}",
                image_path=image_path
            )
            AILogRepository.log(
                report_id=report_id,
                model_name=gemini.model_name,
                prompt_version="v1",
                extraction_version=Config.EXTRACTION_VERSION,
                status="completed",
                error_type=None
            )
            return result, "completed", None
        except Exception as e:
            logger.warning("Gemini extraction failed (%s). Engaging manual fallback.", e)
            fallback = cls.fallback_extract(title, description, category)
            fallback["unknowns"].append(f"AI extraction encountered: {str(e)[:80]}")
            AILogRepository.log(
                report_id=report_id,
                model_name=gemini.model_name or "unknown",
                prompt_version="v1",
                extraction_version=Config.EXTRACTION_VERSION,
                status="failed",
                error_type=type(e).__name__
            )
            return fallback, "failed", type(e).__name__

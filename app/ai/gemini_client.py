import os
import json
import logging
from typing import Optional
from google import genai
from google.genai import types
from app.ai.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT
from app.ai.schemas import ItemExtractionResult

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error("Failed to initialize Gemini Client: %s", e)

    def extract_item_attributes(self, description: str, image_path: str) -> dict:
        """
        Calls Gemini API with multimodal input (text description + image)
        and validates response against ItemExtractionResult schema.
        """
        if not self.api_key or not self.client:
            raise ValueError("GEMINI_API_KEY is not configured or client initialization failed")

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found at path: {image_path}")

        # Determine MIME type
        ext = image_path.rsplit(".", 1)[-1].lower()
        mime_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp"
        }
        mime_type = mime_map.get(ext, "image/jpeg")

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        user_prompt = EXTRACTION_USER_PROMPT.format(description=description)

        # Call with 1 bounded retry for transient network failure
        attempts = 0
        last_error = None

        while attempts < 2:
            attempts += 1
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[
                        EXTRACTION_SYSTEM_PROMPT,
                        image_part,
                        user_prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    )
                )

                response_text = response.text.strip()
                # Parse and validate with Pydantic
                parsed = json.loads(response_text)
                validated = ItemExtractionResult.model_validate(parsed)
                return validated.model_dump()
            except Exception as e:
                last_error = e
                logger.warning("Gemini extraction attempt %d failed: %s", attempts, e)

        raise RuntimeError(f"Gemini extraction failed after {attempts} attempts: {str(last_error)}")

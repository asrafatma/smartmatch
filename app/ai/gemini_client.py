import os
import json
import logging
from typing import Optional
from PIL import Image
from google import genai
from google.genai import types
from pydantic import ValidationError
from app.ai.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT
from app.ai.schemas import ItemExtractionResult

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TIMEOUT_SECONDS = 30

# Map PIL-detected formats to MIME types accepted by Gemini
PIL_FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
EXTENSION_TO_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def _strip_code_fences(text: str) -> str:
    """Some model responses wrap JSON in ```json fences despite JSON mode; tolerate that."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


class GeminiClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        # Precedence: explicit argument > GEMINI_MODEL env var > default
        self.model_name = (model_name or os.getenv("GEMINI_MODEL", "") or DEFAULT_MODEL).strip()
        if timeout_seconds is None:
            try:
                timeout_seconds = int(os.getenv("GEMINI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
            except ValueError:
                timeout_seconds = DEFAULT_TIMEOUT_SECONDS
        self.timeout_seconds = max(1, timeout_seconds)
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(
                    api_key=self.api_key,
                    # HttpOptions.timeout is expressed in milliseconds
                    http_options=types.HttpOptions(timeout=self.timeout_seconds * 1000),
                )
            except Exception as e:
                logger.error("Failed to initialize Gemini Client: %s", e)

    @staticmethod
    def detect_mime_type(image_path: str) -> str:
        """Detect MIME type from the actual image bytes, falling back to the extension."""
        try:
            with Image.open(image_path) as img:
                mime = PIL_FORMAT_TO_MIME.get((img.format or "").upper())
                if mime:
                    return mime
        except Exception:
            pass
        ext = image_path.rsplit(".", 1)[-1].lower() if "." in image_path else ""
        return EXTENSION_TO_MIME.get(ext, "image/jpeg")

    def extract_item_attributes(self, description: str, image_path: str) -> dict:
        """
        Calls Gemini API with multimodal input (text description + image)
        and validates response against ItemExtractionResult schema.
        """
        if not self.api_key or not self.client:
            raise ValueError("GEMINI_API_KEY is not configured or client initialization failed")

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found at path: {image_path}")

        mime_type = self.detect_mime_type(image_path)
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        user_prompt = EXTRACTION_USER_PROMPT.format(description=description)
        config = types.GenerateContentConfig(
            system_instruction=EXTRACTION_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.1,
        )

        # 1 bounded retry for transient failures (network errors, malformed JSON)
        attempts = 0
        last_error = None
        while attempts < 2:
            attempts += 1
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[image_part, user_prompt],
                    config=config,
                )
                response_text = (getattr(response, "text", None) or "").strip()
                if not response_text:
                    raise ValueError("Gemini returned an empty response (possibly blocked by safety filters)")

                parsed = json.loads(_strip_code_fences(response_text))
                validated = ItemExtractionResult.model_validate(parsed)
                return validated.model_dump()
            except (ValueError, ValidationError) as e:
                # json.JSONDecodeError is a ValueError subclass
                last_error = e
                logger.warning("Gemini extraction attempt %d returned invalid output: %s", attempts, e)
            except Exception as e:
                last_error = e
                logger.warning("Gemini extraction attempt %d failed: %s", attempts, e)

        raise RuntimeError(f"Gemini extraction failed after {attempts} attempts: {last_error}")

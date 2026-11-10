import io
import logging
import mimetypes
import os
import uuid
from PIL import Image

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
# Formats PIL must actually detect from the file bytes (extension alone is not trusted)
ALLOWED_PIL_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB (spec demo cap)

# Pillow decompression-bomb guard: ~50 megapixels is plenty for a phone photo
Image.MAX_IMAGE_PIXELS = 50_000_000


class ImageValidationError(Exception):
    """Carries an API error code and HTTP status for a rejected upload."""

    def __init__(self, message: str, code: str, status: int):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def _max_bytes() -> int:
    try:
        from flask import current_app
        return int(current_app.config.get("MAX_IMAGE_BYTES", MAX_FILE_SIZE_BYTES))
    except RuntimeError:
        return MAX_FILE_SIZE_BYTES


def inspect_image(file_storage) -> str:
    """
    Validates presence, size, extension and the real image signature.
    Returns the canonical extension for the detected format.
    Raises ImageValidationError with 400 / 413 / 415 semantics.
    """
    if file_storage is None or not getattr(file_storage, "filename", ""):
        raise ImageValidationError(
            "Upload a supported item photograph (JPEG, PNG or WebP) to continue.", "PHOTO_REQUIRED", 400
        )

    filename = file_storage.filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ImageValidationError(
            f"Unsupported file type '.{ext}'. Allowed types are: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
            "UNSUPPORTED_MEDIA_TYPE", 415
        )

    try:
        file_storage.seek(0, os.SEEK_END)
        size = file_storage.tell()
        file_storage.seek(0)
    except Exception:
        raise ImageValidationError("Failed to read the uploaded file.", "INVALID_IMAGE", 400)

    if size == 0:
        raise ImageValidationError("Uploaded image file is empty.", "PHOTO_REQUIRED", 400)
    limit = _max_bytes()
    if size > limit:
        raise ImageValidationError(
            f"Image file exceeds the maximum allowed size of {limit // (1024 * 1024)}MB.", "FILE_TOO_LARGE", 413
        )

    # Decode check: verify() catches truncation/corruption; format check catches renamed files
    try:
        with Image.open(file_storage) as img:
            detected = (img.format or "").upper()
            img.verify()
    except Image.DecompressionBombError:
        raise ImageValidationError("Image dimensions are too large.", "INVALID_IMAGE", 415)
    except Exception:
        raise ImageValidationError("File is not a valid or readable image.", "INVALID_IMAGE", 415)
    finally:
        file_storage.seek(0)

    if detected not in ALLOWED_PIL_FORMATS:
        raise ImageValidationError(
            "File content is not a JPEG, PNG or WebP image.", "UNSUPPORTED_MEDIA_TYPE", 415
        )
    return ALLOWED_PIL_FORMATS[detected]


def validate_image_file(file_storage) -> tuple[bool, str]:
    """Backward-compatible boolean wrapper around inspect_image()."""
    try:
        inspect_image(file_storage)
        return True, ""
    except ImageValidationError as e:
        return False, e.message


def save_upload_image(file_storage, upload_folder: str, ext: str = None) -> tuple[str, str]:
    """
    Saves an uploaded image under a random server-generated name (the user's filename is
    never used) and mirrors it to persistent storage when available.
    Returns (relative_url_path, absolute_file_path).
    """
    os.makedirs(upload_folder, exist_ok=True)
    if not ext:
        ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else "jpg"
    safe_filename = f"{uuid.uuid4().hex}.{ext}"
    dest_path = os.path.join(upload_folder, safe_filename)

    file_storage.seek(0)
    file_storage.save(dest_path)
    persist_image_file(dest_path, safe_filename)
    return f"/uploads/{safe_filename}", dest_path


# ---------------------------------------------------------------------------
# Persistent storage (MongoDB GridFS) for hosts with ephemeral filesystems
# ---------------------------------------------------------------------------

def _gridfs_bucket():
    """Returns a GridFS bucket when a real MongoDB connection is active and enabled."""
    try:
        from flask import current_app
        if not current_app.config.get("IMAGE_STORAGE_GRIDFS", False):
            return None
    except RuntimeError:
        return None
    from app.repositories.db import Database
    if Database.is_mock() or Database.get_db() is None:
        return None
    import gridfs
    return gridfs.GridFSBucket(Database.get_db(), bucket_name="images")


def persist_image_file(path: str, filename: str) -> None:
    bucket = _gridfs_bucket()
    if bucket is None:
        return
    try:
        # Replace any previous copy with the same name (e.g. re-seeding)
        for old in bucket.find({"filename": filename}):
            bucket.delete(old._id)
        with open(path, "rb") as f:
            bucket.upload_from_stream(filename, f)
    except Exception as e:
        logger.error("Failed to persist image %s to GridFS: %s", filename, e)


def load_persisted_image(filename: str) -> tuple[bytes, str] | None:
    """Reads an image from GridFS. Returns (bytes, mimetype) or None."""
    bucket = _gridfs_bucket()
    if bucket is None:
        return None
    try:
        buf = io.BytesIO()
        bucket.download_to_stream_by_name(filename, buf)
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return buf.getvalue(), mime
    except Exception:
        return None


def delete_image_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass

import os
import uuid
from PIL import Image

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

def validate_image_file(file_storage) -> tuple[bool, str]:
    """
    Validates that a file storage object is present, has an allowed extension,
    is within file size limits, and is a valid decodable image.
    """
    if file_storage is None or not file_storage.filename:
        return False, "A valid photograph is mandatory for report submission."

    filename = file_storage.filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type '.{ext}'. Allowed types are: {', '.join(sorted(ALLOWED_EXTENSIONS))}."

    # Check file size by seeking
    try:
        file_storage.seek(0, os.SEEK_END)
        size = file_storage.tell()
        file_storage.seek(0)
        if size == 0:
            return False, "Uploaded image file is empty."
        if size > MAX_FILE_SIZE_BYTES:
            return False, f"Image file exceeds maximum allowed limit of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB."
    except Exception as e:
        return False, f"Failed to inspect file size: {str(e)}"

    # Validate image integrity with PIL
    try:
        img = Image.open(file_storage)
        img.verify()
        file_storage.seek(0)
    except Exception:
        return False, "File is not a valid or readable image."

    return True, ""

def save_upload_image(file_storage, upload_folder: str) -> tuple[str, str]:
    """
    Saves an uploaded image with a safe UUID-based filename.
    Returns (relative_url_path, absolute_file_path).
    """
    os.makedirs(upload_folder, exist_ok=True)
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else "jpg"
    safe_filename = f"{uuid.uuid4().hex}.{ext}"
    dest_path = os.path.join(upload_folder, safe_filename)
    
    file_storage.seek(0)
    file_storage.save(dest_path)
    
    # Store path as /uploads/<safe_filename>
    rel_path = f"/uploads/{safe_filename}"
    return rel_path, dest_path

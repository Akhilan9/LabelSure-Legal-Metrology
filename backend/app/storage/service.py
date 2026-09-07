import hashlib
from pathlib import Path
from uuid import uuid4

SUPPORTED_MIME_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
}

MAGIC_BYTE_SIGNATURES = [
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"RIFF", "image/webp", ".webp"),
]


def detect_and_validate_image(content: bytes, original_filename: str) -> tuple[str, str]:
    """
    Validate that content is non-empty, matches supported magic bytes, and returns (mime_type, ext).
    """
    if not content or len(content) == 0:
        raise ValueError("File content is empty")

    # Check WEBP special case (bytes 0-4 RIFF and bytes 8-12 WEBP)
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp", ".webp"

    for signature, mime_type, ext in MAGIC_BYTE_SIGNATURES:
        if signature != b"RIFF" and content.startswith(signature):
            return mime_type, ext

    raise ValueError("Unsupported or invalid image file. Allowed formats: JPEG, PNG, WebP.")


def calculate_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class LocalStorageService:
    def __init__(self, base_dir: str | Path = "storage"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        clean_rel = Path(relative_path).as_posix().lstrip("/\\")
        target = (self.base_dir / clean_rel).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise ValueError("Path traversal attempt detected")
        return target

    def save_file(self, relative_path: str, data: bytes) -> str:
        target = self._resolve_safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return relative_path

    def read_file(self, relative_path: str) -> bytes:
        target = self._resolve_safe_path(relative_path)
        if not target.is_file():
            raise FileNotFoundError(f"Stored file not found: {relative_path}")
        return target.read_bytes()

    def delete_file(self, relative_path: str) -> bool:
        try:
            target = self._resolve_safe_path(relative_path)
            if target.is_file():
                target.unlink()
                # Clean up parent directory if empty
                try:
                    if target.parent != self.base_dir and not any(target.parent.iterdir()):
                        target.parent.rmdir()
                except OSError:
                    pass
                return True
        except (ValueError, FileNotFoundError):
            pass
        return False

    def file_exists(self, relative_path: str) -> bool:
        try:
            target = self._resolve_safe_path(relative_path)
            return target.is_file()
        except ValueError:
            return False

    def generate_storage_path(self, inspection_id: str, ext: str) -> tuple[str, str]:
        safe_filename = f"{uuid4().hex}{ext}"
        storage_path = f"inspections/{inspection_id}/originals/{safe_filename}"
        return safe_filename, storage_path

    def generate_processed_storage_path(self, inspection_id: str, image_id: str, filename: str = "ocr_ready.png") -> tuple[str, str]:
        storage_path = f"inspections/{inspection_id}/processed/{image_id}/{filename}"
        return filename, storage_path

import pytest
from pathlib import Path

from app.storage.service import (
    LocalStorageService,
    calculate_sha256,
    detect_and_validate_image,
)

# Valid minimal dummy image byte signatures
SAMPLE_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00"
SAMPLE_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
SAMPLE_WEBP = b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x000\x01\x00\x9d\x01*\x01\x00\x01\x00\x00"
INVALID_TEXT = b"This is a text file, not an image!"
EMPTY_BYTES = b""


def test_detect_and_validate_image_success():
    mime, ext = detect_and_validate_image(SAMPLE_JPEG, "photo.jpg")
    assert mime == "image/jpeg"
    assert ext == ".jpg"

    mime, ext = detect_and_validate_image(SAMPLE_PNG, "label.png")
    assert mime == "image/png"
    assert ext == ".png"

    mime, ext = detect_and_validate_image(SAMPLE_WEBP, "package.webp")
    assert mime == "image/webp"
    assert ext == ".webp"


def test_detect_and_validate_image_failures():
    with pytest.raises(ValueError, match="empty"):
        detect_and_validate_image(EMPTY_BYTES, "empty.jpg")

    with pytest.raises(ValueError, match="Unsupported or invalid image file"):
        detect_and_validate_image(INVALID_TEXT, "fake.png")

    with pytest.raises(ValueError, match="Unsupported or invalid image file"):
        detect_and_validate_image(b"GIF89a\x01\x00\x01\x00", "anim.gif")


def test_calculate_sha256():
    hash_val = calculate_sha256(SAMPLE_JPEG)
    assert isinstance(hash_val, str)
    assert len(hash_val) == 64
    assert hash_val == calculate_sha256(SAMPLE_JPEG)
    assert hash_val != calculate_sha256(SAMPLE_PNG)


def test_local_storage_service(tmp_path):
    storage = LocalStorageService(tmp_path / "test_storage")
    filename, rel_path = storage.generate_storage_path("insp_123", ".jpg")

    assert "insp_123" in rel_path
    assert rel_path.endswith(".jpg")

    # Save
    saved_path = storage.save_file(rel_path, SAMPLE_JPEG)
    assert saved_path == rel_path
    assert storage.file_exists(rel_path) is True

    # Read
    content = storage.read_file(rel_path)
    assert content == SAMPLE_JPEG

    # Delete
    deleted = storage.delete_file(rel_path)
    assert deleted is True
    assert storage.file_exists(rel_path) is False

    # Read non-existent
    with pytest.raises(FileNotFoundError):
        storage.read_file(rel_path)


def test_path_traversal_prevention(tmp_path):
    storage = LocalStorageService(tmp_path / "test_storage")
    with pytest.raises(ValueError, match="Path traversal"):
        storage.save_file("../outside.txt", b"danger")

    with pytest.raises(ValueError, match="Path traversal"):
        storage.read_file("../../etc/passwd")

    with pytest.raises(ValueError, match="Path traversal"):
        storage._resolve_safe_path("..\\..\\windows\\system32\\calc.exe")

from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LABELSURE_", env_file=".env", extra="ignore", populate_by_name=True
    )
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./labelsure.db"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    jwt_secret: SecretStr | None = Field(default=None, validation_alias="JWT_SECRET")
    jwt_algorithm: Literal["HS256"] = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    max_upload_size_mb: int = Field(default=15, ge=1, le=100, validation_alias="MAX_UPLOAD_SIZE_MB")
    max_images_per_inspection: int = Field(default=20, ge=1, le=100, validation_alias="MAX_IMAGES_PER_INSPECTION")
    storage_local_dir: str = Field(default="storage", validation_alias="STORAGE_LOCAL_DIR")
    image_min_width: int = Field(default=800, ge=100, validation_alias="IMAGE_MIN_WIDTH")
    image_min_height: int = Field(default=600, ge=100, validation_alias="IMAGE_MIN_HEIGHT")
    blur_threshold: float = Field(default=100.0, ge=0.0, validation_alias="BLUR_THRESHOLD")
    brightness_low_threshold: float = Field(default=40.0, ge=0.0, validation_alias="BRIGHTNESS_LOW_THRESHOLD")
    brightness_high_threshold: float = Field(default=220.0, le=255.0, validation_alias="BRIGHTNESS_HIGH_THRESHOLD")
    contrast_threshold: float = Field(default=25.0, ge=0.0, validation_alias="CONTRAST_THRESHOLD")
    glare_pixel_threshold: int = Field(default=250, ge=0, le=255, validation_alias="GLARE_PIXEL_THRESHOLD")
    glare_ratio_threshold: float = Field(default=0.08, ge=0.0, le=1.0, validation_alias="GLARE_RATIO_THRESHOLD")
    image_pipeline_version: str = Field(default="1", validation_alias="IMAGE_PIPELINE_VERSION")
    ruleset_id: str = Field(default="LMPC-2026-RULES", min_length=1, max_length=64, validation_alias="RULESET_ID")
    ruleset_version: str = Field(default="1", min_length=1, max_length=32, validation_alias="RULESET_VERSION")
    rule_engine_version: str = Field(default="1", min_length=1, max_length=32, validation_alias="RULE_ENGINE_VERSION")
    rules_allow_prototypes: bool = Field(default=True, validation_alias="RULES_ALLOW_PROTOTYPES")
    context_pipeline_version: str = Field(default="1", min_length=1, max_length=32, validation_alias="CONTEXT_PIPELINE_VERSION")
    extraction_pipeline_version: str = Field(default="1", min_length=1, max_length=32, validation_alias="EXTRACTION_PIPELINE_VERSION")
    ocr_provider: str = Field(default="rapid", validation_alias="OCR_PROVIDER")
    ocr_pipeline_version: str = Field(default="1", validation_alias="OCR_PIPELINE_VERSION")
    ocr_language: str = Field(default="en", validation_alias="OCR_LANGUAGE")
    ocr_confidence_good: float = Field(default=0.85, ge=0.0, le=1.0, validation_alias="OCR_CONFIDENCE_GOOD")
    ocr_confidence_review: float = Field(default=0.60, ge=0.0, le=1.0, validation_alias="OCR_CONFIDENCE_REVIEW")
    paddleocr_use_gpu: bool = Field(default=False, validation_alias="PADDLEOCR_USE_GPU")
    paddleocr_enable_mkldnn: bool = Field(default=False, validation_alias="PADDLEOCR_ENABLE_MKLDNN")

    @model_validator(mode="after")
    def secure_jwt_configuration(self):
        if self.jwt_secret is not None and len(self.jwt_secret.get_secret_value().encode()) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 bytes; generate a random secret")
        if self.environment == "production" and self.jwt_secret is None:
            raise ValueError("JWT_SECRET is required in production")
        return self

    @field_validator("database_url")
    @classmethod
    def supported_database(cls, value: str) -> str:
        if make_url(value).drivername not in {"sqlite", "postgresql+psycopg"}:
            raise ValueError("Use sqlite or postgresql+psycopg")
        return value

    @field_validator("cors_origins")
    @classmethod
    def explicit_origins(cls, values: list[str]) -> list[str]:
        if any(v == "*" or not v.startswith(("http://", "https://")) for v in values):
            raise ValueError("CORS requires explicit HTTP(S) origins")
        return values

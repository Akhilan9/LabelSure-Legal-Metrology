import unicodedata
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class InspectorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_category: str | None = Field(default=None,max_length=100)
    package_type: Literal["PACKET","BOX","BOTTLE","JAR","CAN","POUCH","TUBE","CARTON","OTHER","UNKNOWN"] | None = None
    import_status: Literal["DOMESTIC","IMPORTED","UNKNOWN"] | None = None
    country_of_origin: str | None = Field(default=None,max_length=100)
    quantity_kind: Literal["WEIGHT","VOLUME","COUNT","LENGTH","AREA","UNKNOWN"] | None = None

    @field_validator("product_category","country_of_origin")
    @classmethod
    def safe_text(cls, value):
        if value is None:
            return value
        if any(unicodedata.category(c) in {"Cs","Cc","Cf"} for c in value):
            raise ValueError("Control characters and malformed Unicode are not allowed")
        value = unicodedata.normalize("NFKC",value).strip()
        if len(value)>100:
            raise ValueError("Value is too long")
        return value or None

class ResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inspector_input: InspectorInput | None = None


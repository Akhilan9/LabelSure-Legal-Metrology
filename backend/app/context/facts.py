import unicodedata
from app.models.context import FactType

PRESENCE = {
    "MRP": ("HAS_MRP_CANDIDATE","mrp"),
    "NET_QUANTITY": ("HAS_NET_QUANTITY_CANDIDATE","net_quantity"),
    "MANUFACTURER": ("HAS_MANUFACTURER_CANDIDATE","manufacturer"),
    "PACKER": ("HAS_PACKER_CANDIDATE","packer"),
    "IMPORTER": ("HAS_IMPORTER_CANDIDATE","importer"),
    "CONSUMER_CARE": ("HAS_CONSUMER_CARE_CANDIDATE","consumer_care"),
    "MONTH_YEAR": ("HAS_MONTH_YEAR_CANDIDATE","month_year"),
    "COMMON_PRODUCT_NAME": ("HAS_COMMON_NAME_CANDIDATE","common_name"),
    "COUNTRY_OF_ORIGIN": ("HAS_COUNTRY_OF_ORIGIN_CANDIDATE","country_of_origin"),
}
KEYS = {"PRODUCT_CATEGORY":"product.category","PACKAGE_TYPE":"package.type",
        "IMPORT_STATUS":"package.import_status","COUNTRY_OF_ORIGIN":"package.country_of_origin",
        "QUANTITY_KIND":"quantity.kind","OCR_EVIDENCE_AVAILABLE":"evidence.ocr_available",
        "OCR_CONFIDENCE_STATE":"evidence.ocr_confidence_state","DECLARATION_CONFLICT_PRESENT":"declaration.conflict_present"}
KEYS.update({fact:"declaration."+key+".detected" for fact,key in PRESENCE.values()})
FIELDS = {"product_category":"PRODUCT_CATEGORY","package_type":"PACKAGE_TYPE","import_status":"IMPORT_STATUS",
          "country_of_origin":"COUNTRY_OF_ORIGIN","quantity_kind":"QUANTITY_KIND"}
PACKAGES = {"PACKET","BOX","BOTTLE","JAR","CAN","POUCH","TUBE","CARTON","OTHER","UNKNOWN"}
CATEGORIES = {"FOOD","COSMETIC","HOUSEHOLD","PERSONAL_CARE","ELECTRONICS","OTHER","UNKNOWN"}

def safe(value):
    if value is None:
        return None
    return " ".join("".join(c if not unicodedata.category(c).startswith("C") else " "
                           for c in unicodedata.normalize("NFKC",str(value)[:2048])).split())

def normalize(kind, value):
    text = safe(value)
    if not text:
        return "UNKNOWN"
    upper = text.upper().replace(" ","_")
    if kind == "PRODUCT_CATEGORY":
        upper = {"COSMETICS":"COSMETIC","FOOD_&_BEVERAGES":"FOOD","FOOD_AND_BEVERAGES":"FOOD"}.get(upper,upper)
        return upper if upper in CATEGORIES else "OTHER"
    if kind == "PACKAGE_TYPE":
        return upper if upper in PACKAGES else "OTHER"
    if kind in {"IMPORT_STATUS","QUANTITY_KIND"}:
        return upper
    return text

def quantity_kind(unit):
    return {"g":"WEIGHT","kg":"WEIGHT","ml":"VOLUME","l":"VOLUME","count":"COUNT","pcs":"COUNT","pieces":"COUNT",
            "m":"LENGTH","cm":"LENGTH","mm":"LENGTH","m2":"AREA","m²":"AREA"}.get(safe(unit or "").lower(),"UNKNOWN")

def matching(candidates, prefix):
    return [c for c in candidates if c["declaration_type"] == prefix or c["declaration_type"].startswith(prefix+"_")]


import re
def rx(value):
    return re.compile(value, re.I)

MRP_LABEL = r"(?:m\.?\s*r\.?\s*p\.?|maximum\s+retail\s+price|retail\s+price(?:\s+maximum)?|max\.?\s*retail\s+price|max\.?\s*price)"
NET_LABEL = r"(?:net\s*(?:qty\.?|quantity|weight|content|contents|vol\.?|volume)|net\s+wt\.?)"
DATE_LABEL = r"(?:mfg\.?|mfd\.?|pkd\.?|pkg\.?|pkt\.?\s*dt\.?|pktdt|mfg\.?\s*dt\.?|mfd\.?\s*dt\.?|pkd\.?\s*dt\.?|packed(?:\s+on)?|manufactured(?:\s+on)?|imported(?:\s+on)?|date\s+of\s+pack(?:aging|ing)?|date\s+of\s+mfg|month\s*&\s*year\s+of\s+(?:manufacture|packing|import))"
CARE_LABEL = r"(?:consumer\s+care|customer\s+care|complaints|consumer\s+helpline|for\s*feedback|for\s+consumer\s+feedback|consumer\s+services|contact\s+customer\s+care|feedback/complaints|consumer\s+cell|addressabore|address\s+above)"
ORG_LABEL = r"(?:(?:manufactur\w*|manuta\w*|mfd\.?|mfg\.?)\s*(?:&|and)?\s*(?:packed|pkd\.?|marketed|mktd\.?)?\s*by|(?:marketed|mktd\.?)\s*by|marketedby|(?:packed|pkd\.?)\s*by|(?:imported|importer)\s*by|importer|manufactured\s+in\s+india\s+by|gujarat\s+co-operative|pepsico\s+india)"
ORIGIN_LABEL = r"(?:country\s+of\s+origin|made\s+in|imported\s+from|origin|produced\s+in)"
BOUNDARY = rx(r"\b(?:" + "|".join([MRP_LABEL, NET_LABEL, DATE_LABEL, CARE_LABEL, ORG_LABEL, ORIGIN_LABEL, r"barcode|gtin|unit\s+sale\s+price|product\s*name|item"]) + r")\b")

MRP = rx(r"\b" + MRP_LABEL + r"\s*[:=]?\s*(?:₹|rs\.?|inr)?\s*([0-9][0-9,]{0,14}(?:\.[0-9]{1,2})?)(?![0-9.])")
QUANTITY = rx(r"\b" + NET_LABEL + r"\s*[:=]?\s*(\d{1,9}(?:\.\d{1,4})?)\s*(grams|pieces|liters|litres|litre|liter|gms|ltr|pcs|gm|kg|ml|cm|m|g|l|n)\b")
DATE = rx(r"\b" + DATE_LABEL + r"\s*[:=]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}[/-]\d{2,4}|[A-Za-z]{3,9}\s+\d{4})(?!\d|[/-]\d)")
ORIGIN = rx(r"\b" + ORIGIN_LABEL + r"\s*[:=-]?\s*([A-Za-z][A-Za-z .'-]{1,70})")
ORG = rx(r"\b(" + ORG_LABEL + r")\s*[:=-]?\s*")
CARE = rx(r"\b" + CARE_LABEL + r"\s*[:=-]?\s*")
EMAIL = rx(r"(?<![\w.+-])[A-Z0-9._%+-]{1,64}@[A-Z0-9.-]{1,190}\.[A-Z]{2,24}\b")
PHONE = rx(r"(?<!\w)(\+?\d[\d ()-]{5,24}\d)(?!\w)")
GTIN = rx(r"\b(?:barcode|gtin(?:-?(?:8|12|13|14))?|ean|upc)\s*[:=-]?\s*([0-9]{8,14})\b")
PRODUCT = rx(r"\b(?:common\s+product\s*name|product\s*name|commodity|item(?:\s*name)?|product)\s*[:=-]\s*(.{2,160})")
UNIT_PRICE = rx(r"(?:\bunit\s+sale\s+price\s*[:=-]?\s*(?:₹|rs\.?|inr)?|(?:₹|rs\.?|inr))\s*(\d{1,9}(?:\.\d{1,2})?)\s*(?:/|per\s+)(?:(\d{1,4})\s*)?(kg|g|ml|l|piece|m|cm)\b")
OTHER = rx(r"\bother\s+declaration\s*:\s*(.{2,160})")

EXPIRY = rx(r"\b(?:expiry(?:\s*(?:date|dt\.?))?|exp(?:\.|\s*dt\.?)?|expires?|use\s*by|best\s+before)\s*[:=-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}[/-]\d{4}|[A-Za-z]{3,9}\s+\d{4}|\d{1,3}\s*(?:months?|days?|years?)\s+from\s+(?:manufactur\w+|pack\w+))\b")
DIMENSIONS = rx(r"\b(?:dimensions?|size|length|width)\s*[:=-]?\s*(\d+(?:\.\d+)?(?:\s*[x×]\s*\d+(?:\.\d+)?){0,2}\s*(?:mm|cm|m|inches?|ft))\b")
SELLER = rx(r"\b(?:sold\s+by|seller(?:\s+name)?|marketed\s+by)\s*[:=-]\s*(.{2,160})")

STANDALONE_MRP = rx(r"(?:₹|rs\.?|inr)\s*([0-9][0-9,]{0,14}(?:\.[0-9]{1,2})?)(?!\d)")
STANDALONE_QUANTITY = rx(r"\b(\d{1,9}(?:\.\d{1,4})?)\s*(grams|pieces|liters|litres|litre|liter|gms|ltr|pcs|gm|kg|ml|cm|m|g|l|n)\b")



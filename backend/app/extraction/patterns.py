import re
def rx(value):
    return re.compile(value, re.I)

MRP_LABEL = r"(?:m\.?\s*r\.?\s*p\.?(?:\s*\([^)]*\))?|maximum\s+retail\s+price|retail\s+price(?:\s+maximum)?|max\.?\s*retail\s+price|max\.?\s*price|all\s+taxes\)?|incl\.?\s+of\s+all\s+taxes|price)"
NET_LABEL = r"(?:net\s*(?:qty\.?|quantity|weight|content|contents|vol\.?|volume)|net\s+wt\.?|net\s*w\b)"
DATE_LABEL = r"(?:mfg\.?|mfd\.?|pkd\.?|pkg\.?|pkt\.?\s*dt\.?|pktdt|mfg\.?\s*dt\.?|mfd\.?\s*dt\.?|pkd\.?\s*dt\.?|packed(?:\s+on)?|manufactured(?:\s+on)?|imported(?:\s+on)?|date\s+of\s+pack(?:aging|ing)?|date\s+of\s+mfg|date\s+of\s+mfd|date\s+of\s+pkd|month\s*&\s*year\s+of\s+(?:manufacture|packing|import)|mfd|mfg|pkd|pkg)"
CARE_LABEL = r"(?:consumer\s+care|customer\s+care|complaints|consumer\s+helpline|for\s*feedback|for\s+consumer\s+feedback|consumer\s+services|contact\s+customer\s+care|feedback/complaints|consumer\s+cell|addressabore|address\s+above|tol\s*free(?:\s*no\.?)?|toll\s*free(?:\s*no\.?)?|toll-free|helpline|customer\s+relation(?:s)?(?:\s+officer)?|call\s+customer|customer\s+helpline|phone\s*no\.?|contact\s*no\.?|call\s*us|tel\s*no\.?)"
ORG_LABEL = r"(?:(?:mfd\.?|mfg\.?|mid\.?|mig\.?|mfd|mfg|mid|manufactur\w*|manuta\w*|actured|nufactured|anufactured)\s*(?:&|and)?\s*(?:packed|pkd\.?|marketed|mktd\.?)?\s*by|(?:marketed|mktd\.?|mkt\.?|mkt)\s*by|marketedby|(?:packed|pkd\.?|pkg\.?)\s*by|(?:imported|importer)\s*by|importer|manufactured\s+in\s+india\s+by|fabrique\s*par|gujarat\s+co-operative|pepsico\s+india)"
ORIGIN_LABEL = r"(?:country\s+of\s+origin|made\s+in|imported\s+from|origin|produced\s+in)"
BOUNDARY = rx(r"\b(?:" + "|".join([MRP_LABEL, NET_LABEL, DATE_LABEL, CARE_LABEL, ORG_LABEL, ORIGIN_LABEL, r"barcode|gtin|unit\s+sale\s+price|product\s*name|item|lic\.?\s*no\.?|fssai"]) + r")\b")

MRP = rx(r"\b" + MRP_LABEL + r"\s*[:=]?\s*(?:₹|rs\.?|inr)?\s*([0-9][0-9,]{0,14}(?:\.[0-9]{1,2})?)(?![0-9.])")
COMPOUND_PRICE = rx(r"(?:(?:₹|rs\.?|inr)\s*([0-9]+(?:\.[0-9]{1,2})?)\s*(?:/|\()\s*(?:₹|rs\.?|inr)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:/|per\s+)?(g|gm|gms|kg|ml|l|ltr|pcs|piece|cm|m)?\b|([0-9]+\.[0-9]{2})\s*(?:/|\()\s*(?:₹|rs\.?|inr)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:/|per\s+)?(g|gm|gms|kg|ml|l|ltr|pcs|piece|cm|m)?\b)")
QUANTITY = rx(r"\b" + NET_LABEL + r"\s*[:=]?\s*(\d{1,9}(?:\.\d{1,4})?)\s*(grams|pieces|liters|litres|litre|liter|gms|ltr|pcs|gm|kg|ml|cm|m|g|l|n)\b")
DATE = rx(r"\b" + DATE_LABEL + r"\s*[:=]?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{1,2}[/.-]\d{2,4}|[A-Za-z0-9]{3,9}\s*\d{2,4})(?!\d|[/-]\d)")
ORIGIN = rx(r"\b" + ORIGIN_LABEL + r"\s*[:=-]?\s*([A-Za-z][A-Za-z .'-]{1,70})")
ORG = rx(r"\b(" + ORG_LABEL + r")\s*[:=-]?\s*")
CARE = rx(r"\b" + CARE_LABEL + r"\s*[:=-]?\s*")
EMAIL = rx(r"(?<![\w.+-])[A-Z0-9._%+-]{1,64}@[A-Z0-9.-]{1,190}\.[A-Z]{2,24}\b")
PHONE = rx(r"(?:(?:toll\s*free(?:\s*no\.?)?|tol\s*free(?:\s*no\.?)?|helpline|call|phone|tel|contact|care)\s*[:=.-]?\s*)?(\b1800[- ]?\d{3}[- ]?\d{3,4}\b|\b1800\s*\d{6,7}\b|\+?91[- ]?[6-9]\d{9}\b|(?<!\w)\b[6-9]\d{9}\b|(?<!\w)\+?\d[\d ()-]{6,16}\d(?!\w))")
GTIN = rx(r"\b(?:barcode|gtin(?:-?(?:8|12|13|14))?|ean|upc)\s*[:=-]?\s*([0-9]{8,14})\b")
PRODUCT = rx(r"\b(?:common\s+product\s*name|product\s*name|commodity|item(?:\s*name)?|product)\s*[:=-]\s*(.{2,160})")
UNIT_PRICE = rx(r"(?:\bunit\s+sale\s+price\s*[:=-]?\s*(?:₹|rs\.?|inr)?|(?:₹|rs\.?|inr))\s*(\d{1,9}(?:\.\d{1,2})?)\s*(?:/|per\s+)(?:(\d{1,4})\s*)?(kg|g|ml|l|piece|m|cm)\b")
OTHER = rx(r"\bother\s+declaration\s*:\s*(.{2,160})")

FSSAI = rx(r"\b(?:fssai(?:\s*lic\.?\s*(?:no\.?|number)?)?|lic\.?\s*no\.?|license\s*no\.?)\s*[:=.-]?\s*([12]\d{13})\b")
STANDALONE_FSSAI = rx(r"\b([12]\d{13})\b")

EXPIRY = rx(r"\b(?:expiry(?:\s*(?:date|dt\.?))?|exp(?:\.|\s*dt\.?)?|expires?|use\s*by|best\s+before)\s*[:=-]?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{1,2}[/.-]\d{2,4}|[A-Za-z0-9]{3,9}\s*\d{2,4}|\d{1,3}\s*(?:months?|days?|years?)\s+from\s+(?:manufactur\w+|pack\w+))\b")
DIMENSIONS = rx(r"\b(?:dimensions?|size|length|width)\s*[:=-]?\s*(\d+(?:\.\d+)?(?:\s*[x×]\s*\d+(?:\.\d+)?){0,2}\s*(?:mm|cm|m|inches?|ft))\b")
SELLER = rx(r"\b(?:sold\s+by|seller(?:\s+name)?|marketed\s+by)\s*[:=-]\s*(.{2,160})")

STANDALONE_MRP = rx(r"(?:₹|rs\.?|inr)\s*([0-9][0-9,]{0,14}(?:\.[0-9]{1,2})?)(?!\d)")
STANDALONE_QUANTITY = rx(r"\b(\d{1,9}(?:\.\d{1,4})?)\s*(grams|pieces|liters|litres|litre|liter|gms|ltr|pcs|gm|kg|ml|cm|m|g|l|n)\b")
POSTAL_ADDRESS = rx(r"\b(?:plot\s*(?:no\.?)?|road|street|nagar|vihar|phase|sector|lane|estate|complex|building|bldg|khasra|sy\.?\s*no\.?|survey\s*no\.?|village|industrial\s+area|gidc|midc|dist\.?|district|taluk|taluka|nh[- ]?\d+|highway|near|opp\.?|opposite)\b.*?(?:[A-Za-z]+[- ]?\d{6}\b|\b[1-9]\d{5}\b|hyderabad|mumbai|delhi|bengaluru|chennai|kolkata|pune|noida|gujarat|telangana|andhra|karnataka|maharashtra|tamil\s+nadu|haryana|uttar\s+pradesh|india)")
PINCODE_ONLY = rx(r"\b(?:[A-Za-z\s]{3,30})[- ,]+([1-9]\d{5})\b")




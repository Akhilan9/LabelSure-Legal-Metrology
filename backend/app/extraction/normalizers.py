import re
import unicodedata
from decimal import Decimal, InvalidOperation

MAX_TEXT = 2048

def clean(text):
    text = unicodedata.normalize("NFKC", text[:MAX_TEXT])
    return " ".join("".join(c if not unicodedata.category(c).startswith("C") else " " for c in text).split())

def money(value):
    try:
        amount = Decimal(value.replace(",", ""))
        if not amount.is_finite() or amount <= 0 or amount > 1000000000:
            return None
        return {"amount": format(amount, ".2f"), "currency": "INR"}
    except InvalidOperation:
        return None

UNITS = {"gm": "g", "gms": "g", "grams": "g", "gram": "g", "g": "g",
         "kg": "kg", "ml": "ml", "l": "L", "ltr": "L", "litre": "L",
         "litres": "L", "liter": "L", "liters": "L", "pcs": "count",
         "pieces": "count", "n": "count", "cm": "cm", "m": "m"}

def quantity(number, unit):
    value = Decimal(number)
    if value <= 0:
        return None
    return {"numeric_value": format(value.normalize(), "f"), "unit": UNITS[unit.lower()]}

def month_year(value):
    val = value.strip().replace(".", "/")
    match_3 = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2}|\d{4})", val)
    if match_3:
        p1, p2, p3 = int(match_3[1]), int(match_3[2]), match_3[3]
        year = int(p3) if len(p3) == 4 else (2000 + int(p3))
        if 1 <= p2 <= 12 and p1 > 12:
            return {"day": p1, "month": p2, "year": year}, len(p3) == 2
        if 1 <= p1 <= 12 and p2 > 12:
            return {"day": p2, "month": p1, "year": year}, len(p3) == 2
        if 1 <= p1 <= 12 and 1 <= p2 <= 12:
            return {"day": p1, "month": p2, "year": year}, True
        return {}, True
    match = re.fullmatch(r"(\d{1,2})[/-](\d{2}|\d{4})", val)
    if match:
        month = int(match[1])
        y_str = match[2]
        if not 1 <= month <= 12:
            return {}, True
        year = int(y_str) if len(y_str) == 4 else (2000 + int(y_str))
        return {"month": month, "year": year, "year_text": y_str}, len(y_str) == 2
    match = re.fullmatch(r"([A-Za-z0-9]{3,9})\s*(\d{2,4})", val)
    if match:
        months_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
            "dct": 10, "dce": 12, "au6": 8, "jui": 7, "0ct": 10, "1an": 1,
            "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        }
        name = match[1].lower()
        m_num = months_map.get(name) or months_map.get(name[:3])
        if m_num:
            y_str = match[2]
            year = int(y_str) if len(y_str) == 4 else (2000 + int(y_str))
            return {"month": m_num, "year": year, "year_text": y_str}, len(y_str) == 2
    return {}, True

def valid_gtin(value):
    if len(value) not in {8, 12, 13, 14} or not value.isascii() or not value.isdigit():
        return False
    total = sum(int(n) * (3 if i % 2 == 0 else 1) for i, n in enumerate(reversed(value[:-1])))
    return (10 - total % 10) % 10 == int(value[-1])


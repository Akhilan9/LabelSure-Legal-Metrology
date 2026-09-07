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
    match_3 = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2}|\d{4})", value.strip())
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
    match = re.fullmatch(r"(\d{1,2})[/-](\d{2}|\d{4})", value.strip())
    if match:
        month, year = map(int, match.groups())
        if not 1 <= month <= 12:
            return {}, True
        # A two-digit year has an unresolved century.
        return {"month": month, "year": year if len(match[2]) == 4 else None, "year_text": match[2]}, len(match[2]) == 2
    match = re.fullmatch(r"([A-Za-z]{3,9})\s+(\d{4})", value.strip())
    if match:
        months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        full = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        name = match[1].lower()
        if name in months or name in full:
            return {"month": months.index(name[:3]) + 1, "year": int(match[2])}, False
    return {}, True

def valid_gtin(value):
    if len(value) not in {8, 12, 13, 14} or not value.isascii() or not value.isdigit():
        return False
    total = sum(int(n) * (3 if i % 2 == 0 else 1) for i, n in enumerate(reversed(value[:-1])))
    return (10 - total % 10) % 10 == int(value[-1])


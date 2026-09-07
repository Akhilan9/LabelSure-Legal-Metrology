"""
Standard Legal Metrology Guideline Failure Justifications
per the Legal Metrology (Packaged Commodities) Rules, 2011–2026 and
Section 36(1) of the Legal Metrology Act, 2009.
"""

from typing import Any

LM_RULE_JUSTIFICATION_MAP: dict[str, dict[str, str]] = {
    # 1. Common / Generic Name
    "COMMON_NAME": {
        "code": "LM-0001",
        "pcr_clause": "Rule 6(1)(a)",
        "declaration": "Generic or Common Name of the commodity",
        "description": "Generic or Common Name of the commodity. is missing from the package label.",
    },
    "COMMON_NAME_PRESENCE": {
        "code": "LM-0001",
        "pcr_clause": "Rule 6(1)(a)",
        "declaration": "Generic or Common Name of the commodity",
        "description": "Generic or Common Name of the commodity. is missing from the package label.",
    },

    # 2. Manufacturer / Packer / Importer Name & Postal Address
    "MANUFACTURER": {
        "code": "LM-0002",
        "pcr_clause": "Rule 6(1)(b)",
        "declaration": "Complete Name and Postal Address of Manufacturer / Packer / Importer",
        "description": "Complete Name and Postal Address of Manufacturer / Packer / Importer. is missing from the package label.",
    },
    "MANUFACTURER_PRESENCE": {
        "code": "LM-0002",
        "pcr_clause": "Rule 6(1)(b)",
        "declaration": "Complete Name and Postal Address of Manufacturer / Packer / Importer",
        "description": "Complete Name and Postal Address of Manufacturer / Packer / Importer. is missing from the package label.",
    },
    "PACKER_IMPORTER": {
        "code": "LM-0002",
        "pcr_clause": "Rule 6(1)(b)",
        "declaration": "Complete Name and Postal Address of Manufacturer / Packer / Importer",
        "description": "Complete Name and Postal Address of Manufacturer / Packer / Importer. is missing from the package label.",
    },
    "PACKER_PRESENCE": {
        "code": "LM-0002",
        "pcr_clause": "Rule 6(1)(b)",
        "declaration": "Complete Name and Postal Address of Manufacturer / Packer / Importer",
        "description": "Complete Name and Postal Address of Manufacturer / Packer / Importer. is missing from the package label.",
    },
    "IMPORTER_PRESENCE": {
        "code": "LM-0002",
        "pcr_clause": "Rule 6(1)(b)",
        "declaration": "Complete Name and Postal Address of Manufacturer / Packer / Importer",
        "description": "Complete Name and Postal Address of Manufacturer / Packer / Importer. is missing from the package label.",
    },

    # 3. Net Quantity
    "NET_QUANTITY": {
        "code": "LM-0003",
        "pcr_clause": "Rule 6(1)(c)",
        "declaration": "Net Quantity declaration in standard units of weight, measure or number",
        "description": "Net Quantity in standard units of weight, measure or number (g/kg/ml/L/units). is missing or non-compliant.",
    },
    "NET_QUANTITY_STRUCTURE": {
        "code": "LM-0003",
        "pcr_clause": "Rule 6(1)(c)",
        "declaration": "Net Quantity declaration in standard units of weight, measure or number",
        "description": "Net Quantity in standard units of weight, measure or number (g/kg/ml/L/units). is missing or non-compliant.",
    },

    # 4. Maximum Retail Price (MRP)
    "MRP": {
        "code": "LM-0004",
        "pcr_clause": "Rule 6(1)(d)",
        "declaration": "Maximum Retail Price (MRP inclusive of all taxes)",
        "description": "Maximum Retail Price (MRP inclusive of all taxes). is missing or incorrectly formatted.",
    },
    "MRP_PRESENCE": {
        "code": "LM-0004",
        "pcr_clause": "Rule 6(1)(d)",
        "declaration": "Maximum Retail Price (MRP inclusive of all taxes)",
        "description": "Maximum Retail Price (MRP inclusive of all taxes). is missing or incorrectly formatted.",
    },

    # 5. Month & Year of Manufacture / Packing / Import
    "PACKING_DATE": {
        "code": "LM-0005",
        "pcr_clause": "Rule 6(1)(e)",
        "declaration": "Month and Year of manufacture, packing, or import (MM/YYYY)",
        "description": "Month and Year of manufacture, packing, or import (MM/YYYY). is missing from the package label.",
    },
    "MONTH_YEAR_STRUCTURE": {
        "code": "LM-0005",
        "pcr_clause": "Rule 6(1)(e)",
        "declaration": "Month and Year of manufacture, packing, or import (MM/YYYY)",
        "description": "Month and Year of manufacture, packing, or import (MM/YYYY). is missing from the package label.",
    },

    # 6. Country of Origin
    "ORIGIN": {
        "code": "LM-0006",
        "pcr_clause": "Rule 6(1)(f)",
        "declaration": "Country of Origin for imported commodity",
        "description": "Country of Origin for imported commodity. is missing from the package label.",
    },
    "ORIGIN_PRESENCE": {
        "code": "LM-0006",
        "pcr_clause": "Rule 6(1)(f)",
        "declaration": "Country of Origin for imported commodity",
        "description": "Country of Origin for imported commodity. is missing from the package label.",
    },

    # 7. Consumer Care Cell Contact Details
    "CONSUMER_CARE": {
        "code": "LM-0007",
        "pcr_clause": "Rule 6(1)(g)",
        "declaration": "Consumer Care Cell contact details (Name, Address, Helpline Phone, Email)",
        "description": "Consumer Care Cell contact details (Name, Address, Helpline Phone, Email). is missing or non-compliant.",
    },
    "CONSUMER_CONTACT_DEMO": {
        "code": "LM-0007",
        "pcr_clause": "Rule 6(1)(g)",
        "declaration": "Consumer Care Cell contact details (Name, Address, Helpline Phone, Email)",
        "description": "Consumer Care Cell contact details (Name, Address, Helpline Phone, Email). is missing or non-compliant.",
    },

    # 8. Unit Sale Price (USP)
    "UNIT_PRICE": {
        "code": "LM-0008",
        "pcr_clause": "Rule 6(1)(h)",
        "declaration": "Unit Sale Price (USP) per g/kg/ml/L for products > 1kg/1L or > 1 unit",
        "description": "Unit Sale Price (USP) per g/kg/ml/L for products > 1kg/1L or > 1 unit. is missing from the package label.",
    },

    # 9. Expiry / Best Before
    "EXPIRY": {
        "code": "LM-0009",
        "pcr_clause": "Rule 6(1)(da)",
        "declaration": "Best Before / Use By / Expiry date for perishable commodity",
        "description": "Best Before / Use By / Expiry date for perishable commodity. is missing from the package label.",
    },

    # 10. Dimensions / Size
    "DIMENSIONS": {
        "code": "LM-0010",
        "pcr_clause": "Rule 6(1)(n)",
        "declaration": "Dimension or Size of the commodity",
        "description": "Dimension or Size of the commodity (length, width, height, radius). is missing from the package label.",
    },

    # 11. E-Commerce
    "ECOMMERCE": {
        "code": "LM-0011",
        "pcr_clause": "Rule 6(10)",
        "declaration": "E-Commerce statutory declarations",
        "description": "E-Commerce statutory declarations under Rule 6(10). is missing or non-compliant.",
    },
}

PENALTY_JUSTIFICATION = (
    "[LM-0016 Violation]: PCR Rule 6(1) FAIL [Rule 32 Violation]: "
    "Penalties for non-compliance under Section 36(1) of Legal Metrology Act, 2009. "
    "is missing or non-compliant."
)


TOKEN_TO_LM_MAP: list[tuple[set[str], str]] = [
    ({"COMMON_NAME", "GENERIC_NAME", "COMMON"}, "COMMON_NAME"),
    ({"MFG", "MANUFACTURER", "PACKER", "IMPORTER"}, "MANUFACTURER"),
    ({"NETQTY", "NET_QUANTITY", "QUANTITY", "NETWEIGHT", "NET_WEIGHT"}, "NET_QUANTITY"),
    ({"MRP", "PRICE", "RETAIL_PRICE"}, "MRP"),
    ({"DATE", "PACKING_DATE", "MONTH_YEAR", "MFG_DATE", "PACK_DATE"}, "PACKING_DATE"),
    ({"ORIGIN", "COUNTRY_OF_ORIGIN", "IMPORT_ORIGIN"}, "ORIGIN"),
    ({"CARE", "CONSUMER_CARE", "CUSTOMER_CARE", "HELPLINE", "CONTACT"}, "CONSUMER_CARE"),
    ({"USP", "UNIT_PRICE", "UNIT_SALE_PRICE"}, "UNIT_PRICE"),
    ({"EXPIRY", "EXPIRY_DATE", "BEST_BEFORE", "USE_BY"}, "EXPIRY"),
    ({"DIMENSIONS", "DIMENSION", "SIZE"}, "DIMENSIONS"),
    ({"ECOMMERCE", "E_COMMERCE"}, "ECOMMERCE"),
]


def generate_failure_justifications(failed_rules: list[Any]) -> list[str]:
    """
    Given a list of failed rule evaluations (dicts, objects, or rule key strings),
    generates standard formatted Legal Metrology Guideline Failure Justifications.
    """
    if not failed_rules:
        return []

    justifications: list[str] = []
    seen_codes: set[str] = set()

    for item in failed_rules:
        if isinstance(item, str):
            key = item
        elif isinstance(item, dict):
            key = str(item.get("rule_key") or item.get("rule_id") or "")
        else:
            key = str(getattr(item, "rule_key", None) or getattr(item, "rule_id", None) or "")

        clean_key = key.upper().replace("-", "_")
        tokens = set(clean_key.split("_"))

        matched = False

        # 1. Direct or token match in TOKEN_TO_LM_MAP
        for token_set, canonical_key in TOKEN_TO_LM_MAP:
            if (token_set & tokens) or any(t in clean_key for t in token_set):
                mapping = LM_RULE_JUSTIFICATION_MAP[canonical_key]
                code = mapping["code"]
                if code not in seen_codes:
                    seen_codes.add(code)
                    justifications.append(
                        f"[{mapping['code']} Violation]: PCR Rule 6(1) FAIL [{mapping['pcr_clause']} Violation]: {mapping['description']}"
                    )
                matched = True
                break

        # 2. Check full dictionary keys
        if not matched:
            for map_key, mapping in LM_RULE_JUSTIFICATION_MAP.items():
                if map_key in clean_key or clean_key in map_key:
                    code = mapping["code"]
                    if code not in seen_codes:
                        seen_codes.add(code)
                        justifications.append(
                            f"[{mapping['code']} Violation]: PCR Rule 6(1) FAIL [{mapping['pcr_clause']} Violation]: {mapping['description']}"
                        )
                    matched = True
                    break

        # 3. Deterministic fallback for unmapped rules
        if not matched and clean_key:
            code_num = abs(hash(clean_key)) % 899 + 12
            code = f"LM-00{code_num:02d}" if code_num < 100 else f"LM-0{code_num:03d}"
            if code not in seen_codes:
                seen_codes.add(code)
                justifications.append(
                    f"[{code} Violation]: PCR Rule 6(1) FAIL [Rule 6(1) Violation]: Mandatory statutory declaration for {key}. is missing or non-compliant."
                )

    # If any violation occurred, always append the Section 36(1) penalty justification
    if justifications and "LM-0016" not in seen_codes:
        justifications.append(PENALTY_JUSTIFICATION)

    return justifications


def format_failure_justifications(justifications: list[str]) -> str:
    """Formats list of justifications into user's requested block layout with heading."""
    if not justifications:
        return ""
    return "Legal Metrology Guideline Failure Justifications\n" + "\n".join(justifications)

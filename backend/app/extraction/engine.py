"""Bounded deterministic pattern and spatial-context extraction."""
import re
from app.extraction import patterns as p
from app.extraction.normalizers import clean, money, quantity, month_year, valid_gtin
from app.extraction.spatial import neighbors, nearby
from app.extraction.scoring import score

def extract(blocks, panel, product_name=None):
    results = []
    seen = set()
    def emit(kind, sources, value, structured=None, review=False, heuristic=False, reason=None):
        if not value or not sources:
            return
        key = (kind, tuple(b.id for b in sources), value)
        if key in seen:
            return
        seen.add(key)
        confidence, factors = score(sources, valid=not review, heuristic=heuristic,
                                    relevant_panel=panel in {"MRP_PANEL", "DECLARATION_PANEL", "BACK"})
        reasons = ([reason] if reason else []) + (["Low extraction confidence"] if confidence < .80 else [])
        if heuristic:
            reasons.append("Heuristic interpretation")
        results.append(dict(declaration_type=kind, sources=sources,
            raw_value="\n".join(b.raw_text for b in sources), normalized_value=value[:2048],
            structured_value=structured or {}, confidence_score=confidence, confidence_factors=factors,
            extraction_method="MULTI_BLOCK" if len(sources) > 1 else "KEYWORD_CONTEXT",
            needs_review=review or heuristic or confidence < .80, review_reasons=reasons))

    # Global Email & Phone extraction for explicit customer care numbers/emails across ALL blocks
    for block in blocks:
        text_raw = block.raw_text
        text_cln = clean(text_raw)
        if p.CARE.search(text_cln) or re.search(r"customercare|consumer\s+helpline|for\s+feedback|consumer\s+care|addressabore|address\s+above|consumer|customer", text_cln, re.I):
            for match in p.EMAIL.finditer(text_raw):
                emit("CONSUMER_CARE_EMAIL", [block], match[0].lower())
            for match in p.PHONE.finditer(text_raw):
                digits = re.sub(r"\D", "", match[1])
                if 7 <= len(digits) <= 15:
                    emit("CONSUMER_CARE_PHONE", [block], ("+" if match[1].startswith("+") else "") + digits)

    # Document-Level Sliding Window Concatenation Pass with Spatial Proximity Check
    def block_pos(b):
        box = getattr(b, 'bounding_box', {}) or {}
        return (box.get('y_min', 0), box.get('x_min', 0))

    sorted_blocks = sorted(blocks, key=block_pos)
    for window_size in [2, 3, 4]:
        for i in range(len(sorted_blocks) - window_size + 1):
            window_src = sorted_blocks[i:i+window_size]
            spatially_valid = True
            for k in range(len(window_src) - 1):
                if not nearby(window_src[k], window_src[k+1]):
                    spatially_valid = False
                    break
            if not spatially_valid:
                continue

            first_text = clean(window_src[0].raw_text)
            if p.BOUNDARY.search(first_text) and not any(pat.search(first_text) for pat in [p.MRP, p.QUANTITY, p.DATE, p.GTIN]):
                joined_text = " ".join(clean(b.raw_text) for b in window_src)

                # MRP in window
                for match in p.MRP.finditer(joined_text):
                    data = money(match[1])
                    if data:
                        emit("MRP", window_src, data["amount"], data)

                # Net Quantity in window
                for match in p.QUANTITY.finditer(joined_text):
                    data = quantity(match[1], match[2])
                    if data:
                        emit("NET_QUANTITY", window_src, data["numeric_value"] + " " + data["unit"], data)

                # Date in window
                for match in p.DATE.finditer(joined_text):
                    data, review = month_year(match[1])
                    value = f'{data["year"]:04d}-{data["month"]:02d}' if data.get("year") else match[1]
                    emit("MONTH_YEAR", window_src, value, data, review=review)

                # Organization / Manufacturer in window
                org_w = p.ORG.search(joined_text)
                if org_w:
                    role = "MANUFACTURER" if re.search(r"manufactured|mfd|mfg|gujarat", org_w[1], re.I) else "PACKER" if re.search(r"packed|pkd", org_w[1], re.I) else "IMPORTER"
                    tail = joined_text[org_w.end():].strip()
                    if tail and re.search(r"[A-Za-z]{2}", tail):
                        parts = re.split(r",\s*(?=\d)", tail, maxsplit=1)
                        emit(role + "_NAME", window_src, parts[0], heuristic=True)
                        if len(parts) > 1:
                            emit(role + "_ADDRESS", window_src, parts[1], heuristic=True)

    # Individual Block Scanning Pass
    for index, block in enumerate(blocks):
        text = clean(block.raw_text)
        group = neighbors(blocks, index, p.BOUNDARY, clean)
        # Only join the immediate value neighbor for scalar labels.
        scalar_sources = [block]
        scalar = text
        if p.BOUNDARY.search(text) and len(group) > 1:
            scalar_sources = group[:2]
            scalar = " ".join(clean(b.raw_text) for b in scalar_sources)
        for pattern, kind in [(p.MRP, "MRP"), (p.QUANTITY, "NET_QUANTITY"),
                              (p.DATE, "MONTH_YEAR"), (p.ORIGIN, "COUNTRY_OF_ORIGIN"),
                              (p.GTIN, "BARCODE_OR_GTIN"), (p.UNIT_PRICE, "UNIT_SALE_PRICE")]:
            matches = list(pattern.finditer(text))
            sources = [block]
            if not matches:
                matches = list(pattern.finditer(scalar))
                sources = scalar_sources
            for match in matches:
                if kind == "MRP":
                    data = money(match[1])
                    if data:
                        emit(kind, sources, data["amount"], data)
                elif kind == "NET_QUANTITY":
                    data = quantity(match[1], match[2])
                    if data:
                        emit(kind, sources, data["numeric_value"] + " " + data["unit"], data)
                elif kind == "MONTH_YEAR":
                    data, review = month_year(match[1])
                    value = f'{data["year"]:04d}-{data["month"]:02d}' if data.get("year") else match[1]
                    emit(kind, sources, value, data, review=review, reason="Ambiguous date" if review else None)
                elif kind == "COUNTRY_OF_ORIGIN":
                    value = p.BOUNDARY.split(match[1])[0].strip(" .,:;-")
                    if value and len(value.split()) <= 6:
                        emit(kind, sources, value, {"country_text": value}, heuristic=True)
                elif kind == "BARCODE_OR_GTIN":
                    if valid_gtin(match[1]):
                        emit(kind, sources, match[1], {"gtin": match[1], "check_digit_valid": True})
                else:
                    data = money(match[1])
                    if data:
                        data["per_unit"] = match[3].lower()
                        data["per_quantity"] = match[2] or "1"
                        if int(data["per_quantity"]) > 0:
                            emit(kind, sources, data["amount"] + "/" + (match[2] or "") + data["per_unit"], data)
        org = p.ORG.search(text)
        if org:
            role = "MANUFACTURER" if re.search(r"manufactur\w*|manuta\w*|mfd|mfg|marketed", org[1], re.I) else "PACKER" if re.search(r"packed|pkd", org[1], re.I) else "IMPORTER"
            tail = text[org.end():].strip()
            name_sources = [block]
            address_blocks = group[1:]
            if not tail and len(group) > 1:
                tail = clean(group[1].raw_text)
                name_sources = group[:2]
                address_blocks = group[2:]
            if tail and re.search(r"[A-Za-z]{2}", tail):
                # Separate explicit comma-delimited organization/address when possible.
                parts = re.split(r",\s*(?=\d)", tail, maxsplit=1)
                if not re.fullmatch(r"(?:manufactur\w*|manuta\w*|mfd|mfg|packed|pkd|marketed|mktd|importer?|by|\s|&|:)+", parts[0], re.I):
                    emit(role + "_NAME", name_sources, parts[0], heuristic=True)
                if len(parts) > 1:
                    emit(role + "_ADDRESS", name_sources, parts[1], heuristic=True)
            if address_blocks:
                emit(role + "_ADDRESS", [block] + address_blocks,
                     " ".join(clean(b.raw_text) for b in address_blocks), heuristic=True)
        # Postal address detection for statutory manufacturer / packer address
        if re.search(r"\b(?:plot\s*no\.?|road|street|nagar|estate|sector|lane|industrial\s+area)\b.*?(?:hyderabad|mumbai|delhi|bengaluru|chennai|kolkata|pune|gujarat|[A-Za-z]+-\d{2,6}|\b\d{6}\b)", text, re.I):
            emit("MANUFACTURER_ADDRESS", [block], text, heuristic=True)
        care = p.CARE.search(text)
        if care:
            care_blocks = group
            for item in care_blocks:
                line = clean(item.raw_text)
                sources = [block] if item.id == block.id else [block, item]
                for match in p.EMAIL.finditer(line):
                    emit("CONSUMER_CARE_EMAIL", sources, match[0].lower())
                for match in p.PHONE.finditer(line):
                    digits = re.sub(r"\D", "", match[1])
                    if 7 <= len(digits) <= 15:
                        emit("CONSUMER_CARE_PHONE", sources, ("+" if match[1].startswith("+") else "") + digits)
            residual = []
            for item in care_blocks:
                line = clean(item.raw_text)
                if item.id == block.id:
                    line = line[care.end():]
                if p.EMAIL.search(line) or p.PHONE.search(line):
                    continue
                line = re.sub(r"^(?:name|address)\s*:\s*", "", line, flags=re.I).strip()
                if line:
                    residual.append((item, line))
            if residual:
                first, value = residual[0]
                address_first = bool(re.search(r"\d|\bstreet\b|\broad\b|\bestate\b", value, re.I))
                if not address_first:
                    emit("CONSUMER_CARE_NAME", list({b.id:b for b in [block, first]}.values()), value, heuristic=True)
                    residual = residual[1:]
                if residual:
                    emit("CONSUMER_CARE_ADDRESS", list({b.id:b for b in [block] + [r[0] for r in residual]}.values()),
                         " ".join(r[1] for r in residual), heuristic=True)
        for pattern, kind in [(p.EXPIRY, "EXPIRY_DATE"), (p.DIMENSIONS, "DIMENSIONS"), (p.SELLER, "ECOMMERCE_SELLER")]:
            found = pattern.search(text)
            if found:
                emit(kind, [block], found[1], heuristic=True)
        product = p.PRODUCT.search(text)
        if product:
            emit("COMMON_PRODUCT_NAME", [block], product[1], heuristic=True)
        elif panel == "FRONT" and product_name and clean(product_name).casefold() == text.casefold() and not p.BOUNDARY.search(text):
            emit("COMMON_PRODUCT_NAME", [block], text, heuristic=True, reason="OCR agrees with inspector product context")
        other = p.OTHER.search(text)
        if other:
            emit("OTHER", [block], other[1], heuristic=True)
    if panel == "FRONT" and product_name and not any(item["declaration_type"] == "COMMON_PRODUCT_NAME" for item in results):
        titles = [b for b in blocks if 3 <= len(clean(b.raw_text)) <= 160
                  and re.search(r"[A-Za-z]{3}", b.raw_text)
                  and not p.BOUNDARY.search(clean(b.raw_text))
                  and not re.search(r"nutrition|ingredients|energy|protein|fat|carbohydrate|www\.|@|\d", b.raw_text, re.I)]
        if titles:
            title = max(titles, key=lambda b: b.bounding_box.get("height", b.bounding_box.get("y_max",0)-b.bounding_box.get("y_min",0)))
            emit("COMMON_PRODUCT_NAME", [title], clean(title.raw_text), heuristic=True,
                 reason="Prominent front-panel text; confirm the commodity name rather than the brand")
    if not any(item["declaration_type"] == "MRP" for item in results):
        mrp_blocks = [b for b in blocks if re.search(p.MRP_LABEL, clean(b.raw_text), re.I)]
        usp_item = next((item for item in results if item["declaration_type"] == "UNIT_SALE_PRICE"), None)
        qty_item = next((item for item in results if item["declaration_type"] == "NET_QUANTITY"), None)
        if mrp_blocks and usp_item and qty_item:
            try:
                from decimal import Decimal
                usp_data = usp_item.get("structured_value", {})
                qty_data = qty_item.get("structured_value", {})
                usp_num = Decimal(str(usp_data.get("amount", "0")))
                qty_num = Decimal(str(qty_data.get("numeric_value", "0")))
                if usp_num > 0 and qty_num > 0:
                    calc_mrp = str((usp_num * qty_num).quantize(Decimal("0.01")))
                    emit("MRP", mrp_blocks, calc_mrp, {"amount": calc_mrp, "currency": "INR", "inferred_from_usp": True}, heuristic=True)
            except Exception:
                pass

    return results

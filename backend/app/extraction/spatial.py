def nearby(a, b):
    """Bounded same-row or vertically aligned neighbors, in OCR image coordinates."""
    x, y = a.bounding_box, b.bounding_box
    try:
        height = max(1, min(x["y_max"] - x["y_min"], y["y_max"] - y["y_min"]))
        same_row = abs(x["y_min"] - y["y_min"]) <= height * .6
        if same_row:
            return 0 <= y["x_min"] - x["x_max"] <= height * 4
        overlap = min(x["x_max"], y["x_max"]) - max(x["x_min"], y["x_min"])
        aligned = overlap > 0 or abs(x["x_min"] - y["x_min"]) <= height * 2.5
        return aligned and -height * 0.6 <= y["y_min"] - x["y_max"] <= height * 3.5
    except (KeyError, TypeError):
        return False

def neighbors(blocks, index, boundary, clean):
    current = blocks[index]
    result = [current]
    # First try contiguous sequence in array
    for block in blocks[index+1:index+6]:
        if boundary.search(clean(block.raw_text)) or not nearby(result[-1], block):
            break
        result.append(block)
    if len(result) > 1:
        return result

    # If contiguous array search was cut off by multi-column layout, look for column-aligned blocks
    cur_box = current.bounding_box or {}
    cur_xmin = cur_box.get("x_min", 0)
    cur_xmax = cur_box.get("x_max", 0)
    cur_ymin = cur_box.get("y_min", 0)
    cur_h = max(10, cur_box.get("y_max", 0) - cur_ymin)

    candidates = []
    for b in blocks:
        if b.id == current.id:
            continue
        box = b.bounding_box or {}
        b_ymin = box.get("y_min", 0)
        b_xmin = box.get("x_min", 0)
        b_xmax = box.get("x_max", 0)
        if b_ymin < cur_ymin:
            continue
        overlap = min(cur_xmax, b_xmax) - max(cur_xmin, b_xmin)
        is_aligned = overlap > 0 or abs(cur_xmin - b_xmin) <= cur_h * 3.0
        if is_aligned:
            candidates.append(b)

    candidates.sort(key=lambda b: (b.bounding_box or {}).get("y_min", 0))
    last = current
    for b in candidates:
        if len(result) >= 6:
            break
        last_box = last.bounding_box or {}
        b_box = b.bounding_box or {}
        b_ymin = b_box.get("y_min", 0)
        last_ymax = last_box.get("y_max", 0)
        last_ymin = last_box.get("y_min", 0)
        h = max(10, last_ymax - last_ymin)
        if -h * 0.6 <= (b_ymin - last_ymax) <= h * 3.5:
            text_cln = clean(b.raw_text)
            if boundary.search(text_cln):
                break
            result.append(b)
            last = b

    return result



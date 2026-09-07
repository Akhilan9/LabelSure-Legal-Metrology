def nearby(a, b):
    """Bounded same-row or vertically aligned neighbors, in OCR image coordinates."""
    x, y = a.bounding_box, b.bounding_box
    try:
        height = max(1, min(x["y_max"] - x["y_min"], y["y_max"] - y["y_min"]))
        same_row = abs(x["y_min"] - y["y_min"]) <= height * .6
        if same_row:
            return 0 <= y["x_min"] - x["x_max"] <= height * 4
        overlap = min(x["x_max"], y["x_max"]) - max(x["x_min"], y["x_min"])
        aligned = overlap > 0 or abs(x["x_min"] - y["x_min"]) <= height * 2
        return aligned and 0 <= y["y_min"] - x["y_max"] <= height * 2
    except (KeyError, TypeError):
        return False

def neighbors(blocks, index, boundary, clean):
    result = [blocks[index]]
    for block in blocks[index+1:index+5]:
        if boundary.search(clean(block.raw_text)) or not nearby(result[-1], block):
            break
        result.append(block)
    return result


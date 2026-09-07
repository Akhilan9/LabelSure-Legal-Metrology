import math

def score(blocks, valid=True, heuristic=False, relevant_panel=False):
    values = [float(b.confidence) for b in blocks]
    ocr = min(max(0.0, min(1.0, n)) if math.isfinite(n) else 0.0 for n in values)
    factors = {"ocr": round(.55 * ocr, 4), "keyword": .10 if heuristic else .20,
               "format": .05 if heuristic or not valid else .15,
               "spatial": .05, "panel": .05 if relevant_panel else 0.0}
    value = round(min(1.0, sum(factors.values())), 4)
    return value, factors


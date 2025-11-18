# summarizer.py
def summarize_invoice(parsed):
    """
    Flatten Donut output into a clean summary dictionary.
    This function is intentionally forgiving.
    """
    result = {}

    # invoice number heuristics
    try:
        for n in parsed.get("menu", {}).get("nm", []):
            if isinstance(n, str) and "invoice" in n.lower():
                result["invoice_number"] = n.split(":")[-1].strip()
                break
    except Exception:
        result["invoice_number"] = ""

    try:
        vendor = parsed.get("menu", {}).get("cnt", {}).get("nm")
        result["vendor"] = vendor[0] if isinstance(vendor, list) else vendor or ""
    except Exception:
        result["vendor"] = ""

    try:
        date = parsed.get("menu", {}).get("unitprice")
        result["date"] = date[0] if isinstance(date, list) else date or ""
    except Exception:
        result["date"] = ""

    # items
    try:
        items = []
        for n in parsed.get("menu", {}).get("nm", []):
            if isinstance(n, str) and all(x not in n.lower() for x in ["invoice", "tax", "total"]):
                items.append({"description": n.strip()})
        result["items"] = items
    except Exception:
        result["items"] = []

    # monetary fields fallback
    result["subtotal"] = parsed.get("sub_total", {}).get("amount", "") if isinstance(parsed.get("sub_total", {}), dict) else ""
    result["tax"] = parsed.get("tax", "") or parsed.get("sub_total", {}).get("tax", "")
    result["grand_total"] = parsed.get("total", {}).get("total_price") or parsed.get("total_price", "") or ""

    result = {k: (v if v is not None else "") for k, v in result.items()}
    return result

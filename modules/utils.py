import re

def parse_numeric(text):
    if not text or not isinstance(text, str):
        return None
    text = text.replace(",", "").replace(" ", "").strip()
    try:
        if text.startswith("(") and text.endswith(")"):
            text = "-" + text[1:-1]

        if text.endswith("K"):
            return float(text[:-1]) * 1e3
        if text.endswith("M"):
            return float(text[:-1]) * 1e6
        if text.endswith("B"):
            return float(text[:-1]) * 1e9

        return float(text)
    except ValueError:
        try:
            return float(text)  # fallback for sci notation
        except Exception:
            return None


def find_currency_symbol(text):
    """Detect currency symbol from text."""
    if not text:
        return ""
    if "$" in text:
        return "$"
    if "₹" in text:
        return "₹"
    if "€" in text:
        return "€"
    if "£" in text:
        return "£"
    return ""


def extract_numbers_from_text(text):
    """Extract all numbers from text as floats."""
    matches = re.findall(r"[-+]?\d*\.\d+|\d+", text)
    return [parse_numeric(m) for m in matches if parse_numeric(m) is not None]


def format_currency(value, currency="$"):
    """Format number nicely with currency."""
    if isinstance(value, (int, float)):
        return f"{currency}{value:,.2f}"
    return value


def safe_format_metrics(metrics, currency="$"):
    """Format dict of metrics into readable string."""
    return {k: format_currency(v, currency) for k, v in metrics.items()}

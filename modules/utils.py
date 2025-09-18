import re


# -------------------- Numeric Parsing --------------------
def parse_numeric(text):
    """
    Convert a string containing a number into a float.

    Handles:
        - Commas and spaces
        - Parentheses for negatives (e.g., "(100)" → -100)
        - Suffixes like K, M, B (e.g., "1.5M" → 1,500,000)
        - Scientific notation (e.g., "1e6")

    Args:
        text (str): Input string with numeric value

    Returns:
        float | None: Parsed number, or None if parsing fails
    """
    if not text or not isinstance(text, str):
        return None

    # Remove commas, spaces → standardize
    text = text.replace(",", "").replace(" ", "").strip()

    try:
        # Handle accounting-style negatives: (100) → -100
        if text.startswith("(") and text.endswith(")"):
            text = "-" + text[1:-1]

        # Handle suffix multipliers
        if text.endswith("K"):
            return float(text[:-1]) * 1e3
        if text.endswith("M"):
            return float(text[:-1]) * 1e6
        if text.endswith("B"):
            return float(text[:-1]) * 1e9

        # Default case → parse as float
        return float(text)

    except ValueError:
        # Retry in case input is in scientific notation
        try:
            return float(text)
        except Exception:
            return None


# -------------------- Currency Detection --------------------
def find_currency_symbol(text):
    """
    Detect currency symbol from a given text.

    Supports:
        $, ₹, €, £

    Args:
        text (str): Input string

    Returns:
        str: Currency symbol, or empty string if not found
    """
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


# -------------------- Number Extraction --------------------
def extract_numbers_from_text(text):
    """
    Extract all numeric values from a text string.

    Uses regex to detect integers, floats, and negatives,
    then parses them into floats.

    Args:
        text (str): Input text

    Returns:
        list[float]: All detected numbers
    """
    matches = re.findall(r"[-+]?\d*\.\d+|\d+", text)
    return [parse_numeric(m) for m in matches if parse_numeric(m) is not None]


# -------------------- Formatting Helpers --------------------
def format_currency(value, currency="$"):
    """
    Format a numeric value with currency symbol and commas.

    Args:
        value (float | int): Numeric value
        currency (str, optional): Currency symbol

    Returns:
        str: Formatted string (e.g., "$1,234.56")
    """
    if isinstance(value, (int, float)):
        return f"{currency}{value:,.2f}"
    return value  # If value is not numeric, return as-is


def safe_format_metrics(metrics, currency="$"):
    """
    Format a dict of metrics into human-readable strings.
    
    Args:
        metrics (dict): Metric name → numeric value
        currency (str, optional): Currency symbol

    Returns:
        dict: Metric name → formatted string
    """
    return {k: format_currency(v, currency) for k, v in metrics.items()}

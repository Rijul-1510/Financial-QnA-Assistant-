# modules/processor.py
import re
import os
import pdfplumber
import pandas as pd
from collections import defaultdict
from modules.utils import parse_numeric, find_currency_symbol

# ----------------------------------------------------------------------
# Keyword dictionary for detecting common financial metrics in text/tables
# ----------------------------------------------------------------------
METRIC_KEYWORDS = {
    "revenue": ["revenue", "total revenue", "sales", "net sales"],
    "gross_profit": ["gross profit", "gross margin"],
    "operating_income": ["operating income", "operating profit"],
    "net_income": ["net income", "net profit", "profit for the year", "profit after tax"],
    "ebitda": ["ebitda"],
    "total_assets": ["total assets"],
    "total_liabilities": ["total liabilities"],
    "cash_and_equivalents": ["cash and cash equivalents", "cash and equivalents"],
    "cost_of_revenue": ["cost of revenue", "cost of sales", "cost of goods sold", "cogs"],
    "total_equity": ["total equity", "shareholders' equity", "shareholders equity"],
}

# ----------------------------------------------------------------------
# Function: find_metric_in_text
# ----------------------------------------------------------------------
def find_metric_in_text(text, keyword_list):
    """
    Search for financial metrics in plain text lines.

    Args:
        text (str): Raw extracted text from documents.
        keyword_list (list): List of possible keywords for a metric.

    Returns:
        list: Tuples of (line, numeric_values) for matched lines.
    """
    text_l = text.lower()
    best_hits = []
    # Look for lines containing the keyword and numeric values
    for kw in keyword_list:
        for line in text_l.splitlines():
            if kw in line:
                nums = re.findall(r"[-+]?\d[\d,\.]*", line)
                if nums:
                    best_hits.append((line.strip(), nums))
    return best_hits

# ----------------------------------------------------------------------
# Function: read_numbers_from_tables
# ----------------------------------------------------------------------
def read_numbers_from_tables(tables):
    """
    Extract metrics from tabular data (DataFrames).

    Logic:
        - Checks column headers and first column for keywords.
        - Picks first numeric-looking value in the row/column.

    Args:
        tables (list[pd.DataFrame]): Tables extracted from PDF/Excel.

    Returns:
        dict: {metric_name -> numeric_value}
    """
    results = {}
    for metric, kws in METRIC_KEYWORDS.items():
        for df in tables:
            df2 = df.copy()
            df2.columns = [str(c).lower() for c in df2.columns]

            # Check for metric keywords in column headers
            for col in df2.columns:
                col_text = str(col).lower()
                for kw in kws:
                    if kw in col_text:
                        colvals = df2[col].astype(str).replace("nan", "", regex=False)
                        for v in colvals:
                            if contains_number(str(v)):
                                results[metric] = parse_numeric(str(v))
                                break

            # Check first column (row labels)
            leftcol = df2.iloc[:, 0].astype(str).str.lower()
            for idx, label in leftcol.items():
                for kw in kws:
                    if kw in str(label):
                        row = df.iloc[idx, :].astype(str)
                        for cell in row:
                            if contains_number(str(cell)):
                                results[metric] = parse_numeric(str(cell))
                                break
    return results

# ----------------------------------------------------------------------
# Function: contains_number
# ----------------------------------------------------------------------
def contains_number(s):
    """Return True if a string contains a numeric pattern."""
    return bool(re.search(r"[-+]?\d[\d,\.]*", s))

# ----------------------------------------------------------------------
# Function: find_currency_in_document
# ----------------------------------------------------------------------
def find_currency_in_document(raw_text, tables):
    """
    Detect currency symbol/code in raw text or tables.

    Args:
        raw_text (str): Text extracted from document.
        tables (list[pd.DataFrame]): Extracted tables.

    Returns:
        str | None: Detected currency symbol/code.
    """
    txt = raw_text
    symbols = ['₹', '$', '€', '£', '¥']
    for s in symbols:
        if s in txt:
            return s
    for token in ["inr", "usd", "eur", "gbp", "jpy", "aud"]:
        if token in txt.lower():
            return token.upper()
    # Check tables for symbolic currencies
    for df in tables:
        if any(df.astype(str).apply(lambda col: col.str.contains(r"₹|\$|€|£", na=False)).any()):
            return "symbolic"
    return None

# ----------------------------------------------------------------------
# Function: pretty_print_metrics
# ----------------------------------------------------------------------
def pretty_print_metrics(structured):
    """
    Convert structured metrics dict into a DataFrame for display.

    Args:
        structured (dict): {"metrics": {...}, "currency": ...}

    Returns:
        pd.DataFrame: Table of metrics and values.
    """
    metrics = structured.get("metrics", {})
    rows = [{"metric": k, "value": v} for k, v in metrics.items()]
    return pd.DataFrame(rows)

# ----------------------------------------------------------------------
# Function: extract_multi_year_data
# ----------------------------------------------------------------------
def extract_multi_year_data(tables):
    """
    Extract financial metrics across multiple years from tables.

    Steps:
        1. Identify year columns (e.g., "2021", "FY22", "2020-21").
        2. For each metric row, map year -> metric -> value.

    Args:
        tables (list[pd.DataFrame]): Extracted tables.

    Returns:
        dict: {year -> {metric -> value}}
    """
    yearly_data = {}

    for df in tables:
        df_str = df.astype(str).replace("nan", "", regex=False)
        df_str = df_str.replace(r"\(.*\)", "-", regex=True)  # Handle negatives

        # Detect year columns
        year_columns = []
        for col_idx, col_name in enumerate(df_str.columns):
            year_match = re.search(r'(20\d{2})|(FY\s*\d{2})|(\d{4}[-/]\d{2})', str(col_name))
            if year_match:
                year = year_match.group(1) or year_match.group(2) or year_match.group(3)
                year_columns.append((col_idx, year))

        # Fallback: detect years in first row if not in headers
        if not year_columns and len(df_str) > 0:
            first_row = df_str.iloc[0]
            for col_idx, cell_value in enumerate(first_row):
                year_match = re.search(r'(20\d{2})|(FY\s*\d{2})|(\d{4}[-/]\d{2})', str(cell_value))
                if year_match:
                    year = year_match.group(1) or year_match.group(2) or year_match.group(3)
                    year_columns.append((col_idx, year))

        if not year_columns:
            continue

        # Extract metrics row by row
        for row_idx, row in df_str.iterrows():
            if row_idx == 0:  # Skip header
                continue

            row_label = str(row.iloc[0]).lower().strip()
            for metric, keywords in METRIC_KEYWORDS.items():
                if any(keyword in row_label for keyword in keywords):
                    for col_idx, year in year_columns:
                        if col_idx < len(row) and row.iloc[col_idx].strip():
                            clean_value = re.sub(r'[\(\)\$,]', '', str(row.iloc[col_idx])).strip()
                            if re.search(r'\(.*\)', str(row.iloc[col_idx])):
                                clean_value = '-' + clean_value
                            value = parse_numeric(clean_value)
                            if value is not None:
                                yearly_data.setdefault(year, {})[metric] = value
                    break

    return yearly_data

# ----------------------------------------------------------------------
# Function: structure_financial_data
# ----------------------------------------------------------------------
def structure_financial_data(raw_text, tables):
    """
    Aggregate financial data from text + tables.

    Steps:
        1. Extract single metrics (tables first, fallback to text).
        2. Extract multi-year data from tables.
        3. Use latest year values to improve single-metric confidence.
        4. Detect currency used.

    Args:
        raw_text (str): Text extracted from document.
        tables (list[pd.DataFrame]): Extracted tables.

    Returns:
        dict: {
            "metrics": {...},
            "yearly_metrics": {...},
            "currency": str,
            "confidence": {...}
        }
    """
    metrics, confidence = {}, {}

    # Prefer table extraction
    table_metrics = read_numbers_from_tables(tables)
    for k, v in table_metrics.items():
        metrics[k] = v
        confidence[k] = "high"

    # Fallback: text-based search
    for metric, kws in METRIC_KEYWORDS.items():
        if metric not in metrics:
            hits = find_metric_in_text(raw_text, kws)
            if hits:
                val = parse_numeric(hits[0][1][-1])
                if val is not None:
                    metrics[metric] = val
                    confidence[metric] = "medium"

    # Multi-year extraction
    yearly_metrics = extract_multi_year_data(tables)

    # Use latest year values to boost single-metric accuracy
    if yearly_metrics:
        latest_year = max(yearly_metrics.keys())
        for metric, value in yearly_metrics[latest_year].items():
            if metric not in metrics or confidence.get(metric) != "high":
                metrics[metric] = value
                confidence[metric] = "high"

    # Normalize metrics dict to include all expected keys
    normalized = {k: metrics.get(k) for k in METRIC_KEYWORDS.keys()}

    return {
        "metrics": normalized,
        "yearly_metrics": yearly_metrics,
        "currency": find_currency_in_document(raw_text, tables),
        "confidence": confidence
    }

# ----------------------------------------------------------------------
# Function: process_documents
# ----------------------------------------------------------------------
def process_documents(uploaded_files):
    """
    Process uploaded PDF/Excel files into structured context dicts.

    Steps:
        1. Save uploaded file locally.
        2. Extract text + tables (pdfplumber for PDF, pandas for Excel).
        3. Structure financial data into metrics + yearly metrics.

    Args:
        uploaded_files (list): Uploaded file objects.

    Returns:
        list[dict]: Each dict contains
            {
                "name": file_name,
                "metrics": {...},
                "raw_text": str,
                "currency": str,
                "yearly_metrics": {...}
            }
    """
    docs_context = []

    for file in uploaded_files:
        file_path = file.name
        ext = os.path.splitext(file_path)[1].lower()

        # Save locally so PDF/Excel parsers can read
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

        raw_text, tables = "", []

        try:
            if ext == ".pdf":
                # Extract text + tables from PDF pages
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        raw_text += page.extract_text() or ""
                        try:
                            for t in page.extract_tables():
                                if t:
                                    df = pd.DataFrame(t[1:], columns=t[0])
                                    tables.append(df)
                        except Exception:
                            continue

            elif ext in [".xls", ".xlsx"]:
                # Extract text + tables from Excel
                xls = pd.ExcelFile(file_path)
                for sheet in xls.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet)
                    raw_text += df.to_string(index=False) + "\n"
                    tables.append(df)

        except Exception as e:
            raw_text += f"\n[Error processing file: {e}]"

        # Extract financial metrics
        structured = structure_financial_data(raw_text, tables)

        docs_context.append({
            "name": file.name,
            "metrics": structured,
            "raw_text": raw_text,
            "currency": structured.get("currency"),
            "yearly_metrics": structured.get("yearly_metrics", {})
        })

    return docs_context

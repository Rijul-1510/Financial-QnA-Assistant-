# modules/processor.py (updated)
import re
import os
import pdfplumber
import pandas as pd
from collections import defaultdict
from modules.utils import parse_numeric, find_currency_symbol

# Heuristics-based extractor: finds common financial metrics in text and tables.
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

# Keep the rest of the functions the same as before
def find_metric_in_text(text, keyword_list):
    text_l = text.lower()
    best_hits = []
    # look for lines containing keyword and a number
    for kw in keyword_list:
        for line in text_l.splitlines():
            if kw in line:
                nums = re.findall(r"[-+]?\d[\d,\.]*", line)
                if nums:
                    best_hits.append((line.strip(), nums))
    return best_hits

def read_numbers_from_tables(tables):
    """
    Attempt to locate metrics in DataFrames by scanning headers and leftmost column for keywords.
    Returns dict metric->value
    """
    results = {}
    for metric, kws in METRIC_KEYWORDS.items():
        for df in tables:
            # convert all headers and first column to strings
            df2 = df.copy()
            df2.columns = [str(c).lower() for c in df2.columns]
            # check columns
            for col in df2.columns:
                col_text = str(col).lower()
                for kw in kws:
                    if kw in col_text:
                        # get the first numeric-looking cell in column
                        colvals = df2[col].astype(str).replace("nan","",regex=False)
                        for v in colvals:
                            if contains_number(str(v)):
                                results[metric] = parse_numeric(str(v))
                                break
            # check first column/left-most text labels
            leftcol = df2.iloc[:,0].astype(str).str.lower()
            for idx, label in leftcol.items():
                for kw in kws:
                    if kw in str(label):
                        # pick numeric from row
                        row = df.iloc[idx, :].astype(str)
                        for cell in row:
                            if contains_number(str(cell)):
                                results[metric] = parse_numeric(str(cell))
                                break
    return results

def contains_number(s):
    return bool(re.search(r"[-+]?\d[\d,\.]*", s))

def find_currency_in_document(raw_text, tables):
    # naive currency detection by searching for ₹, $, €, £ or words like INR, USD
    txt = raw_text
    symbols = ['₹', '$', '€', '£', '¥']
    for s in symbols:
        if s in txt:
            return s
    for token in ["inr", "usd", "eur", "gbp", "jpy", "aud"]:
        if token in txt.lower():
            return token.upper()
    # check tables
    for df in tables:
        if any(df.astype(str).apply(lambda col: col.str.contains(r"₹|\$|€|£", na=False)).any()):
            return "symbolic"
    return None

def pretty_print_metrics(structured):
    """
    structured = {'metrics': {..}, 'currency': ...}
    returns DataFrame for display
    """
    metrics = structured.get("metrics", {})
    rows = []
    for k, v in metrics.items():
        rows.append({"metric": k, "value": v})
    df = pd.DataFrame(rows)
    return df

# modules/processor.py (updated extract_multi_year_data function)
def extract_multi_year_data(tables):
    """
    Extract financial data for multiple years from tables
    Returns a dictionary with year as key and metrics as value
    """
    yearly_data = {}
    
    for df in tables:
        # Convert all values to strings and clean up
        df_str = df.astype(str)
        df_str = df_str.replace("nan", "", regex=False)
        df_str = df_str.replace(r"\(.*\)", "-", regex=True)  # Handle negative numbers in parentheses
        
        # Look for year columns (4-digit numbers or financial year labels)
        year_columns = []
        for col_idx, col_name in enumerate(df_str.columns):
            col_str = str(col_name)
            # Match 4-digit years or financial year patterns
            year_match = re.search(r'(20\d{2})|(FY\s*\d{2})|(\d{4}[-/]\d{2})', col_str)
            if year_match:
                year = year_match.group(1) or year_match.group(2) or year_match.group(3)
                year_columns.append((col_idx, year))
        
        if not year_columns:
            # Try to find years in the first row if not in headers
            if len(df_str) > 0:
                first_row = df_str.iloc[0]
                for col_idx, cell_value in enumerate(first_row):
                    cell_str = str(cell_value)
                    year_match = re.search(r'(20\d{2})|(FY\s*\d{2})|(\d{4}[-/]\d{2})', cell_str)
                    if year_match:
                        year = year_match.group(1) or year_match.group(2) or year_match.group(3)
                        year_columns.append((col_idx, year))
        
        if not year_columns:
            continue
            
        # Process each row to find metrics
        for row_idx, row in df_str.iterrows():
            if row_idx == 0:  # Skip header row if we're using first row for years
                continue
                
            row_label = str(row.iloc[0]).lower().strip()
            
            # Check if this row contains a financial metric
            for metric, keywords in METRIC_KEYWORDS.items():
                if any(keyword in row_label for keyword in keywords):
                    # Extract values for each year column
                    for col_idx, year in year_columns:
                        if col_idx < len(row) and row.iloc[col_idx].strip() and row.iloc[col_idx].strip() not in ['', 'nan']:
                            # Clean the value (remove parentheses, commas, etc.)
                            clean_value = re.sub(r'[\(\)\$,]', '', str(row.iloc[col_idx])).strip()
                            # Handle negative values in parentheses
                            if re.search(r'\(.*\)', str(row.iloc[col_idx])):
                                clean_value = '-' + clean_value
                            value = parse_numeric(clean_value)
                            if value is not None:
                                if year not in yearly_data:
                                    yearly_data[year] = {}
                                yearly_data[year][metric] = value
                    break
    
    return yearly_data

def structure_financial_data(raw_text, tables):
    # Extract single metrics (original approach)
    metrics = {}
    confidence = {}
    
    # Extract from tables (preferred)
    table_metrics = read_numbers_from_tables(tables)
    for k, v in table_metrics.items():
        metrics[k] = v
        confidence[k] = "high"

    # Fallback to text
    for metric, kws in METRIC_KEYWORDS.items():
        if metric not in metrics:
            hits = find_metric_in_text(raw_text, kws)
            if hits:
                val = parse_numeric(hits[0][1][-1])  # last number
                if val is not None:
                    metrics[metric] = val
                    confidence[metric] = "medium"

    # Extract multi-year data
    yearly_metrics = extract_multi_year_data(tables)
    
    # If we have multi-year data, use the most recent year for single metrics
    if yearly_metrics:
        latest_year = max(yearly_metrics.keys())
        for metric, value in yearly_metrics[latest_year].items():
            if metric not in metrics or confidence.get(metric, "") != "high":
                metrics[metric] = value
                confidence[metric] = "high"

    # Normalize
    normalized = {k: metrics.get(k) for k in METRIC_KEYWORDS.keys()}

    return {
        "metrics": normalized,
        "yearly_metrics": yearly_metrics,
        "currency": find_currency_in_document(raw_text, tables),
        "confidence": confidence
    }

def process_documents(uploaded_files):
    """
    Process uploaded PDF/Excel documents into structured context dicts.
    Returns a list of dicts with {name, metrics, yearly_metrics, raw_text, currency}.
    """
    docs_context = []

    for file in uploaded_files:
        file_path = file.name
        ext = os.path.splitext(file_path)[1].lower()

        # Save uploaded file locally (so pdfplumber/pandas can open it)
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

        raw_text = ""
        tables = []

        try:
            if ext == ".pdf":
                # Extract text and tables from PDF
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        raw_text += page.extract_text() or ""
                        try:
                            # Convert extracted tables into pandas DataFrames
                            page_tables = page.extract_tables()
                            for t in page_tables:
                                if t:
                                    df = pd.DataFrame(t[1:], columns=t[0])
                                    tables.append(df)
                        except Exception:
                            continue

            elif ext in [".xls", ".xlsx"]:
                # Read Excel sheets
                xls = pd.ExcelFile(file_path)
                for sheet in xls.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet)
                    raw_text += df.to_string(index=False) + "\n"
                    tables.append(df)

        except Exception as e:
            raw_text += f"\n[Error processing file: {e}]"

        # Extract metrics + multi-year info
        structured = structure_financial_data(raw_text, tables)

        docs_context.append({
            "name": file.name,
            "metrics": structured,
            "raw_text": raw_text,
            "currency": structured.get("currency"),
            "yearly_metrics": structured.get("yearly_metrics", {})
        })

    return docs_context
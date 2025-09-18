# modules/extractor.py (updated)
import io
import pdfplumber
import pandas as pd
import re   
from typing import Tuple, List
from modules.utils import extract_numbers_from_text as utils_extract_numbers

def extract_numbers_from_text(text):
    return utils_extract_numbers(text)

def extract_from_pdf(file_obj) -> Tuple[str, List]:
    text_pages, tables = [], []
    try:
        with pdfplumber.open(file_obj) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    text_pages.append(f"[Page {page_num}]\n{text}")
                try:
                    for t in page.extract_tables() or []:
                        df = pd.DataFrame(t).dropna(how="all")
                        if not df.empty:
                            # Clean up the table - remove empty rows and columns
                            df = df.replace("", pd.NA).dropna(how="all").dropna(axis=1, how="all")
                            tables.append(df)
                except Exception as e:
                    print(f"⚠️ Table extraction failed on page {page_num}: {e}")
    except Exception as e:
        raise RuntimeError(f"PDF extraction failed: {e}")
    
    raw_text = re.sub(r"\n{3,}", "\n\n", "\n\n".join(text_pages))
    return raw_text, tables

def extract_from_excel(file_obj) -> Tuple[str, List]:
    try:
        xls = pd.read_excel(file_obj, sheet_name=None, engine="openpyxl")
    except Exception:
        xls = pd.read_excel(file_obj, sheet_name=None, engine="xlrd")

    tables = []
    text_parts = []
    for sheet_name, df in xls.items():
        if not df.empty:
            tables.append(df)
            text_parts.append(f"Sheet: {sheet_name} | shape: {df.shape}")
            # include a few header rows for context
            text_parts.append("Headers: " + ", ".join([str(c) for c in df.columns[:10]]))
    raw_text = "\n".join(text_parts)
    return raw_text, tables
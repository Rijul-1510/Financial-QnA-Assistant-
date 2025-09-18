# -------------------- Imports --------------------
import io
import pdfplumber             # For extracting text and tables from PDF
import pandas as pd           # For handling tabular data
import re                     # For text cleaning and regex operations
from typing import Tuple, List
from modules.utils import extract_numbers_from_text as utils_extract_numbers


# -------------------- Wrapper Function --------------------
def extract_numbers_from_text(text):
    """
    Wrapper around utils_extract_numbers.
    Extracts numeric values from text using a helper in utils.py.
    """
    return utils_extract_numbers(text)


# -------------------- PDF Extraction --------------------
def extract_from_pdf(file_obj) -> Tuple[str, List]:
    """
    Extract text and tables from a PDF file.

    Args:
        file_obj: A file-like object (uploaded PDF)

    Returns:
        raw_text (str): Combined text extracted from all PDF pages
        tables (List[pd.DataFrame]): List of extracted tables
    """
    text_pages, tables = [], []  # Store extracted text and tables
    try:
        with pdfplumber.open(file_obj) as pdf:
            # Loop through each page in PDF
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract page text
                text = (page.extract_text() or "").strip()
                if text:
                    text_pages.append(f"[Page {page_num}]\n{text}")

                # Try extracting tables
                try:
                    for t in page.extract_tables() or []:
                        df = pd.DataFrame(t).dropna(how="all")
                        if not df.empty:
                            # Clean table → remove empty rows and columns
                            df = df.replace("", pd.NA).dropna(how="all").dropna(axis=1, how="all")
                            tables.append(df)
                except Exception as e:
                    print(f"⚠️ Table extraction failed on page {page_num}: {e}")
    except Exception as e:
        # If PDF reading completely fails
        raise RuntimeError(f"PDF extraction failed: {e}")
    
    # Join all extracted text, ensuring no huge blank gaps
    raw_text = re.sub(r"\n{3,}", "\n\n", "\n\n".join(text_pages))
    return raw_text, tables


# -------------------- Excel Extraction --------------------
def extract_from_excel(file_obj) -> Tuple[str, List]:
    """
    Extract text and tables from an Excel file.

    Args:
        file_obj: A file-like object (uploaded Excel file)

    Returns:
        raw_text (str): Metadata-like summary of sheets and headers
        tables (List[pd.DataFrame]): List of extracted DataFrames
    """
    # Try openpyxl first (newer engine), fallback to xlrd (legacy engine)
    try:
        xls = pd.read_excel(file_obj, sheet_name=None, engine="openpyxl")
    except Exception:
        xls = pd.read_excel(file_obj, sheet_name=None, engine="xlrd")

    tables = []
    text_parts = []

    # Process each sheet in the Excel file
    for sheet_name, df in xls.items():
        if not df.empty:
            tables.append(df)

            # Add summary info for context in raw_text
            text_parts.append(f"Sheet: {sheet_name} | shape: {df.shape}")

            # Add first few column headers for quick reference
            text_parts.append("Headers: " + ", ".join([str(c) for c in df.columns[:10]]))
    
    # Join all summaries into one raw text string
    raw_text = "\n".join(text_parts)
    return raw_text, tables

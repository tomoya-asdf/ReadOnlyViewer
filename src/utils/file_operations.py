import os
import fitz  # PyMuPDF
import openpyxl
from pptx import Presentation
import csv
import docx
import chardet

# --- Text Extraction Functions ---

def extract_text_preview(filepath):
    """Extracts text from various file types for preview."""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".pdf":
            return extract_pdf_text(filepath)
        elif ext in [".xlsx", ".xlsm"]:
            return extract_excel_text(filepath)
        elif ext in [".pptx", ".pptm"]:
            return extract_pptx_text(filepath)
        elif ext in [".docx", ".docm"]:
            return extract_docx_text(filepath)
        elif ext == ".csv":
            return extract_csv_text(filepath)
        else:
            # For other extensions, attempt to read as a text file.
            return extract_text_file(filepath)
    except Exception as e:
        # This is a fallback for binary files or read errors.
        return f"プレビュー中にエラーが発生しました: {e}"

def extract_pdf_text(filepath):
    with fitz.open(filepath) as doc:
        return "".join(page.get_text() for page in doc)

def render_pdf_as_pixmaps(filepath, dpi=96):
    try:
        with fitz.open(filepath) as doc:
            matrix = fitz.Matrix(dpi / 72, dpi / 72)
            return [page.get_pixmap(matrix=matrix) for page in doc]
    except Exception as e:
        print(f"PDFレンダリングエラー: {e}")
        return []

def extract_excel_text(filepath):
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    text = []
    for sheet in wb.worksheets:
        text.append(f"[{sheet.title}]")
        for row in sheet.iter_rows(values_only=True):
            line = "\t".join(str(cell) if cell is not None else "" for cell in row)
            text.append(line)
    return "\n".join(text)

def extract_pptx_text(filepath):
    prs = Presentation(filepath)
    text = []
    for i, slide in enumerate(prs.slides):
        text.append(f"[スライド{i + 1}]")
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text.append(shape.text)
    return "\n".join(text)

def extract_docx_text(filepath):
    doc = docx.Document(filepath)
    return "\n".join(p.text for p in doc.paragraphs)

def extract_csv_text(filepath):
    encoding = detect_encoding(filepath) or 'utf-8'
    rows = []
    try:
        with open(filepath, newline="", encoding=encoding, errors='ignore') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i >= 200: # Limit rows for performance
                    break
                rows.append(", ".join(row))
        return "\n".join(rows)
    except (UnicodeDecodeError, csv.Error):
        # Fallback to raw text read if CSV parsing fails
        return extract_text_file(filepath)

def extract_text_file(filepath):
    """Reads a plain text file with robust encoding detection."""
    encoding = detect_encoding(filepath)
    try:
        with open(filepath, "r", encoding=encoding or 'utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        # If chardet fails or file is binary, read with a safe fallback.
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

def detect_encoding(filepath, sample_size=4096):
    """Detects the encoding of a file by reading a sample."""
    try:
        with open(filepath, 'rb') as f:
            sample = f.read(sample_size)
            result = chardet.detect(sample)
            return result['encoding']
    except (IOError, IndexError):
        return None

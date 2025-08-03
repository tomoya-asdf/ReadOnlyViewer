import os
import fitz  # PyMuPDF
import openpyxl
from pptx import Presentation
import csv
import docx

def extract_text_preview(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".pdf":
            return extract_pdf_text(filepath)
        elif ext in [".xlsx", "xlsm"]:
            return extract_excel_text(filepath)
        elif ext in [".pptx", ".pptm"]:
            return extract_pptx_text(filepath)
        elif ext in [".docx", ".docm"]: 
            return extract_docx_text(filepath)
        elif ext == ".csv":
            return extract_csv_text(filepath)
        # 一般的なテキストファイル、コードファイル、設定ファイルなどを追加
        elif ext in [".txt", ".md", ".json", ".xml", ".html", ".htm", ".css", ".js", ".jsx",
                      ".ts", ".tsx", ".py", ".java", ".c", ".cpp", ".h", ".go", ".rb",
                      ".php", ".sh", ".log", ".ini", ".conf", ".yml", ".yaml", ".bat", ".cmd", ".ps1",
                      ".sql", ".pl", ".swift", ".kt", ".vue", ".svelte", ".toml", ".gitignore", ".editorconfig",
                      ".npmrc", ".env", ".dockerfile", ".makefile", ".rst", ".tex", ".rtf", ".nfo", ".diz"]:
            return extract_text_file(filepath)
        else:
            # 上記以外のファイルもテキストとして読み込みを試みる
            try:
                return extract_text_file(filepath)
            except Exception:
                return "未対応またはバイナリ形式のファイルです。"
    except Exception as e:
        return f"プレビュー中にエラーが発生しました：{e}"

def extract_pdf_text(filepath):
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def render_pdf_as_pixmaps(filepath, dpi=96):
    try:
        doc = fitz.open(filepath)
        pixmaps = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
            pixmaps.append(pix)
        doc.close()
        return pixmaps
    except Exception as e:
        print(f"PDFレンダリングエラー: {e}")
        return []

def extract_excel_text(filepath):
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    text = ""
    for sheet in wb.worksheets:
        text += f"[{sheet.title}]\n"
        for row in sheet.iter_rows(values_only=True):
            line = "\t".join(str(cell) if cell is not None else "" for cell in row)
            text += line + "\n"
    return text

def extract_pptx_text(filepath):
    prs = Presentation(filepath)
    text = ""
    for i, slide in enumerate(prs.slides):
        text += f"[スライド{i + 1}]\n"
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"
    return text

def extract_csv_text(filepath):
    encodings_to_try = ['utf-8', 'utf-16', 'shift_jis', 'cp932', 'euc_jp', 'iso2022_jp']
    for encoding in encodings_to_try:
        try:
            rows = []
            with open(filepath, newline="", encoding=encoding, errors="ignore") as f:
                reader = csv.reader(f)
                for row in reader:
                    rows.append(", ".join(row))
                    if len(rows) > 100:  # Limit to 100 rows for preview
                        break
            return "\n".join(rows)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            # Other errors like FileNotFoundError should still be raised or handled
            raise e
    # Fallback if no encoding works
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def extract_docx_text(filepath):
    doc = docx.Document(filepath)
    return "\n".join(p.text for p in doc.paragraphs)

def extract_text_file(filepath):
    encodings_to_try = ['utf-8', 'utf-16', 'shift_jis', 'cp932', 'euc_jp', 'iso2022_jp']
    for encoding in encodings_to_try:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            # Other errors like FileNotFoundError should still be raised or handled
            raise e
    # Fallback if no encoding works
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
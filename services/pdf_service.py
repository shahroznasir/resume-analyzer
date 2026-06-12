import pdfplumber

def extract_pdf_text(file_path: str) -> str:
    pages = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
        return "\n".join(pages)
    except Exception as e:
        raise Exception(
            f"Failed to extract text from PDF: {str(e)}"
        )
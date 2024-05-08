from pypdf import PdfReader


def extract_text_from_pdf(file_path, nougate_model=None):
    if nougate_model:
        return nougate_model.extract_text(file_path)
    else:
        with open(file_path, "rb") as file:
            reader = PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
                # break  # Remove this line to extract text from all pages
        return text


def extract_text_from_docx(file_path):
    pass


def extract_text_from_txt(file_path):
    with open(file_path, "r") as file:
        text = file.read()
    return text


def extract_text_from_html(file_path):
    pass


extractors = {
    "pdf": extract_text_from_pdf,
    "docx": extract_text_from_docx,
    "txt": extract_text_from_txt,
    "html": extract_text_from_html,
}

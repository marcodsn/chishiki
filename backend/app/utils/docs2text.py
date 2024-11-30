from pypdf import PdfReader
import os

# Docling compatible extractors
def extract_text_from_pdf(file_path, docling_converter=None):
    if docling_converter:
        return docling_converter.extract_text(file_path)
    else:
        with open(file_path, "rb") as file:
            reader = PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text

def extract_text_from_document(file_path, docling_converter=None):
    if docling_converter:
        return docling_converter.convert(file_path)
    else:
        return None

def extract_text_from_txt(file_path):
    with open(file_path, "r") as file:
        text = file.read()
    return text

# Whisper compatible extractors
def extract_text_from_audio(file_path, asr_model):
    return asr_model.transcribe_and_diarize(file_path)

def extract_text_from_video(file_path, asr_model):
    audio_file_path = "temp_audio.wav"
    asr_model.extract_audio_from_video(file_path, audio_file_path)
    result = asr_model.transcribe_and_diarize(audio_file_path)
    os.remove(audio_file_path)
    return result

extractors = {
    "pdf": extract_text_from_pdf,
    "docx": extract_text_from_document,
    "html": extract_text_from_document,
    "pptx": extract_text_from_document,
    "asciidoc": extract_text_from_document,
    "md": extract_text_from_document,

    "png": extract_text_from_document,
    "jpg": extract_text_from_document,
    "jpeg": extract_text_from_document,

    "txt": extract_text_from_txt,
    "wav": extract_text_from_audio,
    "mp3": extract_text_from_audio,
    "ogg": extract_text_from_audio,
    "mp4": extract_text_from_video,
}

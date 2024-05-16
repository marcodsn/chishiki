from pypdf import PdfReader
import os

def extract_text_from_pdf(file_path, nougat_model=None):
    if nougat_model:
        return nougat_model.extract_text(file_path)
    else:
        with open(file_path, "rb") as file:
            reader = PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
        return text

def extract_text_from_docx(file_path):
    pass

def extract_text_from_txt(file_path):
    with open(file_path, "r") as file:
        text = file.read()
    return text

def extract_text_from_audio(file_path, asr_model):
    return asr_model.transcribe_and_diarize(file_path)

def extract_text_from_video(file_path, asr_model):
    audio_file_path = "temp_audio.wav"
    asr_model.extract_audio_from_video(file_path, audio_file_path)
    result = asr_model.transcribe_and_diarize(audio_file_path)
    os.remove(audio_file_path)
    return result

def extract_text_from_html(file_path):
    pass

extractors = {
    "pdf": extract_text_from_pdf,
    "docx": extract_text_from_docx,
    "txt": extract_text_from_txt,
    # "audio": extract_text_from_audio,
    # "video": extract_text_from_video,
    "wav": extract_text_from_audio,
    "mp3": extract_text_from_audio,
    "ogg": extract_text_from_audio,
    "mp4": extract_text_from_video,
    "html": extract_text_from_html,
}

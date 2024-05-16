import os
import torch
import whisper
from pyannote.audio import Pipeline
import moviepy.editor as mp

class ASRModel:
    def __init__(self, whisper_model_name="large-v3", diarization_model_name="pyannote/speaker-diarization-3.1", use_cuda=True, auth_token=None):
        self.device = torch.device("cuda:0" if use_cuda and torch.cuda.is_available() else "cpu")
        
        print("Loading ASR model...")
        
        # Load the Whisper model
        self.whisper_model = whisper.load_model(whisper_model_name)
        self.whisper_model = self.whisper_model.to(self.device)
        
        # Load the PyAnnote speaker diarization pipeline
        if auth_token is None:
            auth_token = os.getenv("HF_AUTH_TOKEN")  # Read the HF token from environment variables
        self.diarization_pipeline = Pipeline.from_pretrained(diarization_model_name, use_auth_token=auth_token)
        self.diarization_pipeline.to(self.device)
        
        print("ASR model loaded successfully.")
    
    def transcribe_and_diarize(self, audio_file_path):
        # Transcribe the audio file using Whisper
        print("Transcribing audio...")
        result = self.whisper_model.transcribe(audio_file_path, verbose=False)
        print("Transcription complete.")
        
        # Perform speaker diarization using PyAnnote
        print("Performing speaker diarization...")
        diarization_result = self.diarization_pipeline(audio_file_path)
        print("Diarization complete.")
        
        # Combine ASR and diarization results
        combined_results = []
        for turn, _, speaker in diarization_result.itertracks(yield_label=True):
            # Find the text segments that overlap with the current speaker turn
            start_time = turn.start
            end_time = turn.end
            segment_text = []
            for segment in result["segments"]:
                segment_start = segment["start"]
                segment_end = segment["end"]
                if segment_start >= start_time and segment_end <= end_time:
                    segment_text.append(segment["text"])
            
            # Combine the text segments for the current speaker turn
            combined_text = " ".join(segment_text).replace("  ", " ").strip()
            if not combined_text:
                continue
            
            # Append the result with timestamps, speaker ID, and text
            combined_results.append({
                "start_time": start_time,
                "end_time": end_time,
                "speaker": speaker,
                "text": combined_text
            })
        
        # return combined_results
        combined_results_str = ""
        for result in combined_results:
            combined_results_str += f"{result['speaker']} ({result['start_time']} - {result['end_time']}): {result['text']}\n"
            
        return combined_results_str.strip()

    def extract_audio_from_video(self, video_file_path, audio_file_path):
        video = mp.VideoFileClip(video_file_path)
        video.audio.write_audiofile(audio_file_path)


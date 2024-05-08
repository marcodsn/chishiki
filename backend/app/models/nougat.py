import torch
from transformers import (
    AutoProcessor,
    VisionEncoderDecoderModel,
    StoppingCriteriaList,
    StoppingCriteria,
)
import fitz  # PyMuPDF
import io
from PIL import Image
from collections import defaultdict


class RunningVarTorch:
    def __init__(self, L=15, norm=False):
        self.values = None
        self.L = L
        self.norm = norm

    def push(self, x: torch.Tensor):
        assert x.dim() == 1
        if self.values is None:
            self.values = x[:, None]
        elif self.values.shape[1] < self.L:
            self.values = torch.cat((self.values, x[:, None]), 1)
        else:
            self.values = torch.cat((self.values[:, 1:], x[:, None]), 1)

    def variance(self):
        if self.values is None:
            return
        if self.norm:
            return torch.var(self.values, 1) / self.values.shape[1]
        else:
            return torch.var(self.values, 1)


class StoppingCriteriaScores(StoppingCriteria):
    def __init__(self, threshold: float = 0.015, window_size: int = 200):
        super().__init__()
        self.threshold = threshold
        self.vars = RunningVarTorch(norm=True)
        self.varvars = RunningVarTorch(L=window_size)
        self.stop_inds = defaultdict(int)
        self.stopped = defaultdict(bool)
        self.size = 0
        self.window_size = window_size

    @torch.no_grad()
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor):
        last_scores = scores[-1]
        self.vars.push(last_scores.max(1)[0].float().cpu())
        self.varvars.push(self.vars.variance())
        self.size += 1
        if self.size < self.window_size:
            return False

        varvar = self.varvars.variance()
        for b in range(len(last_scores)):
            if varvar[b] < self.threshold:
                if self.stop_inds[b] > 0 and not self.stopped[b]:
                    self.stopped[b] = self.stop_inds[b] >= self.size
                else:
                    self.stop_inds[b] = int(
                        min(max(self.size, 1) * 1.15 + 150 + self.window_size, 4095)
                    )
            else:
                self.stop_inds[b] = 0
                self.stopped[b] = False
        return all(self.stopped.values()) and len(self.stopped) > 0


class Nougat:
    def __init__(self, model_name="facebook/nougat-small"):
        # Load the model and processor
        self.processor = AutoProcessor.from_pretrained(model_name)
        
        print("Loading nougat...")
        self.model = VisionEncoderDecoderModel.from_pretrained(model_name)
        print("Model loaded successfully.")
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)

    def rasterize_pdf(self, pdf_input, dpi=96, return_pil=True, is_path=True):
        """
        Convert PDF file to a list of images.
        :param pdf_input: Either a file path or a byte stream of the PDF.
        :param dpi: Resolution for rasterizing the PDF.
        :param return_pil: Return PIL Images if True, otherwise return byte streams.
        :param is_path: True if pdf_input is a file path, False if pdf_input is a byte stream.
        """
        pillow_images = []
        try:
            # Open PDF from path or byte stream
            pdf = fitz.open(pdf_input) if is_path else fitz.open("pdf", pdf_input)
            for page in pdf:
                page_bytes = page.get_pixmap(dpi=dpi).tobytes("png")
                if return_pil:
                    pillow_images.append(io.BytesIO(page_bytes))
        except Exception as e:
            print(f"Failed to rasterize PDF: {e}")
        return pillow_images

    def extract_text(self, pdf_input, is_path=True):
        """
        Extract text from the given PDF input using the Nougat model.
        :param pdf_input: Either a file path or a byte stream of the PDF.
        :param is_path: True if pdf_input is a file path, False if pdf_input is a byte stream.
        """
        images = self.rasterize_pdf(pdf_input, is_path=is_path)
        all_text = []

        for image_stream in images:
            image = Image.open(image_stream)
            # Prepare image for the model
            pixel_values = self.processor(
                images=image, return_tensors="pt"
            ).pixel_values
            pixel_values = pixel_values.to(self.device)

            # Generate text
            outputs = self.model.generate(
                pixel_values,
                min_length=1,
                max_length=3584,
                bad_words_ids=[[self.processor.tokenizer.unk_token_id]],
                return_dict_in_generate=True,
                output_scores=True,
                stopping_criteria=StoppingCriteriaList([StoppingCriteriaScores()]),
            )

            # Decode and postprocess text
            generated_text = self.processor.batch_decode(
                outputs[0], skip_special_tokens=True
            )[0]
            generated_text = self.processor.post_process_generation(
                generated_text, fix_markdown=False
            )
            all_text.append(generated_text)

        return "\n\n".join(all_text)
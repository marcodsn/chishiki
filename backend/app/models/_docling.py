from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode

class Docling:
    def __init__(self):
        print("Loading Docling...")
        pipeline_options = PdfPipelineOptions(do_table_structure=True)
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE  # use more accurate TableFormer model

        self.converter = DocumentConverter(
            format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        print("Docling loaded.")

    def extract_text(self, source: str) -> str:
        """
        Extract text from a PDF file or URL.
        :param source: PDF file path or URL
        """
        result = self.converter.convert(source)
        return result.document.export_to_markdown()

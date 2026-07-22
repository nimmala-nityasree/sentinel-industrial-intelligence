"""
OCR & document text-extraction service.

Design rationale
-----------------
Industrial document corpora are mixed: born-digital PDFs (SOPs exported from
Word), scanned paper forms (near-miss reports filled out by hand and
photographed), and tabular logs (CSV work-order exports). Treating all of
them as "just run OCR" wastes accuracy on clean text and treating all of
them as "just extract text" fails silently on scans (returns empty/garbage
text with no error). This service picks the right path per file and raises
a typed error when extraction confidence is too low to trust downstream.
"""
from pathlib import Path

import pandas as pd
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from pypdf import PdfReader

from app.config import settings
from app.core.exceptions import OCRExtractionError, UnsupportedFileTypeError
from app.core.logging_config import logger

pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

MIN_NATIVE_TEXT_CHARS_PER_PAGE = 40  # below this, assume the PDF page is a scan, not native text
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".csv", ".txt", ".md"}


class OCRService:
    """Extracts clean text from heterogeneous industrial document formats."""

    def extract_text(self, file_path: str) -> tuple[str, bool]:
        """
        Extract text from a document.

        Returns
        -------
        (text, ocr_used): the extracted text, and whether OCR (vs native
        extraction) was required — surfaced to the API/UI so the demo can
        visibly show which documents needed OCR.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFileTypeError(f"Unsupported file type: {suffix}")

        if suffix == ".pdf":
            return self._extract_pdf(path)
        if suffix in {".png", ".jpg", ".jpeg", ".tiff"}:
            return self._extract_image(path), True
        if suffix == ".csv":
            return self._extract_csv(path), False
        if suffix in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="ignore"), False

        raise UnsupportedFileTypeError(f"No handler registered for: {suffix}")

    def _extract_pdf(self, path: Path) -> tuple[str, bool]:
        """
        Try native text extraction first (fast, exact). If the average
        characters-per-page falls below threshold, the PDF is almost
        certainly a scan — fall back to OCR page-by-page.
        """
        try:
            reader = PdfReader(str(path))
            native_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:  # pypdf can raise various parse errors on malformed PDFs
            logger.warning(f"Native PDF extraction failed for {path.name}: {exc}; falling back to OCR")
            native_text = ""

        avg_chars_per_page = len(native_text) / max(len(reader.pages), 1) if native_text else 0

        if avg_chars_per_page >= MIN_NATIVE_TEXT_CHARS_PER_PAGE:
            logger.info(f"{path.name}: native text extraction succeeded ({len(native_text)} chars)")
            return native_text, False

        logger.info(f"{path.name}: native text sparse ({avg_chars_per_page:.0f} chars/page) — running OCR")
        return self._ocr_pdf(path), True

    def _ocr_pdf(self, path: Path) -> str:
        try:
            images = convert_from_path(str(path))
        except Exception as exc:
            raise OCRExtractionError(f"Could not rasterize PDF for OCR: {path.name} ({exc})") from exc

        pages_text = []
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image, lang=settings.ocr_language)
            pages_text.append(text)
            logger.debug(f"{path.name} page {i + 1}: OCR extracted {len(text)} chars")

        full_text = "\n".join(pages_text)
        if len(full_text.strip()) < 20:
            raise OCRExtractionError(
                f"OCR produced near-empty output for {path.name} — document may be illegible"
            )
        return full_text

    def _extract_image(self, path: Path) -> str:
        try:
            image = Image.open(path)
            text = pytesseract.image_to_string(image, lang=settings.ocr_language)
        except Exception as exc:
            raise OCRExtractionError(f"OCR failed for image {path.name}: {exc}") from exc

        if len(text.strip()) < 10:
            raise OCRExtractionError(f"OCR produced near-empty output for {path.name}")
        return text

    def _extract_csv(self, path: Path) -> str:
        """
        Convert tabular work-order / training-record CSVs into a text
        representation the entity-extraction agent can reason over, while
        preserving row structure for downstream parsing.
        """
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            raise OCRExtractionError(f"Could not parse CSV {path.name}: {exc}") from exc

        return df.to_csv(index=False)


ocr_service = OCRService()

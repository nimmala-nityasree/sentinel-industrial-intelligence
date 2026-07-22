"""Unit tests for OCRService's routing logic and error handling on unsupported/corrupt input."""
import pytest

from app.core.exceptions import UnsupportedFileTypeError
from app.services.ocr_service import OCRService


@pytest.fixture
def ocr():
    return OCRService()


def test_txt_file_extracted_directly(tmp_path, ocr):
    file_path = tmp_path / "sop.txt"
    file_path.write_text("Inspect valve V-204 every 180 days.")
    text, ocr_used = ocr.extract_text(str(file_path))
    assert "V-204" in text
    assert ocr_used is False


def test_csv_file_extracted_as_text(tmp_path, ocr):
    file_path = tmp_path / "work_orders.csv"
    file_path.write_text("wo_number,equipment_tag,performed_on\nWO-1,V-204,2024-01-01\n")
    text, ocr_used = ocr.extract_text(str(file_path))
    assert "WO-1" in text
    assert ocr_used is False


def test_unsupported_extension_raises(tmp_path, ocr):
    file_path = tmp_path / "notes.xyz"
    file_path.write_text("irrelevant")
    with pytest.raises(UnsupportedFileTypeError):
        ocr.extract_text(str(file_path))


def test_markdown_file_extracted_directly(tmp_path, ocr):
    file_path = tmp_path / "procedure.md"
    file_path.write_text("# SOP\nInspect every 180 days.")
    text, ocr_used = ocr.extract_text(str(file_path))
    assert "SOP" in text
    assert ocr_used is False

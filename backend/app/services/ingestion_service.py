"""
Document ingestion service.

Handles the mechanical part of ingestion — extract text (OCR if needed),
chunk it, embed and index it — and returns the raw text alongside indexing
stats. The knowledge-graph agent layer then runs entity extraction on the
same raw text and writes structured nodes/relationships. Splitting these
two concerns (mechanical indexing vs. semantic extraction) keeps each
piece independently testable and replaceable.
"""
import uuid
from dataclasses import dataclass

from app.core.logging_config import logger
from app.models.schemas import DocumentType
from app.services.ocr_service import ocr_service
from app.services.vector_store_service import vector_store_service
from app.utils.text_chunking import chunk_text


@dataclass
class IngestionResult:
    document_id: str
    raw_text: str
    chunks_indexed: int
    ocr_used: bool


class IngestionService:
    """Coordinates OCR extraction, chunking, and vector indexing for one document."""

    def ingest(self, file_path: str, filename: str, document_type: DocumentType) -> IngestionResult:
        document_id = str(uuid.uuid4())

        raw_text, ocr_used = ocr_service.extract_text(file_path)
        logger.info(f"Ingesting '{filename}' as {document_id} | ocr_used={ocr_used} | chars={len(raw_text)}")

        chunks = chunk_text(raw_text)
        chunks_indexed = vector_store_service.add_chunks(
            document_id=document_id,
            document_name=filename,
            document_type=document_type,
            chunks=chunks,
        )

        return IngestionResult(
            document_id=document_id,
            raw_text=raw_text,
            chunks_indexed=chunks_indexed,
            ocr_used=ocr_used,
        )


ingestion_service = IngestionService()

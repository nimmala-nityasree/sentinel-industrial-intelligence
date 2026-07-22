"""
Document ingestion API.

A single upload endpoint intentionally orchestrates both the mechanical
ingestion service (OCR/chunk/embed) and the knowledge graph agent
(entity extraction/graph write) — from the caller's perspective, "upload a
document" should be one atomic action, even though internally it's a
two-stage pipeline.
"""
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agents.knowledge_graph_agent import knowledge_graph_agent
from app.core.exceptions import DocumentIngestionError, SentinelException
from app.core.logging_config import logger
from app.models.schemas import DocumentType, DocumentUploadResponse
from app.services.ingestion_service import ingestion_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
) -> DocumentUploadResponse:
    """
    Upload a document (PDF, scanned image, or CSV). Runs OCR if needed,
    indexes it for retrieval, extracts entities, and writes them to the
    knowledge graph — all before returning.
    """
    suffix = Path(file.filename).suffix.lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        ingestion_result = ingestion_service.ingest(
            file_path=tmp_path, filename=file.filename, document_type=document_type
        )

        entities_extracted = knowledge_graph_agent.extract_and_persist(
            document_id=ingestion_result.document_id,
            document_type=document_type,
            text=ingestion_result.raw_text,
        )

        return DocumentUploadResponse(
            document_id=ingestion_result.document_id,
            filename=file.filename,
            document_type=document_type,
            chunks_indexed=ingestion_result.chunks_indexed,
            entities_extracted=entities_extracted,
            ocr_used=ingestion_result.ocr_used,
            message="Document ingested, indexed, and merged into the knowledge graph.",
        )

    except DocumentIngestionError as exc:
        logger.error(f"Ingestion failed for {file.filename}: {exc}")
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SentinelException as exc:
        logger.error(f"Unexpected failure ingesting {file.filename}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

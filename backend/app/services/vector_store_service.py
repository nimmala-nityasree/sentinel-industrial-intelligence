"""
Vector store service (ChromaDB + Gemini embeddings).

Wraps Chroma behind a narrow interface (`add_chunks`, `similarity_search`)
so agents never import chromadb directly. This is what lets us swap Chroma
for FAISS later without touching a single agent file — the agent layer only
knows about this service's public methods.
"""
import uuid

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import settings
from app.core.exceptions import VectorStoreError
from app.core.logging_config import logger
from app.models.schemas import DocumentType, EvidenceCitation


class VectorStoreService:
    """Thin, swappable wrapper around a Chroma collection with Gemini embeddings."""

    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._embedder = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.gemini_api_key,
        )

    def add_chunks(
        self,
        document_id: str,
        document_name: str,
        document_type: DocumentType,
        chunks: list[str],
    ) -> int:
        """Embed and index a list of text chunks belonging to one document."""
        if not chunks:
            return 0
        try:
            embeddings = self._embedder.embed_documents(chunks)
            ids = [f"{document_id}-{i}-{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]
            metadatas = [
                {
                    "document_id": document_id,
                    "document_name": document_name,
                    "document_type": document_type.value,
                    "chunk_index": i,
                }
                for i in range(len(chunks))
            ]
            self._collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
            logger.info(f"Indexed {len(chunks)} chunks for document '{document_name}' ({document_id})")
            return len(chunks)
        except Exception as exc:
            raise VectorStoreError(f"Failed to index chunks for {document_name}: {exc}") from exc

    def similarity_search(
        self, query: str, top_k: int = 5, document_type_filter: str | None = None
    ) -> list[EvidenceCitation]:
        """Return the top-k most semantically relevant chunks as evidence citations."""
        try:
            query_embedding = self._embedder.embed_query(query)
            where = {"document_type": document_type_filter} if document_type_filter else None
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
            )
        except Exception as exc:
            raise VectorStoreError(f"Similarity search failed for query '{query}': {exc}") from exc

        citations: list[EvidenceCitation] = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        for doc_text, meta in zip(docs, metas):
            citations.append(
                EvidenceCitation(
                    document_id=meta.get("document_id", "unknown"),
                    document_name=meta.get("document_name", "unknown"),
                    document_type=DocumentType(meta.get("document_type", "other")),
                    excerpt=doc_text[:300],
                    location=f"chunk {meta.get('chunk_index', '?')}",
                )
            )
        return citations


vector_store_service = VectorStoreService()

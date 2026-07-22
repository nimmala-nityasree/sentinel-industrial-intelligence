"""
Domain-specific exception hierarchy.

Using typed exceptions instead of bare Exception/ValueError lets the API
layer (app/api/*.py) translate failures into precise HTTP responses, and
lets agents catch exactly the failure modes they know how to recover from.
"""


class SentinelException(Exception):
    """Base class for all Sentinel domain exceptions."""


class DocumentIngestionError(SentinelException):
    """Raised when a document cannot be parsed, OCR'd, or chunked."""


class UnsupportedFileTypeError(DocumentIngestionError):
    """Raised when an uploaded document's extension is not supported."""


class OCRExtractionError(DocumentIngestionError):
    """Raised when the OCR engine fails to extract usable text from a scan."""


class GraphWriteError(SentinelException):
    """Raised when a Neo4j write (node/relationship upsert) fails."""


class GraphQueryError(SentinelException):
    """Raised when a Cypher query against the knowledge graph fails."""


class VectorStoreError(SentinelException):
    """Raised when an embedding/upsert/similarity-search operation against Chroma fails."""


class LLMGenerationError(SentinelException):
    """Raised when the Gemini API call fails or returns an unusable response."""


class LowConfidenceAnswerError(SentinelException):
    """
    Raised internally by the RAG Copilot agent when retrieved evidence does not
    meet MIN_ANSWER_CONFIDENCE. Caught by the orchestrator to trigger an
    'escalate to human' response instead of a hallucinated answer.
    """


class AgentExecutionError(SentinelException):
    """Raised when a LangGraph agent node fails during orchestrated execution."""

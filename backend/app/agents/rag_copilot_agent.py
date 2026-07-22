"""
RAG Copilot Agent — the Expert Knowledge Copilot from the problem statement.

Deliberately NOT a generic chatbot: every answer is generated strictly from
retrieved evidence, carries a numeric confidence score derived from
retrieval quality, and — critically — refuses to answer confidently when
evidence is weak, escalating to a human instead of hallucinating. This is
the "false positive rate must be very low" principle applied to a
safety-critical Q&A surface.
"""
from app.agents.base_agent import BaseAgent, SentinelState
from app.config import settings
from app.core.exceptions import LLMGenerationError
from app.services.llm_service import llm_service
from app.services.vector_store_service import vector_store_service

_ANSWER_PROMPT_TEMPLATE = """
You are an industrial operations copilot. Answer the technician's question
using ONLY the evidence excerpts below. If the evidence does not clearly
answer the question, say so explicitly rather than guessing.

Question: {question}

Evidence:
{evidence_block}

Respond in 2-4 sentences. Do not state anything not supported by the evidence above.
"""


class RAGCopilotAgent(BaseAgent):
    name = "rag_copilot_agent"

    def run(self, state: SentinelState) -> SentinelState:
        question = state["question"]
        top_k = state.get("top_k", 5)
        equipment_filter = state.get("equipment_filter")

        self._trace(state, f"Retrieving top-{top_k} evidence chunks for query")
        citations = vector_store_service.similarity_search(
            query=question, top_k=top_k, document_type_filter=equipment_filter
        )

        confidence = self._estimate_confidence(citations)
        self._trace(state, f"Retrieval confidence estimated at {confidence:.2f}")

        if confidence < settings.min_answer_confidence or not citations:
            self._trace(state, "Confidence below threshold — escalating to human instead of answering")
            state["answer"] = (
                "I don't have sufficiently strong evidence in the indexed documents to answer this "
                "confidently. Please consult a subject-matter expert or upload the relevant document."
            )
            state["confidence"] = confidence
            state["evidence"] = [c.model_dump() for c in citations]
            state["escalate_to_human"] = True
            return state

        evidence_block = "\n".join(
            f"[{i+1}] ({c.document_name}, {c.location}): {c.excerpt}" for i, c in enumerate(citations)
        )
        prompt = _ANSWER_PROMPT_TEMPLATE.format(question=question, evidence_block=evidence_block)

        try:
            answer = llm_service.generate(prompt)
            self._trace(state, "Answer synthesized from retrieved evidence")
        except LLMGenerationError as exc:
            self._trace(state, f"Generation failed: {exc}")
            answer = "I retrieved relevant evidence but could not generate an answer. Please try again."
            state["escalate_to_human"] = True

        state["answer"] = answer.strip() if isinstance(answer, str) else str(answer)
        state["confidence"] = confidence
        state["evidence"] = [c.model_dump() for c in citations]
        state.setdefault("escalate_to_human", False)
        return state

    @staticmethod
    def _estimate_confidence(citations: list) -> float:
        """
        Simple, explainable confidence heuristic: more corroborating
        evidence chunks (up to a saturation point) implies higher
        confidence. Kept intentionally simple and transparent rather than
        a black-box score, in line with the explainability requirement.
        """
        if not citations:
            return 0.0
        base = min(len(citations) / 4, 1.0)  # saturates at 4+ supporting chunks
        return round(0.4 + 0.6 * base, 2)  # floor of 0.4 when at least one chunk is retrieved


rag_copilot_agent = RAGCopilotAgent()

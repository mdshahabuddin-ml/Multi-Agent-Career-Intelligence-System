from typing import Dict, List, Any, Optional
from backend.evaluation.base import BaseEvaluator, TestCase, EvaluationResult, EvaluationMetric, MetricType
import re
from collections import Counter


class RAGGenerationEvaluator:
    """Evaluates RAG generation quality including relevance, faithfulness, and coherence."""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.min_relevance = self.config.get("min_relevance", 0.7)
        self.min_faithfulness = self.config.get("min_faithfulness", 0.8)
        self.max_hallucination_rate = self.config.get("max_hallucination_rate", 0.1)

    def evaluate(self, test_case: TestCase, actual_output: Dict) -> Dict:
        """Evaluate RAG generation quality."""
        metrics = []

        query = test_case.input_data.get("query", "")
        retrieved_docs = actual_output.get("retrieved_documents", [])
        generated_answer = actual_output.get("generated_answer", "")
        expected_answer = test_case.expected_output.get("answer", "") if test_case.expected_output else ""

        # Relevance - does answer address the query?
        relevance = self._evaluate_relevance(query, generated_answer)
        metrics.append(self._create_metric(
            "relevance", MetricType.RELEVANCE,
            relevance,
            threshold=self.min_relevance
        ))

        # Faithfulness - is answer supported by retrieved docs?
        faithfulness = self._evaluate_faithfulness(generated_answer, retrieved_docs)
        metrics.append(self._create_metric(
            "faithfulness", MetricType.FACTUALITY,
            faithfulness,
            threshold=self.min_faithfulness
        ))

        # Hallucination rate
        hallucination = self._evaluate_hallucination(generated_answer, retrieved_docs)
        metrics.append(self._create_metric(
            "hallucination_rate", MetricType.FACTUALITY,
            1.0 - hallucination,  # Invert so higher is better
            threshold=1.0 - self.max_hallucination_rate
        ))

        # Answer completeness - covers all aspects of query
        completeness = self._evaluate_completeness(query, generated_answer, expected_answer)
        metrics.append(self._create_metric(
            "completeness", MetricType.COMPLETENESS,
            completeness,
            threshold=0.6
        ))

        # Coherence and fluency
        coherence = self._evaluate_coherence(generated_answer)
        metrics.append(self._create_metric(
            "coherence", MetricType.COHERENCE,
            coherence,
            threshold=0.7
        ))

        # Citation accuracy - are citations correct?
        citation_accuracy = self._evaluate_citation_accuracy(generated_answer, retrieved_docs)
        metrics.append(self._create_metric(
            "citation_accuracy", MetricType.CITATION_QUALITY,
            citation_accuracy,
            threshold=0.7
        ))

        # Conciseness
        conciseness = self._evaluate_conciseness(generated_answer, expected_answer)
        metrics.append(self._create_metric(
            "conciseness", MetricType.USEFULNESS,
            conciseness,
            threshold=0.5
        ))

        passed = all(m.get("passed", False) for m in metrics)
        overall_score = sum(m.get("value", 0) for m in metrics) / len(metrics) if metrics else 0

        return {
            "passed": passed,
            "overall_score": overall_score,
            "metrics": metrics
        }

    def _evaluate_relevance(self, query: str, answer: str) -> float:
        """Evaluate if answer is relevant to query."""
        if not query or not answer:
            return 0.0

        query_terms = set(self._extract_key_terms(query.lower()))
        answer_terms = set(self._extract_key_terms(answer.lower()))

        if not query_terms:
            return 0.5

        overlap = len(query_terms & answer_terms) / len(query_terms)
        return min(overlap * 1.2, 1.0)  # Boost slightly

    def _evaluate_faithfulness(self, answer: str, retrieved_docs: List[Dict]) -> float:
        """Evaluate if answer is faithful to retrieved documents."""
        if not answer or not retrieved_docs:
            return 0.0

        # Combine all retrieved document content
        doc_content = " ".join([doc.get("content", "") for doc in retrieved_docs])
        doc_content = doc_content.lower()

        # Extract claims from answer
        sentences = re.split(r'[.!?]+', answer)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

        if not sentences:
            return 0.5

        supported = 0
        for sentence in sentences:
            # Check if sentence content appears in retrieved docs
            sentence_terms = self._extract_key_terms(sentence.lower())
            if not sentence_terms:
                continue

            matches = sum(1 for term in sentence_terms if term in doc_content)
            if matches / len(sentence_terms) > 0.5:
                supported += 1

        return supported / len(sentences)

    def _evaluate_hallucination(self, answer: str, retrieved_docs: List[Dict]) -> float:
        """Estimate hallucination rate (0 = no hallucination, 1 = all hallucinated)."""
        if not answer:
            return 1.0

        doc_content = " ".join([doc.get("content", "") for doc in retrieved_docs]).lower()

        sentences = re.split(r'[.!?]+', answer)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

        if not sentences:
            return 0.5

        hallucinated = 0
        for sentence in sentences:
            sentence_terms = self._extract_key_terms(sentence.lower())
            if not sentence_terms:
                continue

            matches = sum(1 for term in sentence_terms if term in doc_content)
            if matches / len(sentence_terms) < 0.3:
                hallucinated += 1

        return hallucinated / len(sentences)

    def _evaluate_completeness(self, query: str, answer: str, expected: str = "") -> float:
        """Evaluate if answer covers all aspects of query."""
        if not answer:
            return 0.0

        # If we have expected answer, compare
        if expected:
            expected_terms = set(self._extract_key_terms(expected.lower()))
            answer_terms = set(self._extract_key_terms(answer.lower()))
            if not expected_terms:
                return 0.5
            return len(expected_terms & answer_terms) / len(expected_terms)

        # Otherwise, check query coverage
        query_terms = set(self._extract_key_terms(query.lower()))
        answer_terms = set(self._extract_key_terms(answer.lower()))
        if not query_terms:
            return 0.5

        return len(query_terms & answer_terms) / len(query_terms)

    def _evaluate_coherence(self, answer: str) -> float:
        """Evaluate answer coherence and fluency."""
        if not answer:
            return 0.0

        sentences = re.split(r'[.!?]+', answer)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if len(sentences) < 2:
            return 0.5

        # Check for transition words
        transitions = ["however", "therefore", "furthermore", "additionally", "moreover",
                       "consequently", "nevertheless", "in contrast", "similarly", "meanwhile",
                       "for example", "in particular", "specifically", "in conclusion"]
        transition_count = sum(1 for s in sentences for t in transitions if t in s.lower())

        # Check sentence structure
        avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
        length_score = 1.0 if 8 <= avg_length <= 35 else 0.6

        transition_score = min(transition_count / max(len(sentences) * 0.15, 1), 1.0)

        # Check for repetition
        words = answer.lower().split()
        word_freq = Counter(words)
        repeated = sum(1 for w, c in word_freq.items() if c > 3 and len(w) > 4)
        repetition_penalty = min(repeated * 0.1, 0.3)

        return max(0, (length_score + transition_score) / 2 - repetition_penalty)

    def _evaluate_citation_accuracy(self, answer: str, retrieved_docs: List[Dict]) -> float:
        """Evaluate if citations in answer match retrieved documents."""
        citations = re.findall(r'\[\d+\]', answer)
        if not citations:
            return 0.5 if retrieved_docs else 1.0

        doc_ids = [doc.get("id") or doc.get("url") for doc in retrieved_docs]
        valid_citations = 0

        for citation in citations:
            try:
                idx = int(citation.strip('[]')) - 1
                if 0 <= idx < len(doc_ids):
                    valid_citations += 1
            except:
                pass

        return valid_citations / len(citations) if citations else 0.5

    def _evaluate_conciseness(self, answer: str, expected: str = "") -> float:
        """Evaluate answer conciseness."""
        if not answer:
            return 0.0

        answer_len = len(answer.split())
        expected_len = len(expected.split()) if expected else 100

        # Optimal range is around expected length
        if expected_len > 0:
            ratio = answer_len / expected_len
            if 0.5 <= ratio <= 2.0:
                return 1.0
            elif ratio < 0.5:
                return ratio * 2  # Too short
            else:
                return max(0.3, 2.0 - ratio)  # Too long
        else:
            # Default: prefer 50-300 words
            if 50 <= answer_len <= 300:
                return 1.0
            elif answer_len < 50:
                return answer_len / 50
            else:
                return max(0.3, 300 / answer_len)

    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text."""
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
                      "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
                      "have", "has", "had", "do", "does", "did", "will", "would", "could",
                      "should", "may", "might", "must", "can", "this", "that", "these", "those",
                      "i", "you", "he", "she", "it", "we", "they", "what", "which", "who",
                      "how", "when", "where", "why", "my", "your", "his", "her", "its", "our", "their"}

        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        return [w for w in words if w not in stop_words]

    def _create_metric(self, name: str, metric_type: MetricType, value: float,
                       max_value: float = 1.0, threshold: float = 0.7,
                       unit: str = "", metadata: Dict = None) -> Dict:
        return {
            "name": name,
            "type": metric_type.value,
            "value": value,
            "max_value": max_value,
            "threshold": threshold,
            "passed": value >= threshold,
            "percentage": (value / max_value) * 100 if max_value > 0 else 0,
            "unit": unit,
            "metadata": metadata or {}
        }


class AnswerRelevanceEvaluator:
    """Specific evaluator for answer relevance to user query."""

    def __init__(self, config: Dict = None):
        self.config = config or {}

    def evaluate(self, test_case: TestCase, actual_output: Dict) -> Dict:
        query = test_case.input_data.get("query", "")
        answer = actual_output.get("generated_answer", "")

        # Use semantic similarity or keyword overlap
        relevance = self._keyword_relevance(query, answer)

        metric = self._create_metric(
            "answer_relevance", MetricType.RELEVANCE,
            relevance,
            threshold=0.6
        )

        return {
            "passed": metric["passed"],
            "overall_score": relevance,
            "metrics": [metric]
        }

    def _keyword_relevance(self, query: str, answer: str) -> float:
        query_terms = set(self._extract_key_terms(query.lower()))
        answer_terms = set(self._extract_key_terms(answer.lower()))
        if not query_terms:
            return 0.5
        return len(query_terms & answer_terms) / len(query_terms)

    def _extract_key_terms(self, text: str) -> List[str]:
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
                      "of", "with", "by", "from", "is", "are", "was", "were", "be", "been"}
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        return [w for w in words if w not in stop_words]

    def _create_metric(self, name: str, metric_type: MetricType, value: float,
                       max_value: float = 1.0, threshold: float = 0.7,
                       unit: str = "", metadata: Dict = None) -> Dict:
        return {
            "name": name,
            "type": metric_type.value,
            "value": value,
            "max_value": max_value,
            "threshold": threshold,
            "passed": value >= threshold,
            "percentage": (value / max_value) * 100 if max_value > 0 else 0,
            "unit": unit,
            "metadata": metadata or {}
        }
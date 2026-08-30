from typing import Dict, List, Any, Optional
from backend.evaluation.base import BaseEvaluator, TestCase, EvaluationResult, EvaluationMetric, MetricType
from datetime import datetime


class RetrievalEvaluator:
    """Evaluates RAG retrieval quality."""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.k_values = self.config.get("k_values", [1, 3, 5, 10])
        self.relevance_threshold = self.config.get("relevance_threshold", 0.7)
    
    def evaluate(self, test_case, actual_output: Dict) -> Dict:
        """Evaluate retrieval quality."""
        # Extract retrieved documents and ground truth
        retrieved_docs = actual_output.get("retrieved_documents", [])
        relevant_docs = test_case.expected_output.get("relevant_documents", [])
        
        if not relevant_docs:
            return self._empty_result("No relevant documents in ground truth")
        
        # Calculate metrics
        metrics = []
        
        # Precision@K
        for k in self.k_values:
            precision = self._precision_at_k(retrieved_docs, relevant_docs, k)
            metrics.append({
                "name": f"precision@{k}",
                "type": "retrieval",
                "value": precision,
                "threshold": 0.5,
                "passed": precision >= 0.5
            })
        
        # Recall@K
        for k in self.k_values:
            recall = self._recall_at_k(retrieved_docs, relevant_docs, k)
            metrics.append({
                "name": f"recall@{k}",
                "type": "retrieval",
                "value": recall,
                "threshold": 0.5,
                "passed": recall >= 0.5
            })
        
        # MRR
        mrr = self._mean_reciprocal_rank(retrieved_docs, relevant_docs)
        metrics.append({
            "name": "mrr",
            "type": "retrieval",
            "value": mrr,
            "threshold": 0.5,
            "passed": mrr >= 0.5
        })
        
        # NDCG
        ndcg = self._ndcg_at_k(retrieved_docs, relevant_docs, 10)
        metrics.append({
            "name": "ndcg@10",
            "type": "retrieval",
            "value": ndcg,
            "threshold": 0.5,
            "passed": ndcg >= 0.5
        })
        
        passed = all(m.get("passed", False) for m in metrics)
        overall_score = sum(m.get("value", 0) for m in metrics) / len(metrics) if metrics else 0
        
        return {
            "passed": passed,
            "overall_score": sum(m.get("value", 0) for m in metrics) / len(metrics) if metrics else 0,
            "metrics": metrics
        }
    
    def _precision_at_k(self, retrieved: List[Dict], relevant: List[str], k: int) -> float:
        """Calculate precision@k."""
        if k == 0:
            return 0.0
        retrieved_ids = [doc.get("id") or doc.get("url") for doc in retrieved[:k]]
        relevant_set = set(relevant)
        hits = sum(1 for rid in retrieved_ids if rid in relevant_set)
        return hits / k
    
    def _recall_at_k(self, retrieved: List[Dict], relevant: List[str], k: int) -> float:
        """Calculate recall@k."""
        if not relevant:
            return 0.0
        retrieved_ids = [doc.get("id") or doc.get("url") for doc in retrieved[:k]]
        relevant_set = set(relevant)
        hits = sum(1 for rid in retrieved_ids if rid in relevant_set)
        return hits / len(relevant)
    
    def _mean_reciprocal_rank(self, retrieved: List[Dict], relevant: List[str]) -> float:
        """Calculate Mean Reciprocal Rank."""
        relevant_set = set(relevant)
        for i, doc in enumerate(retrieved):
            doc_id = doc.get("id") or doc.get("url")
            if doc_id in relevant_set:
                return 1.0 / (i + 1)
        return 0.0
    
    def _ndcg_at_k(self, retrieved: List[Dict], relevant: List[str], k: int) -> float:
        """Calculate NDCG@K (simplified)."""
        relevant_set = set(relevant)
        dcg = 0.0
        for i, doc in enumerate(retrieved[:k]):
            doc_id = doc.get("id") or doc.get("url")
            if doc_id in relevant_set:
                dcg += 1.0 / (i + 1)
        
        # Ideal DCG
        idcg = sum(1.0 / (i + 1) for i in range(min(len(relevant), len(retrieved))))
        return dcg / idcg if idcg > 0 else 0.0
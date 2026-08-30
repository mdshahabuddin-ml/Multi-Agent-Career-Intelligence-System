"""
Mock research collector for development and testing.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from backend.data_pipeline.collectors.base_collector import BaseCollector, RawDataRecord, CollectorHealth


class MockResearchCollector(BaseCollector):
    """Mock research collector for development/testing."""
    
    MOCK_RESEARCH = [
        {
            "title": "Attention Is All You Need",
            "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones", "Aidan N. Gomez", "Lukasz Kaiser", "Illia Polosukhin"],
            "abstract": "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
            "content": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks in an encoder-decoder configuration. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8.",
            "source_document_id": "mock_research_1",
            "source_url": "https://arxiv.org/abs/1706.03762",
            "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones", "Aidan N. Gomez", "Lukasz Kaiser", "Illia Polosukhin"],
            "publication_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "research_type": "academic_paper",
            "topics": ["ai_ml", "nlp"],
            "keywords": ["attention", "transformer", "neural network", "machine translation", "sequence transduction"],
            "technologies_mentioned": ["transformer", "attention mechanism", "neural network", "machine learning"],
            "doi": "10.48550/arXiv.1706.03762",
            "venue": "NeurIPS 2017",
            "citation_count": 100000,
            "quality_score": 0.98,
        },
        {
            "title": "Scaling Laws for Neural Language Models",
            "authors": ["Jared Kaplan", "Sam McCandlish", "Tom Henighan", "Tom B. Brown", "Benjamin Chess", "Rebekah Child", "Scott Gray", "Alec Radford", "Jeffrey Wu", "Dario Amodei"],
            "abstract": "We study empirical scaling laws for language model performance on the cross-entropy loss. The loss scales as a power-law with model size, dataset size, and the amount of compute used for training, with some trends spanning more than seven orders of magnitude.",
            "content": "We study empirical scaling laws for language model performance on the cross-entropy loss. The loss scales as a power-law with model size, dataset size, and the amount of compute used for training, with some trends spanning more than seven orders of magnitude. Other architectural details such as network width or depth have minimal effects within a wide range. Simple equations govern the dependence of overfitting on model/dataset size and the dependence of training speed on model size. These relationships allow precise predictions of the performance gains from increased investment in model training.",
            "source_document_id": "mock_research_2",
            "source_url": "https://arxiv.org/abs/2001.08361",
            "authors": ["Jared Kaplan", "Sam McCandlish", "Tom Henighan", "Tom B. Brown", "Benjamin Chess", "Rebekah Child", "Scott Gray", "Alec Radford", "Jeffrey Wu", "Dario Amodei"],
            "publication_date": (datetime.utcnow() - timedelta(days=60)).isoformat(),
            "research_type": "academic_paper",
            "topics": ["ai_ml", "nlp"],
            "keywords": ["scaling laws", "language models", "neural networks", "compute", "training dynamics"],
            "technologies_mentioned": ["language models", "transformer", "deep learning", "neural networks"],
            "doi": "10.48550/arXiv.2001.08361",
            "venue": "ArXiv",
            "citation_count": 15000,
            "quality_score": 0.95,
        },
        {
            "title": "Building LLM Applications with RAG: A Practical Guide",
            "authors": ["Harrison Chase", "LangChain Team"],
            "abstract": "Retrieval-Augmented Generation (RAG) combines the power of large language models with external knowledge retrieval. This guide covers practical implementation patterns for building production RAG systems.",
            "content": "Retrieval-Augmented Generation (RAG) has emerged as the dominant paradigm for building LLM applications that require up-to-date or domain-specific knowledge. This practical guide covers the complete RAG pipeline: document ingestion, chunking strategies, embedding models, vector databases, retrieval algorithms, and generation techniques. We discuss common pitfalls like chunk size optimization, retrieval quality evaluation, and handling hallucinations. Code examples using LangChain and popular vector stores (Pinecone, Weaviate, Chroma) demonstrate production-ready patterns. We also cover advanced techniques like query rewriting, hybrid search, re-ranking, and citation generation.",
            "source_document_id": "mock_research_3",
            "source_url": "https://blog.langchain.dev/building-llm-applications-with-rag/",
            "authors": ["Harrison Chase"],
            "publication_date": (datetime.utcnow() - timedelta(days=15)).isoformat(),
            "research_type": "technical_blog",
            "topics": ["ai_ml", "nlp", "mlops"],
            "keywords": ["RAG", "retrieval augmented generation", "LLM", "vector database", "embedding", "langchain"],
            "technologies_mentioned": ["langchain", "vector database", "embedding", "llm", "rag", "pinecone", "weaviate", "chroma"],
            "doi": None,
            "venue": "LangChain Blog",
            "citation_count": None,
            "quality_score": 0.9,
        },
        {
            "title": "Kubernetes at Scale: Lessons from Running 10,000+ Clusters",
            "authors": ["Kelsey Hightower", "Google Cloud Team"],
            "abstract": "Operating Kubernetes at massive scale requires careful attention to control plane architecture, etcd performance, networking, and multi-tenancy. We share hard-won lessons from managing tens of thousands of clusters.",
            "content": "Running Kubernetes at scale presents unique challenges that don't appear in smaller deployments. Control plane scalability becomes critical - we discuss etcd optimization, API server tuning, and scheduler improvements. Networking at scale requires CNI plugin selection, IP address management, and service discovery optimization. Multi-tenancy isolation involves namespace strategies, resource quotas, and admission controllers. We cover monitoring and observability patterns including custom metrics, distributed tracing, and alerting strategies. Cost optimization techniques include bin packing, spot instance utilization, and cluster autoscaling. These lessons apply to any organization operating Kubernetes beyond a few dozen clusters.",
            "source_document_id": "mock_research_4",
            "source_url": "https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-at-scale-lessons-learned",
            "authors": ["Kelsey Hightower"],
            "publication_date": (datetime.utcnow() - timedelta(days=45)).isoformat(),
            "research_type": "technical_blog",
            "topics": ["cloud_native", "distributed_systems", "performance"],
            "keywords": ["kubernetes", "control plane", "etcd", "networking", "multi-tenancy", "observability", "cost optimization"],
            "technologies_mentioned": ["kubernetes", "etcd", "cni", "prometheus", "grafana", "istio", "cilium", "gke"],
            "doi": None,
            "venue": "Google Cloud Blog",
            "citation_count": None,
            "quality_score": 0.92,
        },
        {
            "title": "The State of AI in 2024: Enterprise Adoption Report",
            "authors": ["McKinsey Global Institute"],
            "abstract": "Annual survey of 2,500+ executives reveals AI adoption has reached 72% across industries, with generative AI driving unprecedented investment and organizational change.",
            "content": "AI adoption has reached a tipping point. Our 2024 survey of 2,500 executives across 15 industries shows 72% of organizations now use AI in at least one business function, up from 55% in 2023. Generative AI is the primary driver, with 65% of organizations regularly using gen AI tools. Investment has surged - 40% of respondents report increased AI budgets. However, challenges remain: talent shortage (cited by 58%), data quality (47%), and governance concerns (43%). The report examines use cases by industry, ROI measurement, risk mitigation strategies, and the evolving regulatory landscape. High-performing organizations share common characteristics: clear AI strategy, strong data foundations, and dedicated AI governance.",
            "source_document_id": "mock_research_5",
            "source_url": "https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai-in-2024",
            "authors": ["McKinsey Global Institute"],
            "publication_date": (datetime.utcnow() - timedelta(days=10)).isoformat(),
            "research_type": "industry_report",
            "topics": ["ai_ml", "hiring"],
            "keywords": ["AI adoption", "generative AI", "enterprise AI", "ROI", "governance", "talent", "investment"],
            "technologies_mentioned": ["generative AI", "LLM", "machine learning", "data science"],
            "doi": None,
            "venue": "McKinsey Global Institute",
            "citation_count": None,
            "quality_score": 0.88,
        },
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._source_name = "mock_research"
        self._source_type = "internal_database"
        self._delay = self.config.get("delay", 0.1)
        self._failure_rate = self.config.get("failure_rate", 0.0)
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    @property
    def source_type(self) -> str:
        return self._source_type

    async def fetch(self, query: str = "", research_type: Optional[str] = None, 
                    topic: Optional[str] = None, days_back: int = 365,
                    limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """Return mock research data for testing."""
        await asyncio.sleep(self._delay)
        
        if self._failure_rate > 0 and random.random() < self._failure_rate:
            raise ConnectionError("Simulated collector failure")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        filtered = []
        query_lower = query.lower()
        
        for research in self.MOCK_RESEARCH:
            pub_date_str = research.get("publication_date")
            if pub_date_str:
                try:
                    pub_date = datetime.fromisoformat(pub_date_str)
                    if pub_date < cutoff_date:
                        continue
                except Exception:
                    pass
            
            if query_lower and not (
                query_lower in research["title"].lower() or
                query_lower in research["abstract"].lower() or
                any(query_lower in k.lower() for k in research.get("keywords", []))
            ):
                continue
            
            if research_type and research_type != research.get("research_type"):
                continue
            
            if topic and topic not in research.get("topics", []):
                continue
            
            filtered.append(research.copy())
            
            if len(filtered) >= limit:
                break
        
        return filtered

    async def parse(self, raw_data: List[Dict[str, Any]]) -> List[RawDataRecord]:
        """Parse raw mock data into RawDataRecord objects."""
        records = []
        for research in raw_data:
            record = RawDataRecord.create(
                source_id="mock_research",
                source_name="Mock Research Provider",
                source_type="internal_database",
                external_id=research["source_document_id"],
                source_url=research["source_url"],
                raw_payload=research,
                metadata={"mock": True}
            )
            records.append(record)
        return records

    async def health_check(self) -> CollectorHealth:
        """Mock collector is always healthy."""
        return CollectorHealth.HEALTHY
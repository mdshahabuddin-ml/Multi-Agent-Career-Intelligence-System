from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum as PyEnum
import json
import asyncio
from abc import ABC, abstractmethod

from backend.evaluation.base import EvaluationMetric, MetricType, BaseEvaluator, TestCase
from backend.config import settings


class JudgeModel(str, PyEnum):
    """Available judge models."""
    GPT4O_MINI = "gpt-4o-mini"
    GPT4O = "gpt-4o"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    LOCAL = "local"


@dataclass
class JudgeConfig:
    """Configuration for LLM judge."""
    model: JudgeModel = JudgeModel.GPT4O_MINI
    temperature: float = 0.0
    max_tokens: int = 1000
    system_prompt: str = ""
    few_shot_examples: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class JudgeResult:
    """Result from LLM judge evaluation."""
    score: float
    reasoning: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMJudgeBase(ABC):
    """Abstract base class for LLM-as-a-Judge evaluators."""

    def __init__(self, config: Optional[JudgeConfig] = None):
        self.config = config or JudgeConfig()
        self._client = None

    @abstractmethod
    async def evaluate(self, **kwargs) -> JudgeResult:
        """Evaluate using LLM judge."""
        pass

    def _build_prompt(self, template: str, **kwargs) -> str:
        """Build evaluation prompt from template."""
        return template.format(**kwargs)

    async def _call_llm(self, prompt: str, system_prompt: str = "") -> str:
        """Call LLM with prompt."""
        if settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            if self._client is None:
                self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            messages = []
            if system_prompt or self.config.system_prompt:
                messages.append({"role": "system", "content": system_prompt or self.config.system_prompt})
            
            for ex in self.config.few_shot_examples:
                messages.append({"role": "user", "content": ex.get("input", "")})
                messages.append({"role": "assistant", "content": ex.get("output", "")})
            
            messages.append({"role": "user", "content": prompt})
            
            response = await self._client.chat.completions.create(
                model=self.config.model.value,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return response.choices[0].message.content
        else:
            return json.dumps({"score": 0.5, "reasoning": "Mock evaluation - no API key", "confidence": 0.0})


class HallucinationJudge(LLMJudgeBase):
    """Detect hallucinations in generated content against source documents."""

    SYSTEM_PROMPT = """You are an expert evaluator detecting hallucinations in AI-generated content.
Your task is to compare the generated answer against the provided source documents and identify any claims that are not supported by the sources.

A hallucination is any claim, fact, or statement in the answer that:
1. Contradicts the source documents
2. Cannot be verified from the source documents
3. Adds information not present in the sources

Rate the hallucination level from 0.0 (no hallucinations) to 1.0 (severe hallucinations).
Provide specific examples of any hallucinations found."""

    EVALUATION_PROMPT = """Source Documents:
{sources}

Generated Answer:
{answer}

Evaluate the answer for hallucinations. Return a JSON object with:
- "score": float between 0.0 and 1.0 (0 = no hallucinations, 1 = severe hallucinations)
- "reasoning": detailed explanation of findings
- "confidence": float between 0.0 and 1.0
- "hallucinations": list of specific hallucinated claims (empty if none)
- "unsupported_claims": list of claims not in sources (empty if none)"""

    async def evaluate(self, answer: str, sources: List[str], **kwargs) -> JudgeResult:
        sources_text = "\n\n---\n\n".join(sources) if sources else "No sources provided."
        prompt = self._build_prompt(self.EVALUATION_PROMPT, sources=sources_text, answer=answer)
        
        response = await self._call_llm(prompt, self.SYSTEM_PROMPT)
        
        try:
            result = json.loads(response)
            return JudgeResult(
                score=1.0 - result.get("score", 0.5),
                reasoning=result.get("reasoning", ""),
                confidence=result.get("confidence", 0.5),
                metadata={
                    "hallucinations": result.get("hallucinations", []),
                    "unsupported_claims": result.get("unsupported_claims", []),
                }
            )
        except json.JSONDecodeError:
            return JudgeResult(
                score=0.5,
                reasoning="Failed to parse judge response",
                confidence=0.0,
                metadata={"raw_response": response}
            )


class FaithfulnessJudge(LLMJudgeBase):
    """Evaluate faithfulness of answer to source documents."""

    SYSTEM_PROMPT = """You are an expert evaluator assessing the faithfulness of AI-generated answers to source documents.
Faithfulness measures whether the answer accurately represents the information in the sources without distortion, omission of critical details, or misleading interpretations.

A faithful answer:
1. Accurately reflects the source information
2. Does not misrepresent or distort facts
3. Includes important caveats and limitations from sources
4. Does not cherry-pick only favorable information

Rate faithfulness from 0.0 (unfaithful) to 1.0 (completely faithful)."""

    EVALUATION_PROMPT = """Source Documents:
{sources}

Generated Answer:
{answer}

Question/Task: {question}

Evaluate the faithfulness of the answer to the sources. Consider:
1. Are all claims in the answer supported by the sources?
2. Are important details from sources omitted?
3. Are there any misleading interpretations?
4. Are caveats and limitations preserved?

Return a JSON object with:
- "score": float between 0.0 and 1.0
- "reasoning": detailed explanation
- "confidence": float between 0.0 and 1.0
- "supported_claims": list of claims well-supported by sources
- "omitted_details": list of important details from sources not in answer
- "distortions": list of any distorted or misleading statements"""

    async def evaluate(self, answer: str, sources: List[str], question: str = "", **kwargs) -> JudgeResult:
        sources_text = "\n\n---\n\n".join(sources) if sources else "No sources provided."
        prompt = self._build_prompt(self.EVALUATION_PROMPT, sources=sources_text, answer=answer, question=question)
        
        response = await self._call_llm(prompt, self.SYSTEM_PROMPT)
        
        try:
            result = json.loads(response)
            return JudgeResult(
                score=result.get("score", 0.5),
                reasoning=result.get("reasoning", ""),
                confidence=result.get("confidence", 0.5),
                metadata={
                    "supported_claims": result.get("supported_claims", []),
                    "omitted_details": result.get("omitted_details", []),
                    "distortions": result.get("distortions", []),
                }
            )
        except json.JSONDecodeError:
            return JudgeResult(
                score=0.5,
                reasoning="Failed to parse judge response",
                confidence=0.0,
                metadata={"raw_response": response}
            )


class RelevanceJudge(LLMJudgeBase):
    """Evaluate relevance of answer to the question/task."""

    SYSTEM_PROMPT = """You are an expert evaluator assessing the relevance of AI-generated answers to the given question or task.
Relevance measures whether the answer directly addresses the question, stays on topic, and provides useful information.

A relevant answer:
1. Directly addresses the question asked
2. Stays focused on the topic
3. Provides actionable or useful information
4. Does not go off on tangents
5. Matches the expected format and depth

Rate relevance from 0.0 (irrelevant) to 1.0 (highly relevant)."""

    EVALUATION_PROMPT = """Question/Task:
{question}

Generated Answer:
{answer}

Context (optional): {context}

Evaluate the relevance of the answer. Consider:
1. Does the answer directly address the question?
2. Is the answer on-topic and focused?
3. Does it provide useful, actionable information?
4. Is the depth and format appropriate?
5. Are there irrelevant tangents or off-topic content?

Return a JSON object with:
- "score": float between 0.0 and 1.0
- "reasoning": detailed explanation
- "confidence": float between 0.0 and 1.0
- "addressed_aspects": list of question aspects addressed
- "missing_aspects": list of question aspects not addressed
- "irrelevant_content": any off-topic or tangential content"""

    async def evaluate(self, answer: str, question: str, context: str = "", **kwargs) -> JudgeResult:
        prompt = self._build_prompt(self.EVALUATION_PROMPT, question=question, answer=answer, context=context)
        
        response = await self._call_llm(prompt, self.SYSTEM_PROMPT)
        
        try:
            result = json.loads(response)
            return JudgeResult(
                score=result.get("score", 0.5),
                reasoning=result.get("reasoning", ""),
                confidence=result.get("confidence", 0.5),
                metadata={
                    "addressed_aspects": result.get("addressed_aspects", []),
                    "missing_aspects": result.get("missing_aspects", []),
                    "irrelevant_content": result.get("irrelevant_content", []),
                }
            )
        except json.JSONDecodeError:
            return JudgeResult(
                score=0.5,
                reasoning="Failed to parse judge response",
                confidence=0.0,
                metadata={"raw_response": response}
            )


class CompletenessJudge(LLMJudgeBase):
    """Evaluate completeness of answer relative to requirements."""

    SYSTEM_PROMPT = """You are an expert evaluator assessing the completeness of AI-generated answers.
Completeness measures whether the answer covers all required aspects, provides sufficient depth, and addresses the full scope of the question.

A complete answer:
1. Addresses all parts of the question
2. Provides sufficient detail for each part
3. Covers the expected scope
4. Doesn't leave critical gaps

Rate completeness from 0.0 (incomplete) to 1.0 (comprehensive)."""

    EVALUATION_PROMPT = """Question/Task:
{question}

Expected Coverage (if specified): {expected_coverage}

Generated Answer:
{answer}

Evaluate the completeness of the answer. Consider:
1. Are all parts of the question addressed?
2. Is the depth sufficient for each part?
3. Are there critical gaps or missing information?
4. Does it meet the expected scope?

Return a JSON object with:
- "score": float between 0.0 and 1.0
- "reasoning": detailed explanation
- "confidence": float between 0.0 and 1.0
- "covered_parts": list of question parts addressed
- "missing_parts": list of question parts not addressed
- "depth_assessment": "insufficient" | "adequate" | "comprehensive" """

    async def evaluate(self, answer: str, question: str, expected_coverage: str = "", **kwargs) -> JudgeResult:
        prompt = self._build_prompt(self.EVALUATION_PROMPT, question=question, answer=answer, expected_coverage=expected_coverage)
        
        response = await self._call_llm(prompt, self.SYSTEM_PROMPT)
        
        try:
            result = json.loads(response)
            return JudgeResult(
                score=result.get("score", 0.5),
                reasoning=result.get("reasoning", ""),
                confidence=result.get("confidence", 0.5),
                metadata={
                    "covered_parts": result.get("covered_parts", []),
                    "missing_parts": result.get("missing_parts", []),
                    "depth_assessment": result.get("depth_assessment", "adequate"),
                }
            )
        except json.JSONDecodeError:
            return JudgeResult(
                score=0.5,
                reasoning="Failed to parse judge response",
                confidence=0.0,
                metadata={"raw_response": response}
            )


class LLMAssistedEvaluator(BaseEvaluator):
    """LLM-assisted evaluator combining multiple judges."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)
        judge_config = JudgeConfig(
            model=JudgeModel(config.get("judge_model", "gpt-4o-mini")) if config else JudgeModel.GPT4O_MINI,
            temperature=config.get("temperature", 0.0) if config else 0.0,
        )
        
        self.hallucination_judge = HallucinationJudge(judge_config)
        self.faithfulness_judge = FaithfulnessJudge(judge_config)
        self.relevance_judge = RelevanceJudge(judge_config)
        self.completeness_judge = CompletenessJudge(judge_config)
        
        self.weights = config.get("weights", {
            "hallucination": 0.3,
            "faithfulness": 0.3,
            "relevance": 0.25,
            "completeness": 0.15,
        }) if config else {
            "hallucination": 0.3,
            "faithfulness": 0.3,
            "relevance": 0.25,
            "completeness": 0.15,
        }

    async def evaluate(self, test_case: TestCase, actual_output: Dict[str, Any]) -> Any:
        """Run all judges and combine results."""
        answer = actual_output.get("answer", "")
        sources = actual_output.get("sources", [])
        question = test_case.input_data.get("question", test_case.input_data.get("query", ""))
        
        # Run all judges in parallel
        results = await asyncio.gather(
            self.hallucination_judge.evaluate(answer=answer, sources=sources),
            self.faithfulness_judge.evaluate(answer=answer, sources=sources, question=question),
            self.relevance_judge.evaluate(answer=answer, question=question),
            self.completeness_judge.evaluate(answer=answer, question=question),
            return_exceptions=True
        )
        
        # Handle exceptions
        judge_results = {}
        judge_names = ["hallucination", "faithfulness", "relevance", "completeness"]
        for i, (name, result) in enumerate(zip(judge_names, results)):
            if isinstance(result, Exception):
                judge_results[name] = JudgeResult(score=0.0, reasoning=f"Judge failed: {result}", confidence=0.0)
            else:
                judge_results[name] = result
        
        # Calculate weighted score
        weighted_score = sum(
            judge_results[name].score * self.weights.get(name, 0)
            for name in judge_names
        )
        
        # Create metrics
        metrics = []
        for name in judge_names:
            jr = judge_results[name]
            metrics.append(EvaluationMetric(
                name=name,
                metric_type=MetricType.FACTUALITY if name in ["hallucination", "faithfulness"] else MetricType.RELEVANCE if name == "relevance" else MetricType.COMPLETENESS,
                value=jr.score,
                max_value=1.0,
                threshold=0.7,
                metadata=jr.metadata
            ))
        
        # Overall metric
        metrics.append(EvaluationMetric(
            name="overall_quality",
            metric_type=MetricType.ACCURACY,
            value=weighted_score,
            max_value=1.0,
            threshold=0.7,
            metadata={name: jr.score for name, jr in judge_results.items()}
        ))
        
        from backend.evaluation.base import EvaluationResult
        return EvaluationResult(
            test_case_id=test_case.test_case_id,
            test_case_name=test_case.name,
            level=test_case.level,
            metrics=metrics,
            passed=all(m.passed for m in metrics),
            overall_score=weighted_score,
            duration_ms=0,
        )
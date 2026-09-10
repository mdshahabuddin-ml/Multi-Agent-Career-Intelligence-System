"""Career-to-Content pipeline orchestrator (backend stages 1-7).

Pipeline: career intake (resume/profile/project/certification/achievement/
research/learning) -> Hermes task routing -> topic selection -> content
research -> LLM generation -> fact/quality gate (incl. entity grounding) ->
platform formatting (incl. captions) -> human approval.

Scheduling, social publishing, and analytics collection are intentionally
out of scope here (deferred stages); approved runs expose formatted,
review-ready content that those stages will consume.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.content_engine.generation import career_templates
from backend.content_engine.transformation.platform_drafts import PlatformDraftBuilder
from backend.content_engine.generation.llm_generator import CareerContentGenerator
from backend.content_engine.generation.topic_selector import pick_topic
from backend.content_engine.quality.pipeline_verifier import PipelineVerifier
from backend.content_engine.transformation.platform_formatter import PlatformFormatter
from backend.hermes_engine.delegation.task_router import TaskRouter
from backend.hermes_engine.supervisor.intent_router import Intent
from backend.models.achievement import Achievement
from backend.models.certification import Certification
from backend.models.content_pipeline_run import (
    ContentKind,
    ContentPipelineRun,
    PipelineSource,
    PipelineStage,
)
from backend.models.experience import Experience
from backend.models.learning_plan import LearningPlan
from backend.models.profile import Profile
from backend.models.project import Project
from backend.models.research import Research
from backend.models.resume import Resume
from backend.models.skill import Skill
from backend.models.user import User
from backend.providers.search.base import SearchConfig
from backend.providers.search.mock import MockSearchProvider

logger = logging.getLogger(__name__)


def default_search_provider():
    """Real keyed search provider when configured, else offline-safe Mock."""
    try:
        from backend.providers.config import load_search_settings
        from backend.providers.search import get_search_registry

        settings = load_search_settings()
        default = settings.default_provider
        entry = settings.providers.get(default)
        if entry is not None and getattr(entry, "api_key", None):
            registry = get_search_registry()
            provider_class = registry.get_provider_class(default)
            if provider_class is not None:
                return provider_class(api_key=entry.api_key, base_url=entry.api_base)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Search provider resolution failed (%s); using Mock provider", exc)
    return MockSearchProvider()

# Platforms with first-class formatting support in this stage set.
SUPPORTED_PLATFORMS = ("linkedin", "instagram", "facebook", "youtube", "youtube_shorts", "tiktok", "short")

# Content kinds that benefit from attached web research.
RESEARCH_BACKED_KINDS = {ContentKind.EDUCATIONAL, ContentKind.LINKEDIN_POST}


class CareerContentService:
    """Build career-grounded, human-approved content drafts."""

    def __init__(
        self,
        db: Session,
        llm_provider=None,
        search_provider=None,
        task_router: Optional[TaskRouter] = None,
    ):
        self.db = db
        self.generator = CareerContentGenerator(provider=llm_provider)
        self.verifier = PipelineVerifier()
        self.formatter = PlatformFormatter()
        self.drafts = PlatformDraftBuilder(self.formatter)
        self.search = search_provider or default_search_provider()
        self.router = task_router or self._default_router()

    # ------------------------------------------------------------------
    # Hermes engine integration (extension point, engine itself untouched)
    # ------------------------------------------------------------------
    def _default_router(self) -> TaskRouter:
        router = TaskRouter()
        router.register("career_content.topics", self._stage_topics)
        router.register("career_content.guard", self._stage_guard)
        router.register("career_content.research", self._stage_research)
        router.register("career_content.generate", self._stage_generate)
        router.register("career_content.verify", self._stage_verify)
        router.register("career_content.format", self._stage_format)
        router.set_fallback(self._stage_unhandled)
        return router

    @staticmethod
    async def _stage_unhandled(task: Dict[str, Any]) -> Dict[str, Any]:
        raise ValueError(f"No handler registered for task type: {task.get('type')}")

    # ------------------------------------------------------------------
    # Stage 1: intake
    # ------------------------------------------------------------------
    def build_brief(self, user_id: int, source: PipelineSource, source_id: Optional[int] = None) -> Dict[str, Any]:
        """Aggregate the user's career material into a generation brief."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()

        brief: Dict[str, Any] = {
            "name": user.full_name or user.email.split("@")[0],
            "headline": (profile.headline if profile else None),
            "target_role": (profile.target_role if profile else None),
            "skills": [],
            "highlight": "",
            "audience": "professional network",
            "extra": {},
        }
        if profile:
            brief["skills"] = [s.name for s in (profile.skills or []) if s.name]

        if source == PipelineSource.PROFILE:
            if not profile:
                raise ValueError("Profile not found")
            brief["highlight"] = profile.bio or profile.headline or ""
            brief["extra"]["location"] = profile.location
            brief["extra"]["years_of_experience"] = profile.years_of_experience
        elif source == PipelineSource.RESUME:
            resume = self._user_resume(user_id, source_id)
            skills = resume.extracted_skills or []
            if skills:
                brief["skills"] = [str(s) for s in skills]
            brief["highlight"] = (resume.raw_text or "")[:600]
            brief["extra"]["resume_file"] = resume.original_filename
        elif source == PipelineSource.PROJECT:
            project = self._scoped(Project, source_id, user_id)
            brief["highlight"] = f"{project.name}: {project.description or ''}"
            brief["extra"]["technologies"] = project.technologies
            brief["extra"]["url"] = project.url
        elif source == PipelineSource.CERTIFICATION:
            cert = self.db.query(Certification).filter(
                Certification.id == source_id, Certification.user_id == user_id
            ).first()
            if not cert:
                raise ValueError("Certification not found")
            brief["highlight"] = f"Earned {cert.name}" + (f" from {cert.issuer}" if cert.issuer else "")
            brief["extra"]["issuer"] = cert.issuer
            brief["extra"]["credential_url"] = cert.credential_url
        elif source == PipelineSource.ACHIEVEMENT:
            item = self.db.query(Achievement).filter(
                Achievement.id == source_id, Achievement.user_id == user_id
            ).first()
            if not item:
                raise ValueError("Achievement not found")
            brief["highlight"] = f"{item.title}: {item.description or ''}"
            brief["extra"]["url"] = item.url
        elif source == PipelineSource.RESEARCH:
            research = self.db.query(Research).filter(
                Research.id == source_id, Research.user_id == user_id
            ).first()
            if not research:
                raise ValueError("Research not found")
            brief["highlight"] = research.executive_summary or research.query
            brief["extra"]["topic"] = research.query
        elif source == PipelineSource.LEARNING:
            plan = self._user_learning_plan(user_id, source_id)
            gaps = plan.skill_gaps or []
            gap_names = [g.get("skill", g) if isinstance(g, dict) else str(g) for g in gaps]
            brief["highlight"] = f"Learning journey toward {plan.target_role}: {', '.join(gap_names[:5])}"
            brief["extra"]["target_role"] = plan.target_role
        else:  # pragma: no cover - enum exhaustiveness guard
            raise ValueError(f"Unsupported source: {source}")

        return brief

    def _user_resume(self, user_id: int, source_id: Optional[int]) -> Resume:
        q = self.db.query(Resume).filter(Resume.user_id == user_id)
        resume = q.filter(Resume.id == source_id).first() if source_id else None
        if resume is None:
            resume = q.filter(Resume.is_primary.is_(True)).first() or q.order_by(Resume.id.desc()).first()
        if resume is None:
            raise ValueError("No resume found for user")
        return resume

    def _user_learning_plan(self, user_id: int, source_id: Optional[int]) -> LearningPlan:
        q = self.db.query(LearningPlan).filter(LearningPlan.user_id == user_id)
        plan = q.filter(LearningPlan.id == source_id).first() if source_id else None
        if plan is None:
            plan = q.order_by(LearningPlan.id.desc()).first()
        if plan is None:
            raise ValueError("No learning plan found for user")
        return plan

    def _scoped(self, model, source_id: Optional[int], user_id: int):
        if not source_id:
            raise ValueError(f"{model.__name__} id is required")
        profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()
        if not profile:
            raise ValueError("Profile not found")
        obj = self.db.query(model).filter(
            model.id == source_id, model.profile_id == profile.id
        ).first()
        if obj is None:
            raise ValueError(f"{model.__name__} not found")
        return obj

    # ------------------------------------------------------------------
    # Pipeline runner (stages 2-7)
    # ------------------------------------------------------------------
    async def run_pipeline(
        self,
        user_id: int,
        source: PipelineSource,
        content_kind: ContentKind,
        platforms: List[str],
        source_id: Optional[int] = None,
        topic: Optional[str] = None,
    ) -> ContentPipelineRun:
        """Execute intake -> topics -> research -> generation -> verification -> formatting."""
        for platform in platforms:
            if platform not in SUPPORTED_PLATFORMS:
                raise ValueError(f"Unsupported platform: {platform}")

        run = ContentPipelineRun(
            user_id=user_id,
            source=source,
            source_id=source_id,
            content_kind=content_kind,
            platforms=list(platforms),
            status=PipelineStage.DRAFT,
            current_stage=PipelineStage.DRAFT.value,
            stage_results={},
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        context: Dict[str, Any] = {"run_id": run.id, "intent": Intent.CONTENT.value}

        def record(stage: PipelineStage, payload: Dict[str, Any]) -> None:
            run.current_stage = stage.value
            run.status = stage
            results = dict(run.stage_results or {})
            results[stage.value] = payload
            run.stage_results = dict(results)  # reassign so SQLAlchemy sees the mutation
            self.db.commit()

        try:
            brief = self.build_brief(user_id, source, source_id)
            brief["platforms"] = list(platforms)
            record(PipelineStage.INTAKE, {"brief": brief})

            topics = await self.router.route(
                {"type": "career_content.topics", "brief": brief,
                 "requested_topic": topic, **context}
            )
            record(PipelineStage.TOPIC_SELECTION, topics)
            brief = {**brief, "topic": topics["selected"]["topic"]}
            required_terms = self._required_terms(source, source_id, user_id)

            guard = await self.router.route(
                {"type": "career_content.guard", "source": source.value
                 if isinstance(source, PipelineSource) else source,
                 "source_id": source_id, "user_id": user_id,
                 "required_terms": required_terms, **context}
            )
            if not guard.get("exists", False):
                run.status = PipelineStage.FAILED
                run.current_stage = PipelineStage.FAILED.value
                run.error_message = guard.get("message", "source entity no longer available")
                self.db.commit()
                self.db.refresh(run)
                return run

            research = await self.router.route(
                {"type": "career_content.research", "brief": brief, "kind": content_kind.value, **context}
            )
            record(PipelineStage.RESEARCH, research)

            draft = await self.router.route(
                {"type": "career_content.generate", "brief": brief, "kind": content_kind.value,
                 "research": research, **context}
            )
            record(PipelineStage.GENERATION, draft)

            verdict = await self.router.route(
                {"type": "career_content.verify", "brief": brief, "draft": draft,
                 "research": research, "required_terms": required_terms,
                 "kind": content_kind.value, "platforms": list(platforms),
                 "guard": guard, **context}
            )
            run.quality_score = verdict.get("score")
            record(PipelineStage.VERIFICATION, verdict)
            if not verdict.get("passed"):
                run.status = PipelineStage.FAILED
                run.current_stage = PipelineStage.FAILED.value
                run.error_message = "; ".join(verdict.get("issues", ["quality gate failed"]))
                self.db.commit()
                return run

            formatted = await self.router.route(
                {"type": "career_content.format", "brief": brief, "draft": draft,
                 "platforms": list(platforms), "kind": content_kind.value, **context}
            )
            record(PipelineStage.FORMATTING, formatted)

            run.status = PipelineStage.PENDING_REVIEW
            run.current_stage = PipelineStage.PENDING_REVIEW.value
            self.db.commit()
            self.db.refresh(run)
            return run
        except Exception as exc:
            logger.exception("Career-to-Content pipeline run %s failed", run.id)
            run.status = PipelineStage.FAILED
            run.current_stage = PipelineStage.FAILED.value
            run.error_message = str(exc)
            self.db.commit()
            self.db.refresh(run)
            return run

    # ------------------------------------------------------------------
    # Stage handlers (routed through the Hermes TaskRouter)
    # ------------------------------------------------------------------
    def _required_terms(
        self, source: PipelineSource, source_id: Optional[int], user_id: int
    ) -> List[str]:
        """Entity names the draft must ground (anti-invention gate).

        Read-only single-column lookups scoped to the user. General
        sources (profile/resume/research/learning) need no entity terms.
        """
        try:
            if source == PipelineSource.CERTIFICATION and source_id:
                row = self.db.query(Certification.name).filter(
                    Certification.id == source_id, Certification.user_id == user_id
                ).first()
                return [row[0]] if row and row[0] else []
            if source == PipelineSource.ACHIEVEMENT and source_id:
                row = self.db.query(Achievement.title).filter(
                    Achievement.id == source_id, Achievement.user_id == user_id
                ).first()
                return [row[0]] if row and row[0] else []
            if source == PipelineSource.PROJECT and source_id:
                profile = self.db.query(Profile).filter(Profile.user_id == user_id).first()
                if profile:
                    row = self.db.query(Project.name).filter(
                        Project.id == source_id, Project.profile_id == profile.id
                    ).first()
                    return [row[0]] if row and row[0] else []
        except Exception as exc:
            logger.warning("Required-terms lookup failed: %s", exc)
        return []

    async def _stage_topics(self, task: Dict[str, Any]) -> Dict[str, Any]:
        picked = pick_topic(task.get("brief", {}), requested=task.get("requested_topic"))
        return {"selected": {k: v for k, v in picked.items() if k != "suggestions"},
                "suggestions": picked.get("suggestions", [])}

    async def _stage_research(self, task: Dict[str, Any]) -> Dict[str, Any]:
        brief, kind = task.get("brief", {}), task.get("kind", "")
        if ContentKind(kind) not in RESEARCH_BACKED_KINDS:
            return {"sources": [], "skipped": True}
        topic = brief.get("highlight", "") or brief.get("target_role", "") or "career growth"
        try:
            results = await self.search.search(SearchConfig(query=str(topic)[:200], limit=5))
        except Exception as exc:
            logger.warning("Research stage search failed: %s", exc)
            return {"sources": [], "skipped": True, "warning": str(exc)}
        return {
            "sources": [
                {"title": r.title, "url": r.url, "snippet": r.snippet, "domain": r.domain}
                for r in (results or [])
            ],
            "skipped": False,
        }

    async def _stage_generate(self, task: Dict[str, Any]) -> Dict[str, Any]:
        brief = task.get("brief", {})
        kind = ContentKind(task.get("kind"))
        research = task.get("research", {}) or {}
        if research.get("sources"):
            brief = {**brief, "requires_sources": False,
                     "extra": {**(brief.get("extra") or {}),
                               "research": "; ".join(s.get("title", "") for s in research["sources"][:3])}}
        return await self.generator.generate(kind, brief)

    async def _stage_guard(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Re-validate that the source entity still exists and is owned.

        Intake already checks existence; this guard re-checks immediately
        before generation so stale or revoked material can never be
        drafted from, and the check is recorded on the run.
        """
        source = task.get("source")
        source_id = task.get("source_id")
        user_id = task.get("user_id")
        entity_sources = (
            PipelineSource.CERTIFICATION.value,
            PipelineSource.ACHIEVEMENT.value,
            PipelineSource.PROJECT.value,
        )
        if source not in entity_sources or not source_id:
            return {"exists": True, "skipped": True}
        terms = task.get("required_terms") or []
        if terms:
            return {"exists": True, "skipped": False, "entities": terms}
        label = {"certification": "Certification", "achievement": "Achievement",
                 "project": "Project"}.get(source, "Source")
        return {
            "exists": False,
            "skipped": False,
            "message": f"{label} #{source_id} no longer exists or is not owned by the user",
        }

    async def _stage_verify(self, task: Dict[str, Any]) -> Dict[str, Any]:
        draft = task.get("draft", {}) or {}
        research = task.get("research", {}) or {}
        kind = ContentKind(task.get("kind"))
        kind_template, _ = career_templates.build_prompt(kind, {})
        verdict = await self.verifier.verify(
            draft.get("text", ""), brief=task.get("brief", {}),
            sources=research.get("sources", []),
            required_terms=task.get("required_terms") or None,
            kind_template=kind_template,
            platforms=list(task.get("platforms", [])),
        )
        verdict["guard"] = task.get("guard", {})
        return verdict

    async def _stage_format(self, task: Dict[str, Any]) -> Dict[str, Any]:
        text = (task.get("draft", {}) or {}).get("text", "")
        kind_value = task.get("kind", "")
        brief = task.get("brief", {}) or {}
        extra_tags = list(brief.get("skills", []) or [])
        variants = self.drafts.build(
            text, kind_value, list(task.get("platforms", [])), extra_tags=extra_tags
        )
        return {"variants": variants}

    # ------------------------------------------------------------------
    # Stage 7: human approval + run access
    # ------------------------------------------------------------------
    def approve_run(self, run_id: int, user_id: int, notes: Optional[str] = None) -> ContentPipelineRun:
        return self._decide(run_id, user_id, approve=True, notes=notes)

    def reject_run(self, run_id: int, user_id: int, notes: Optional[str] = None) -> ContentPipelineRun:
        return self._decide(run_id, user_id, approve=False, notes=notes)

    def _decide(self, run_id: int, user_id: int, approve: bool, notes: Optional[str]) -> ContentPipelineRun:
        run = self.db.query(ContentPipelineRun).filter(
            ContentPipelineRun.id == run_id, ContentPipelineRun.user_id == user_id
        ).first()
        if not run:
            raise ValueError("Pipeline run not found")
        if run.status != PipelineStage.PENDING_REVIEW:
            raise ValueError(f"Run is not awaiting review (status={run.status.value})")
        run.status = PipelineStage.APPROVED if approve else PipelineStage.REJECTED
        run.current_stage = run.status.value
        run.reviewed_by = user_id
        run.reviewed_at = datetime.utcnow()
        run.review_notes = notes
        self.db.commit()
        self.db.refresh(run)
        return run

    # ------------------------------------------------------------------
    # Human revision: edit + regenerate (approved runs are immutable)
    # ------------------------------------------------------------------
    _EDITABLE_STATES = (PipelineStage.PENDING_REVIEW, PipelineStage.FAILED)
    _REGENERABLE_STATES = (PipelineStage.PENDING_REVIEW, PipelineStage.FAILED, PipelineStage.REJECTED)
    _DRAFT_HISTORY_LIMIT = 10

    def _require_state(self, run: ContentPipelineRun, allowed, action: str) -> None:
        status = run.status
        allowed_values = {s.value for s in allowed}
        current = status.value if isinstance(status, PipelineStage) else str(status)
        if current not in allowed_values:
            suffix = "; approved runs are final" if current == PipelineStage.APPROVED.value else ""
            raise ValueError(f"Run cannot be {action} (status={current}{suffix})")

    def _stored_brief(self, run: ContentPipelineRun) -> Dict[str, Any]:
        brief = (run.stage_results or {}).get("intake", {}).get("brief")
        if brief:
            return dict(brief)
        return self.build_brief(run.user_id, run.source, run.source_id)

    def _stored_research(self, run: ContentPipelineRun) -> Dict[str, Any]:
        return dict((run.stage_results or {}).get("research", {}))

    def _push_history(self, run: ContentPipelineRun, draft: Dict[str, Any]) -> List[Dict[str, Any]]:
        history = list((run.stage_results or {}).get("draft_history", []))
        if draft.get("text"):
            history.append({**draft, "at": datetime.utcnow().isoformat()})
        return history[-self._DRAFT_HISTORY_LIMIT:]

    def _save_draft_revision(
        self,
        run: ContentPipelineRun,
        draft: Dict[str, Any],
        history: List[Dict[str, Any]],
        verdict: Dict[str, Any],
        formatted: Dict[str, Any],
    ) -> ContentPipelineRun:
        results = dict(run.stage_results or {})
        results["generation"] = draft
        results["draft_history"] = history
        verdict = dict(verdict)
        verdict.setdefault("guard", results.get("verification", {}).get("guard", {}))
        results["verification"] = verdict
        results["formatting"] = formatted
        run.stage_results = results
        run.quality_score = verdict.get("score")
        if verdict.get("passed"):
            run.status = PipelineStage.PENDING_REVIEW
            run.current_stage = PipelineStage.PENDING_REVIEW.value
            run.error_message = None
        else:
            run.status = PipelineStage.FAILED
            run.current_stage = PipelineStage.FAILED.value
            run.error_message = "; ".join(verdict.get("issues", ["quality gate failed"]))
        self.db.commit()
        self.db.refresh(run)
        return run

    async def _reverify(
        self,
        run: ContentPipelineRun,
        draft: Dict[str, Any],
        brief: Dict[str, Any],
        research: Dict[str, Any],
    ) -> ContentPipelineRun:
        """Verify + format a revised draft and persist the outcome."""
        kind_value = run.content_kind.value if isinstance(run.content_kind, ContentKind) else str(run.content_kind)
        verdict = await self.router.route(
            {"type": "career_content.verify", "brief": brief, "draft": draft,
             "research": research,
             "required_terms": self._required_terms(run.source, run.source_id, run.user_id),
             "kind": kind_value, "platforms": list(run.platforms or []),
             "guard": (run.stage_results or {}).get("verification", {}).get("guard", {}),
             "run_id": run.id, "intent": Intent.CONTENT.value}
        )
        formatted = await self.router.route(
            {"type": "career_content.format", "brief": brief, "draft": draft,
             "platforms": list(run.platforms or []), "kind": kind_value,
             "run_id": run.id, "intent": Intent.CONTENT.value}
        )
        history = self._push_history(run, (run.stage_results or {}).get("generation", {}))
        return self._save_draft_revision(run, draft, history, verdict, formatted)

    async def edit_draft(self, run_id: int, user_id: int, text: str) -> ContentPipelineRun:
        """Human edit of a draft awaiting review (or failed); re-verified on save."""
        run = self.get_run(run_id, user_id)
        self._require_state(run, self._EDITABLE_STATES, "edited")
        text = (text or "").strip()
        if not text:
            raise ValueError("Edited text must not be empty")
        brief = self._stored_brief(run)
        research = self._stored_research(run)
        prior = dict((run.stage_results or {}).get("generation", {}))
        draft = {**prior, "text": text, "model": "human-edit", "origin": "edited"}
        return await self._reverify(run, draft, brief, research)

    async def regenerate_draft(
        self,
        run_id: int,
        user_id: int,
        topic: Optional[str] = None,
        content_kind: Optional[ContentKind] = None,
    ) -> ContentPipelineRun:
        """Regenerate a draft for a run awaiting review, failed, or rejected."""
        run = self.get_run(run_id, user_id)
        self._require_state(run, self._REGENERABLE_STATES, "regenerated")
        brief = self._stored_brief(run)
        research = self._stored_research(run)
        if topic and topic.strip():
            brief = {**brief, "topic": topic.strip()}
        kind = content_kind or run.content_kind
        if isinstance(kind, str):
            try:
                kind = ContentKind(kind)
            except ValueError:
                raise ValueError(f"Unsupported content kind: {kind}")
        current_kind = run.content_kind.value if isinstance(run.content_kind, ContentKind) else str(run.content_kind)
        if kind.value != current_kind:
            run.content_kind = kind
        draft = await self.router.route(
            {"type": "career_content.generate", "brief": brief, "kind": kind.value,
             "research": research, "run_id": run.id, "intent": Intent.CONTENT.value}
        )
        draft = {**draft, "origin": "regenerated"}
        return await self._reverify(run, draft, brief, research)

    def list_runs(self, user_id: int, limit: int = 20) -> List[ContentPipelineRun]:
        return (
            self.db.query(ContentPipelineRun)
            .filter(ContentPipelineRun.user_id == user_id)
            .order_by(ContentPipelineRun.id.desc())
            .limit(limit)
            .all()
        )

    def get_run(self, run_id: int, user_id: int) -> ContentPipelineRun:
        run = self.db.query(ContentPipelineRun).filter(
            ContentPipelineRun.id == run_id, ContentPipelineRun.user_id == user_id
        ).first()
        if not run:
            raise ValueError("Pipeline run not found")
        return run

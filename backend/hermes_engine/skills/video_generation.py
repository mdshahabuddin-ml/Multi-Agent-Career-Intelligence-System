"""
Video Generation Skill - Orchestrates Content → Script → Scenes → Veo → MP4.

This skill:
1. Takes approved content
2. Generates a narration script via LLM
3. Decomposes script into visual scenes
4. Generates video for each scene via Veo
5. Returns the final video URL
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.content import Content
from backend.models.video_pipeline import VideoPipeline, VideoScene
from backend.social_integrations.veo import VeoClient, VeoError, VeoSceneRequest
from backend.hermes_engine.memory.content_context import ContentContextResolver

logger = logging.getLogger(__name__)


SCRIPT_GENERATION_PROMPT = """You are a professional video scriptwriter for career intelligence content.

The customer asked the following question — this is the PRIMARY intent the script must address:
"{original_question}"

Content created to answer this question:
Title: {title}
Body: {body}
Tags: {tags}

The viewer's career context:
{career_context}

Create a video narration script suitable for a {duration}-second video.

Requirements:
- The script MUST directly answer the customer's question above
- Reference the viewer's career context where relevant (target role, skills, experience)
- Write a natural narration script (spoken word style)
- Include visual direction hints in [brackets] like [OPENING SHOT], [CUT TO], [TEXT ON SCREEN]
- Keep it under {max_words} words
- End with a call to action
- Tone: professional but approachable

Return ONLY the script text, no JSON, no markdown formatting."""

SCENE_DECOMPOSITION_PROMPT = """You are a video production planner. Given a narration script, break it into visual scenes.

The video answers this customer question:
"{original_question}"

The content title is: "{title}"

Script:
{script}

Rules:
- Each scene should be {scene_duration} seconds
- Maximum {max_scenes} scenes
- Each scene MUST be visually relevant to the topic above
- Each scene needs a visual description for AI video generation
- Scenes should flow logically from the customer's question to the answer
- Use the original question to guide visual metaphors and scene imagery

Return a JSON array (no markdown, no code blocks) with this exact format:
[
  {{
    "scene_index": 0,
    "description": "Brief description of what appears on screen",
    "prompt": "Detailed visual prompt for AI video generation. Be specific about camera angle, lighting, subject, movement. Always stay on-topic.",
    "narration": "The narration text for this scene"
  }}
]

Return ONLY the JSON array."""


class VideoGenerationSkill:
    """Orchestrates the full video generation pipeline."""

    def __init__(self, db: Session):
        self.db = db
        self.veo = VeoClient()

    async def run_pipeline(
        self, content_id: int, user_id: int, pipeline: Optional[VideoPipeline] = None
    ) -> VideoPipeline:
        """Execute the full pipeline for a content item.

        If pipeline is provided, reuses it. Otherwise creates a new one.
        Returns the VideoPipeline record with all stages populated.
        """
        # 1. Fetch content
        content = self.db.query(Content).filter(
            Content.id == content_id,
            Content.user_id == user_id,
        ).first()
        if not content:
            raise ValueError(f"Content {content_id} not found")
        if content.status != "approved":
            raise ValueError(f"Content must be approved (current: {content.status})")

        # 2. Create or reuse pipeline record
        if pipeline is None:
            pipeline = VideoPipeline(
                user_id=user_id,
                content_id=content_id,
                status="script_generating",
                veo_model=settings.VEO_MODEL,
                started_at=datetime.utcnow(),
            )
            self.db.add(pipeline)
            self.db.commit()
            self.db.refresh(pipeline)
        else:
            pipeline.status = "script_generating"
            pipeline.started_at = datetime.utcnow()
            self.db.commit()

        try:
            # 3. Resolve full context (original question + career context)
            resolver = ContentContextResolver(self.db)
            context = resolver.resolve(content_id, user_id)

            # 4. Generate script
            script = await self._generate_script(content, context)
            pipeline.script = script
            pipeline.status = "script_ready"
            self.db.commit()

            # 5. Decompose into scenes
            scenes = await self._decompose_scenes(script, context)
            pipeline.scenes = scenes
            pipeline.status = "scenes_ready"
            self.db.commit()

            # Save individual scene records
            for scene_data in scenes:
                scene = VideoScene(
                    pipeline_id=pipeline.id,
                    scene_index=scene_data["scene_index"],
                    description=scene_data["description"],
                    prompt=scene_data["prompt"],
                    duration_seconds=settings.VIDEO_SCENE_DURATION_SECONDS,
                    status="pending",
                )
                self.db.add(scene)
            self.db.commit()

            # 6. Generate video for each scene
            pipeline.status = "video_generating"
            self.db.commit()

            video_results = await self._generate_scene_videos(scenes, pipeline.id)

            # 7. Update pipeline with results
            completed_videos = [r for r in video_results if r.get("video_url")]
            if completed_videos:
                # Use the first scene video as the main video
                pipeline.video_url = completed_videos[0]["video_url"]
                pipeline.thumbnail_url = completed_videos[0].get("thumbnail_url")
                pipeline.status = "video_ready"
            else:
                pipeline.status = "failed"
                pipeline.error_message = "No scenes generated successfully"

            pipeline.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(pipeline)

            return pipeline

        except Exception as e:
            pipeline.status = "failed"
            pipeline.error_message = str(e)[:2000]
            pipeline.completed_at = datetime.utcnow()
            self.db.commit()
            raise

    async def _generate_script(self, content: Content, context: Dict[str, Any]) -> str:
        """Generate a narration script from content using LLM."""
        content_ctx = context.get("content", {})
        career_ctx = context.get("career", {})

        original_question = content_ctx.get("original_question") or content.title
        tags = ", ".join(content_ctx.get("tags", []))

        # Format career context for the prompt
        career_lines = []
        if career_ctx.get("target_role"):
            career_lines.append(f"Target role: {career_ctx['target_role']}")
        if career_ctx.get("skills"):
            career_lines.append(f"Key skills: {', '.join(career_ctx['skills'][:10])}")
        if career_ctx.get("recent_experience"):
            roles = [f"{e.get('role', '')} at {e.get('company', '')}" for e in career_ctx["recent_experience"]]
            career_lines.append(f"Experience: {'; '.join(roles)}")
        if career_ctx.get("learning_goals"):
            goals = [g.get("title", "") for g in career_ctx["learning_goals"] if g.get("title")]
            career_lines.append(f"Learning goals: {', '.join(goals)}")
        career_context_str = "\n".join(career_lines) if career_lines else "No specific career context available."

        prompt = SCRIPT_GENERATION_PROMPT.format(
            original_question=original_question,
            title=content.title,
            body=content.body[:2000],
            tags=tags,
            career_context=career_context_str,
            duration=settings.VIDEO_MAX_SCENES * settings.VIDEO_SCENE_DURATION_SECONDS,
            max_words=200,
        )

        if settings.MOCK_VIDEO_GENERATION:
            return self._mock_script(content, context)

        try:
            from backend.providers.llm.factory import LLMFactory
            provider = LLMFactory.create(
                provider="openai",
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
            )
            response = await provider.generate(prompt, max_tokens=500)
            return response.get("text", self._mock_script(content, context))
        except Exception as e:
            logger.warning("LLM script generation failed, using mock: %s", e)
            return self._mock_script(content, context)

    async def _decompose_scenes(self, script: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Decompose script into visual scenes using LLM."""
        content_ctx = context.get("content", {})
        original_question = content_ctx.get("original_question") or content_ctx.get("title", "")
        title = content_ctx.get("title", "")

        prompt = SCENE_DECOMPOSITION_PROMPT.format(
            original_question=original_question,
            title=title,
            script=script,
            scene_duration=settings.VIDEO_SCENE_DURATION_SECONDS,
            max_scenes=settings.VIDEO_MAX_SCENES,
        )

        if settings.MOCK_VIDEO_GENERATION:
            return self._mock_scenes(script, context)

        try:
            from backend.providers.llm.factory import LLMFactory
            provider = LLMFactory.create(
                provider="openai",
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
            )
            response = await provider.generate(prompt, max_tokens=1500)
            text = response.get("text", "")
            # Parse JSON from response
            scenes = json.loads(text.strip())
            if isinstance(scenes, list) and len(scenes) > 0:
                return scenes[:settings.VIDEO_MAX_SCENES]
        except Exception as e:
            logger.warning("LLM scene decomposition failed, using mock: %s", e)

        return self._mock_scenes(script, context)

    async def _generate_scene_videos(
        self, scenes: List[Dict[str, Any]], pipeline_id: int
    ) -> List[Dict[str, Any]]:
        """Generate video for each scene via Veo."""
        results = []
        scene_records = (
            self.db.query(VideoScene)
            .filter(VideoScene.pipeline_id == pipeline_id)
            .order_by(VideoScene.scene_index)
            .all()
        )

        for i, scene_data in enumerate(scenes):
            scene_record = scene_records[i] if i < len(scene_records) else None

            try:
                if scene_record:
                    scene_record.status = "generating"
                    self.db.commit()

                veo_request = VeoSceneRequest(
                    prompt=scene_data["prompt"],
                    duration_seconds=settings.VIDEO_SCENE_DURATION_SECONDS,
                )
                operation = await self.veo.generate_video(
                    prompt=veo_request.prompt,
                    duration_seconds=veo_request.duration_seconds,
                )

                result = {
                    "scene_index": scene_data.get("scene_index", i),
                    "video_url": operation.video_url,
                    "thumbnail_url": operation.thumbnail_url,
                    "operation_id": operation.operation_id,
                }
                results.append(result)

                if scene_record:
                    scene_record.status = "ready"
                    scene_record.video_url = operation.video_url
                    scene_record.veo_operation_id = operation.operation_id
                    scene_record.completed_at = datetime.utcnow()
                    self.db.commit()

            except VeoError as e:
                logger.error("Scene %d video generation failed: %s", i, e)
                results.append({"scene_index": i, "video_url": None, "error": str(e)})
                if scene_record:
                    scene_record.status = "failed"
                    scene_record.error_message = str(e)[:1000]
                    self.db.commit()

        return results

    def _mock_script(self, content: Content, context: Optional[Dict[str, Any]] = None) -> str:
        question = ""
        if context:
            question = context.get("content", {}).get("original_question") or ""
        question_line = f"\n\n[CUSTOMER QUESTION] {question}\n" if question else ""
        return (
            f"[OPENING SHOT] Welcome to Career Intelligence.\n\n"
            f"[TEXT ON SCREEN] {content.title}\n"
            f"{question_line}"
            f"[CUT TO] Let's explore this together.\n\n"
            f"[SCENE] {content.body[:300]}\n\n"
            f"[TEXT ON SCREEN] CareerIntel AI - Your Career, Intelligent.\n\n"
            f"[CLOSING] Start your journey today at careerintel.ai."
        )

    def _mock_scenes(self, script: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        topic = ""
        if context:
            topic = context.get("content", {}).get("original_question") or context.get("content", {}).get("title", "")
        topic_prefix = f"about {topic}, " if topic else ""
        lines = [l.strip() for l in script.split("\n") if l.strip()]
        scenes = []
        for i, line in enumerate(lines[:settings.VIDEO_MAX_SCENES]):
            scenes.append({
                "scene_index": i,
                "description": line[:100],
                "prompt": f"Professional career workspace {topic_prefix}modern office, {line[:200]}. Cinematic lighting, smooth camera movement, 4K quality.",
                "narration": line,
            })
        return scenes if scenes else [{
            "scene_index": 0,
            "description": "Career Intelligence Intro",
            "prompt": f"Modern professional workspace with holographic career analytics display {topic_prefix}cinematic lighting, smooth dolly shot, 4K",
            "narration": "Welcome to Career Intelligence.",
        }]

"""
Short Video Generation Skill - Converts long-form research to YouTube Shorts.

Pipeline: Long-form content → Hermes → Short script → Short scenes → 9:16 video → YouTube Shorts
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
from backend.social_integrations.veo import VeoClient, VeoError
from backend.hermes_engine.memory.content_context import ContentContextResolver

logger = logging.getLogger(__name__)

# 60 seconds for Shorts, vertical 9:16 format
SHORT_DURATION_SECONDS = 60
SHORT_MAX_WORDS = 120
SHORT_MAX_SCENES = 6

SHORT_SCRIPT_PROMPT = """You are a professional short-form video scriptwriter for career intelligence content.

The customer asked the following question — this is the PRIMARY intent the script must address:
"{original_question}"

Content created to answer this question:
Title: {title}
Body: {body}
Tags: {tags}

The viewer's career context:
{career_context}

Create a {duration}-second YouTube Shorts script.

Requirements:
- The hook MUST directly reference the customer's question
- Write a punchy, attention-grabbing hook in the first 2 seconds
- Use short, snappy sentences (TikTok/Reels style)
- Include visual direction hints in [brackets] like [HOOK], [TEXT OVERLAY], [TRANSITION]
- Keep under {max_words} words
- End with a strong call to action
- Tone: energetic, professional but casual
- Focus on ONE key insight from the research that answers the question

Return ONLY the script text, no JSON, no markdown formatting."""


SHORT_SCENES_PROMPT = """You are a short-form video editor. Given a script, break it into vertical (9:16) scenes.

The video answers this customer question:
"{original_question}"

Script:
{script}

Rules:
- Each scene should be {scene_duration} seconds
- Maximum {max_scenes} scenes
- Each scene MUST be visually relevant to the customer's question
- Each scene needs a vertical video prompt (9:16 aspect ratio)
- Scenes should have fast-paced transitions
- Include text overlay descriptions for each scene
- Use the original question to guide visual imagery

Return a JSON array (no markdown, no code blocks) with this exact format:
[
  {{
    "scene_index": 0,
    "description": "Brief description of vertical scene",
    "prompt": "Detailed visual prompt for 9:16 vertical video. Include vertical framing, portrait orientation. Be specific about subject, text overlays, transitions. Always stay on-topic.",
    "text_overlay": "Text that appears on screen (if any)",
    "transition": "Type of transition to next scene"
  }}
]

Return ONLY the JSON array."""


class ShortVideoGenerationSkill:
    """Converts long-form research content to short-form YouTube Shorts."""

    def __init__(self, db: Session):
        self.db = db
        self.veo = VeoClient()

    async def run_pipeline(
        self, content_id: int, user_id: int, pipeline: Optional[VideoPipeline] = None
    ) -> VideoPipeline:
        """Execute the short-form video pipeline.

        Takes long-form content and creates a 60-second vertical video for YouTube Shorts.
        """
        # 1. Fetch long-form content
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
                metadata_json={"format": "short", "aspect_ratio": "9:16", "duration": SHORT_DURATION_SECONDS},
            )
            self.db.add(pipeline)
            self.db.commit()
            self.db.refresh(pipeline)
        else:
            pipeline.status = "script_generating"
            pipeline.started_at = datetime.utcnow()
            if not pipeline.metadata_json:
                pipeline.metadata_json = {"format": "short", "aspect_ratio": "9:16", "duration": SHORT_DURATION_SECONDS}
            self.db.commit()

        try:
            # 3. Resolve full context (original question + career context)
            resolver = ContentContextResolver(self.db)
            context = resolver.resolve(content_id, user_id)

            # 4. Generate short-form script
            script = await self._generate_short_script(content, context)
            pipeline.script = script
            pipeline.status = "script_ready"
            self.db.commit()

            # 5. Decompose into short scenes
            scenes = await self._decompose_short_scenes(script, context)
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
                    duration_seconds=SHORT_DURATION_SECONDS // len(scenes),
                    status="pending",
                )
                self.db.add(scene)
            self.db.commit()

            # 5. Generate vertical video for each scene
            pipeline.status = "video_generating"
            self.db.commit()

            video_results = await self._generate_short_scene_videos(scenes, pipeline.id)

            # 6. Update pipeline with results
            completed_videos = [r for r in video_results if r.get("video_url")]
            if completed_videos:
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

    async def _generate_short_script(self, content: Content, context: Dict[str, Any]) -> str:
        """Generate a short-form script from long-form content using LLM."""
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

        prompt = SHORT_SCRIPT_PROMPT.format(
            original_question=original_question,
            title=content.title,
            body=content.body[:3000],
            tags=tags,
            career_context=career_context_str,
            duration=SHORT_DURATION_SECONDS,
            max_words=SHORT_MAX_WORDS,
        )

        if settings.MOCK_VIDEO_GENERATION:
            return self._mock_short_script(content, context)

        try:
            from backend.providers.llm.factory import LLMFactory
            provider = LLMFactory.create(
                provider="openai",
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
            )
            response = await provider.generate(prompt, max_tokens=300)
            return response.get("text", self._mock_short_script(content, context))
        except Exception as e:
            logger.warning("LLM short script generation failed, using mock: %s", e)
            return self._mock_short_script(content, context)

    async def _decompose_short_scenes(self, script: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Decompose short script into vertical scenes using LLM."""
        content_ctx = context.get("content", {})
        original_question = content_ctx.get("original_question") or content_ctx.get("title", "")

        prompt = SHORT_SCENES_PROMPT.format(
            original_question=original_question,
            script=script,
            scene_duration=SHORT_DURATION_SECONDS // SHORT_MAX_SCENES,
            max_scenes=SHORT_MAX_SCENES,
        )

        if settings.MOCK_VIDEO_GENERATION:
            return self._mock_short_scenes(script, context)

        try:
            from backend.providers.llm.factory import LLMFactory
            provider = LLMFactory.create(
                provider="openai",
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
            )
            response = await provider.generate(prompt, max_tokens=1500)
            text = response.get("text", "")
            scenes = json.loads(text.strip())
            if isinstance(scenes, list) and len(scenes) > 0:
                return scenes[:SHORT_MAX_SCENES]
        except Exception as e:
            logger.warning("LLM short scene decomposition failed, using mock: %s", e)

        return self._mock_short_scenes(script, context)

    async def _generate_short_scene_videos(
        self, scenes: List[Dict[str, Any]], pipeline_id: int
    ) -> List[Dict[str, Any]]:
        """Generate vertical video for each scene via Veo."""
        results = []
        scene_records = (
            self.db.query(VideoScene)
            .filter(VideoScene.pipeline_id == pipeline_id)
            .order_by(VideoScene.scene_index)
            .all()
        )

        scene_duration = SHORT_DURATION_SECONDS // len(scenes) if scenes else 10

        for i, scene_data in enumerate(scenes):
            scene_record = scene_records[i] if i < len(scene_records) else None

            try:
                if scene_record:
                    scene_record.status = "generating"
                    self.db.commit()

                # Add vertical aspect ratio to prompt
                vertical_prompt = f"{scene_data['prompt']} (9:16 vertical format, portrait orientation, mobile-optimized)"

                operation = await self.veo.generate_video(
                    prompt=vertical_prompt,
                    duration_seconds=scene_duration,
                    aspect_ratio="9:16",  # Vertical for Shorts
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
                logger.error("Short scene %d video generation failed: %s", i, e)
                results.append({"scene_index": i, "video_url": None, "error": str(e)})
                if scene_record:
                    scene_record.status = "failed"
                    scene_record.error_message = str(e)[:1000]
                    self.db.commit()

        return results

    def _mock_short_script(self, content: Content, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a mock short-form script."""
        question = ""
        if context:
            question = context.get("content", {}).get("original_question") or ""
        question_hook = f" about {question}" if question else ""
        key_point = content.body[:200] if content.body else "This career insight could change everything."
        return (
            f"[HOOK] Did you know this{question_hook}?\n\n"
            f"[TEXT OVERLAY] {content.title}\n\n"
            f"[SCENE] {key_point}\n\n"
            f"[TRANSITION] Here's the key takeaway...\n\n"
            f"[TEXT OVERLAY] Key Insight\n\n"
            f"[SCENE] This means for your career...\n\n"
            f"[CTA] Follow for more career tips!"
        )

    def _mock_short_scenes(self, script: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate mock vertical scenes."""
        topic = ""
        if context:
            topic = context.get("content", {}).get("original_question") or context.get("content", {}).get("title", "")
        topic_prefix = f"about {topic}, " if topic else ""
        lines = [l.strip() for l in script.split("\n") if l.strip()]
        scenes = []
        scene_duration = SHORT_DURATION_SECONDS // SHORT_MAX_SCENES

        for i, line in enumerate(lines[:SHORT_MAX_SCENES]):
            scenes.append({
                "scene_index": i,
                "description": f"Vertical scene {i+1}: {line[:80]}",
                "prompt": f"Vertical 9:16 video, portrait orientation, {topic_prefix}modern career workspace, {line[:150]}. Dynamic text overlays, smooth transitions, mobile-optimized framing, professional lighting.",
                "text_overlay": line if "[" in line else "",
                "transition": "swipe" if i < len(lines) - 1 else "fade",
                "duration_seconds": scene_duration,
            })

        return scenes if scenes else [{
            "scene_index": 0,
            "description": "Career Intelligence Short Intro",
            "prompt": f"Vertical 9:16 video, modern professional workspace with holographic career analytics {topic_prefix}portrait orientation, dynamic text overlay, smooth camera movement, mobile-optimized",
            "text_overlay": "Career Intelligence",
            "transition": "fade",
            "duration_seconds": scene_duration,
        }]

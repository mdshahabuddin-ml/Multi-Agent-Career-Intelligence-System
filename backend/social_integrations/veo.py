"""
Veo client - Google Veo video generation API integration.

Supports:
- Text-to-video generation
- Scene-by-scene video creation
- Mock mode for development (MOCK_VIDEO_GENERATION=True)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 120.0


class VeoError(Exception):
    """Veo API error."""
    def __init__(self, message: str, status: Optional[int] = None):
        self.status = status
        super().__init__(message)


@dataclass
class VeoSceneRequest:
    """A single scene to generate."""
    prompt: str
    duration_seconds: int = 8
    aspect_ratio: str = "16:9"
    negative_prompt: str = ""


@dataclass
class VeoOperation:
    """Tracks a long-running Veo generation operation."""
    operation_id: str
    status: str  # pending | processing | completed | failed
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VeoClient:
    """Client for Google Veo video generation API.

    Uses Vertex AI REST API:
    POST https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/publishers/google/models/{model}:generateVideo

    When MOCK_VIDEO_GENERATION=True (default), returns simulated results
    with no actual API calls.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        model: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        self.project_id = project_id or settings.GOOGLE_CLOUD_PROJECT
        self.region = region or settings.VEO_REGION
        self.model = model or settings.VEO_MODEL
        self.access_token = access_token
        self._base_url = (
            f"https://{self.region}-aiplatform.googleapis.com/v1"
            f"/projects/{self.project_id}/locations/{self.region}"
            f"/publishers/google/models/{self.model}"
        )

    async def generate_video(
        self,
        prompt: str,
        duration_seconds: int = 8,
        aspect_ratio: str = "16:9",
        negative_prompt: str = "",
    ) -> VeoOperation:
        """Generate a video from a text prompt.

        Returns a VeoOperation that can be polled for completion.
        """
        if settings.MOCK_VIDEO_GENERATION:
            return await self._mock_generate(prompt, duration_seconds)

        if not self.access_token:
            raise VeoError("No access token provided for Veo API")

        request_body = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "durationSeconds": str(duration_seconds),
                "aspectRatio": aspect_ratio,
                "enhancePrompt": True,
            },
        }
        if negative_prompt:
            request_body["parameters"]["negativePrompt"] = negative_prompt

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                f"{self._base_url}:generateVideo",
                json=request_body,
                headers=headers,
            )

        if response.status_code >= 400:
            detail = response.text[:500]
            raise VeoError(f"Veo API error: {detail}", status=response.status_code)

        data = response.json()
        operation_id = data.get("name", str(uuid.uuid4()))

        return VeoOperation(
            operation_id=operation_id,
            status="processing",
            metadata={"raw_response": data},
        )

    async def check_operation(self, operation_id: str) -> VeoOperation:
        """Poll a long-running operation for completion."""
        if settings.MOCK_VIDEO_GENERATION:
            return await self._mock_check(operation_id)

        if not self.access_token:
            raise VeoError("No access token for polling")

        headers = {"Authorization": f"Bearer {self.access_token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(operation_id, headers=headers)

        if response.status_code >= 400:
            raise VeoError(f"Operation poll failed: {response.text[:300]}")

        data = response.json()
        done = data.get("done", False)

        if not done:
            return VeoOperation(
                operation_id=operation_id,
                status="processing",
                metadata=data,
            )

        # Extract video URL from response
        video_url = ""
        thumbnail_url = ""
        if "response" in data:
            videos = data["response"].get("videos", [])
            if videos:
                video_url = videos[0].get("gcsUri", "")
                thumbnail_url = videos[0].get("thumbnailUri", "")

        return VeoOperation(
            operation_id=operation_id,
            status="completed" if not data.get("error") else "failed",
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            completed_at=datetime.utcnow(),
            error=data.get("error", {}).get("message") if data.get("error") else None,
            metadata=data,
        )

    async def generate_scene_video(
        self, scenes: List[VeoSceneRequest]
    ) -> List[VeoOperation]:
        """Generate videos for multiple scenes concurrently."""
        tasks = [
            self.generate_video(
                prompt=scene.prompt,
                duration_seconds=scene.duration_seconds,
                aspect_ratio=scene.aspect_ratio,
                negative_prompt=scene.negative_prompt,
            )
            for scene in scenes
        ]
        return await asyncio.gather(*tasks)

    async def _mock_generate(self, prompt: str, duration: int) -> VeoOperation:
        """Mock video generation for development."""
        op_id = f"mock-veo-{uuid.uuid4().hex[:12]}"
        logger.info("[MOCK] Veo generate: %s (op=%s)", prompt[:60], op_id)

        # Simulate async processing
        await asyncio.sleep(0.1)

        # Use real public sample videos for mock mode
        sample_videos = [
            "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/1080/Big_Buck_Bunny_1080_10s_30MB.mp4",
            "https://test-videos.co.uk/vids/jellyfish/mp4/h264/1080/Jellyfish_1080_10s_30MB.mp4",
            "https://test-videos.co.uk/vids/sintel/mp4/h264/1080/Sintel_1080_10s_30MB.mp4",
        ]
        sample_thumbnails = [
            "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Big_buck_bunny_poster_big.jpg/220px-Big_buck_bunny_poster_big.jpg",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/Elephants_Dream_s1_pro2.jpg/220px-Elephants_Dream_s1_pro2.jpg",
        ]

        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        video_url = sample_videos[hash(prompt_hash) % len(sample_videos)]
        thumbnail_url = sample_thumbnails[hash(prompt_hash) % len(sample_thumbnails)]

        return VeoOperation(
            operation_id=op_id,
            status="completed",
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            duration=float(duration),
            completed_at=datetime.utcnow(),
            metadata={"mock": True, "prompt": prompt},
        )

    async def _mock_check(self, operation_id: str) -> VeoOperation:
        """Mock operation check."""
        return VeoOperation(
            operation_id=operation_id,
            status="completed",
            video_url=f"https://storage.googleapis.com/careerintel-mock/videos/{operation_id}.mp4",
            completed_at=datetime.utcnow(),
            metadata={"mock": True},
        )


# Global client instance
veo_client = VeoClient()

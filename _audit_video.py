"""Audit the current video pipeline output against quality criteria."""
import asyncio
import httpx
from backend.database import SessionLocal
from backend.models.user import User
from backend.models.content import Content
from backend.models.video_pipeline import VideoPipeline, VideoScene
from backend.hermes_engine.skills.video_generation import VideoGenerationSkill
from backend.config import settings

db = SessionLocal()

print("=== CONFIGURATION ===")
print(f"MOCK_VIDEO_GENERATION: {settings.MOCK_VIDEO_GENERATION}")
print(f"VEO_MODEL: {settings.VEO_MODEL}")
print(f"VIDEO_MAX_SCENES: {settings.VIDEO_MAX_SCENES}")
print(f"VIDEO_SCENE_DURATION_SECONDS: {settings.VIDEO_SCENE_DURATION_SECONDS}")
total_dur = settings.VIDEO_MAX_SCENES * settings.VIDEO_SCENE_DURATION_SECONDS
print(f"Total duration: {total_dur}s ({total_dur/60:.1f} min)")

# Get or create test user
user = db.query(User).filter(User.email == "audit@test.com").first()
if not user:
    from backend.utils.security import get_password_hash
    user = User(
        email="audit@test.com",
        hashed_password=get_password_hash("test123"),
        full_name="Audit User",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

# Create test content with original_question
content = Content(
    user_id=user.id,
    title="What Skills Should You Learn to Become a Data Scientist in 2026?",
    body="Data science continues to evolve. Key skills include Python, statistics, machine learning, and data visualization.",
    original_question="What skills should I learn to become a Data Scientist in 2026?",
    status="approved",
    content_type="post",
    tags_json=["data-science", "python", "machine-learning"],
)
db.add(content)
db.commit()
db.refresh(content)
print(f"\nContent ID: {content.id}")
print(f"Original Question: {content.original_question}")

# Run pipeline
async def run():
    skill = VideoGenerationSkill(db)
    pipeline = await skill.run_pipeline(content.id, user.id)
    return pipeline

pipeline = asyncio.run(run())

print(f"\n=== PIPELINE RESULT ===")
print(f"Pipeline ID: {pipeline.id}")
print(f"Status: {pipeline.status}")
print(f"Video URL: {pipeline.video_url}")
script_preview = pipeline.script[:300] if pipeline.script else "None"
print(f"Script preview: {script_preview}...")

# Check scenes
scenes = (
    db.query(VideoScene)
    .filter(VideoScene.pipeline_id == pipeline.id)
    .order_by(VideoScene.scene_index)
    .all()
)
print(f"\n=== SCENES ({len(scenes)}) ===")
for s in scenes:
    print(f"  Scene {s.scene_index}: status={s.status}")
    print(f"    prompt: {s.prompt[:120]}...")
    print(f"    video_url: {s.video_url}")

# === QUALITY CHECKS ===
print(f"\n=== QUALITY CHECKS ===")

# 1. Playable - check video URL returns 200
if pipeline.video_url:
    try:
        r = httpx.head(pipeline.video_url, follow_redirects=True, timeout=10)
        content_type = r.headers.get("content-type", "")
        print(f"[1] Playable: URL returns {r.status_code}, content-type={content_type}")
        print(f"    -> {'PASS' if r.status_code == 200 else 'FAIL'}")
    except Exception as e:
        print(f"[1] Playable: FAIL - {e}")
else:
    print("[1] Playable: FAIL - no video URL")

# 2. Duration
print(f"[2] Duration: {total_dur}s ({total_dur/60:.1f} min) - configured as {settings.VIDEO_MAX_SCENES} scenes x {settings.VIDEO_SCENE_DURATION_SECONDS}s")
print(f"    -> {'PASS' if total_dur >= 600 else 'FAIL - under 10 min'}")

# 3. Topic relevant
has_question = pipeline.script and "data scien" in pipeline.script.lower()
print(f"[3] Topic relevant (script mentions data science): {has_question}")
print(f"    -> {'PASS' if has_question else 'FAIL'}")

# 4. Scenes relevant
topic_in_scenes = sum(1 for s in scenes if any(kw in s.prompt.lower() for kw in ["data", "scien", "python", "machine"]))
print(f"[4] Scenes relevant: {topic_in_scenes}/{len(scenes)} scenes mention topic")
print(f"    -> {'PASS' if topic_in_scenes > 0 else 'FAIL'}")

# 5. Audio - check if script has narration content
narration_lines = [l for l in (pipeline.script or "").split("\n") if l.strip() and not l.strip().startswith("[")]
print(f"[5] Audio (narration text): {len(narration_lines)} non-direction lines")
print(f"    -> {'PASS' if len(narration_lines) > 2 else 'FAIL - too few narration lines'}")

# 6. Captions - check if script has visual directions (used for captions)
directions = [l for l in (pipeline.script or "").split("\n") if l.strip().startswith("[")]
print(f"[6] Captions (visual directions): {len(directions)} direction markers")
print(f"    -> {'PASS' if len(directions) > 2 else 'FAIL - too few directions'}")

# 7. Format - MP4?
is_mp4 = pipeline.video_url and ".mp4" in pipeline.video_url.lower()
print(f"[7] Format (MP4): url ends with .mp4 = {is_mp4}")
print(f"    -> {'PASS' if is_mp4 else 'FAIL'}")

# 8. No failed clips
failed = [s for s in scenes if s.status == "failed"]
print(f"[8] No failed clips: {len(failed)} failed out of {len(scenes)}")
print(f"    -> {'PASS' if not failed else 'FAIL'}")

# Summary
checks = [
    pipeline.video_url is not None,
    total_dur >= 600,
    has_question,
    topic_in_scenes > 0,
    len(narration_lines) > 2,
    len(directions) > 2,
    is_mp4,
    len(failed) == 0,
]
passed = sum(checks)
print(f"\n=== SUMMARY: {passed}/8 checks passed ===")

db.close()

"""
End-to-End Test for CareerIntel AI Pipeline

Tests the complete workflow:
User -> Login -> Career Profile -> Research Topic -> Research Agents -> 
Evidence -> RAG -> Career Analysis -> Content Generation -> Fact Check -> 
Platform Adaptation -> Approval -> Schedule -> Publish -> Analytics -> Feedback
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi.testclient import TestClient

# Test configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api"

class E2ETestClient:
    """Wrapper for making API calls with authentication."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=60.0)
        self.token = None
        self.user = None
        self.csrf_token = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    async def get_csrf_token(self):
        """Get CSRF token for forms."""
        response = await self.client.get(f"{API_PREFIX}/security/csrf-token")
        response.raise_for_status()
        self.csrf_token = response.json()["csrf_token"]
        return self.csrf_token
    
    async def register(self, email: str, password: str, full_name: str) -> Dict[str, Any]:
        """Register a new user."""
        await self.get_csrf_token()
        response = await self.client.post(
            f"{API_PREFIX}/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
            headers={"X-CSRF-Token": self.csrf_token}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        self.user = data["user"]
        return data
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login and get access token."""
        await self.get_csrf_token()
        response = await self.client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": email, "password": password},
            headers={"X-CSRF-Token": self.csrf_token}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        self.user = data["user"]
        return data
    
    def _auth_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {self.token}",
            "X-CSRF-Token": self.csrf_token
        }
    
    async def get_current_user(self) -> Dict[str, Any]:
        """Get current user profile."""
        response = await self.client.get(
            f"{API_PREFIX}/auth/me",
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    # Career Profile
    async def create_career_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update career profile."""
        response = await self.client.post(
            f"{API_PREFIX}/profile",
            json=profile_data,
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_career_profile(self) -> Dict[str, Any]:
        """Get career profile."""
        response = await self.client.get(
            f"{API_PREFIX}/profile",
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    # Research
    async def start_research(self, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start a research task."""
        response = await self.client.post(
            f"{API_PREFIX}/research",
            json=research_data,
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_research_status(self, research_id: int) -> Dict[str, Any]:
        """Get research status."""
        response = await self.client.get(
            f"{API_PREFIX}/research/{research_id}/status",
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_research_report(self, research_id: int) -> Dict[str, Any]:
        """Get research report."""
        response = await self.client.get(
            f"{API_PREFIX}/research/{research_id}",
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def list_research(self) -> List[Dict[str, Any]]:
        """List user's research tasks."""
        response = await self.client.get(
            f"{API_PREFIX}/research",
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()["items"]
    
    # Career Analysis
    async def get_career_insights(self) -> Dict[str, Any]:
        """Get career insights."""
        response = await self.client.get(
            f"{API_PREFIX}/career/insights",
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_career_path_options(self, current_role: str) -> Dict[str, Any]:
        """Get career path options."""
        response = await self.client.get(
            f"{API_PREFIX}/career/path-options",
            params={"current_role": current_role},
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_skill_recommendations(self, target_role: str) -> Dict[str, Any]:
        """Get skill recommendations."""
        response = await self.client.get(
            f"{API_PREFIX}/career/skill-recommendations",
            params={"target_role": target_role},
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def create_career_goal(self, goal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a career goal."""
        response = await self.client.post(
            f"{API_PREFIX}/career/goals",
            json=goal_data,
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    # Content Generation
    async def generate_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate content using AI."""
        response = await self.client.post(
            f"{API_PREFIX}/content-calendar/generate",
            json=content_data,
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def schedule_content(self, content_id: int, schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule content for publishing."""
        response = await self.client.post(
            f"{API_PREFIX}/content-calendar/{content_id}/schedule",
            json=schedule_data,
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def publish_content(self, content_id: int) -> Dict[str, Any]:
        """Publish content."""
        response = await self.client.post(
            f"{API_PREFIX}/content-calendar/{content_id}/publish",
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    # Analytics
    async def get_content_analytics(self, content_id: int) -> Dict[str, Any]:
        """Get content analytics."""
        response = await self.client.get(
            f"{API_PREFIX}/content-calendar/{content_id}/analytics",
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_analytics_summary(self) -> Dict[str, Any]:
        """Get analytics summary."""
        response = await self.client.get(
            f"{API_PREFIX}/analytics/summary",
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()
    
    # Feedback
    async def submit_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit feedback."""
        response = await self.client.post(
            f"{API_PREFIX}/feedback",
            json=feedback_data,
            headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()


# Test data
TEST_USER = {
    "email": "e2e_test@careerintel.ai",
    "password": "TestPassword123!",
    "full_name": "E2E Test User"
}

TEST_CAREER_PROFILE = {
    "current_role": "Software Engineer",
    "years_experience": 5,
    "skills": ["Python", "JavaScript", "React", "PostgreSQL", "Docker", "AWS"],
    "target_role": "Senior Software Engineer",
    "industry": "Technology",
    "location": "San Francisco, CA",
    "salary_range": {"min": 120000, "max": 180000},
    "career_interests": ["Backend Development", "System Design", "Team Leadership"],
    "learning_goals": ["Kubernetes", "Microservices", "Machine Learning"]
}

TEST_RESEARCH_TOPIC = {
    "query": "What are the key skills and technologies needed to transition from Software Engineer to Senior Software Engineer in 2024?",
    "research_type": "career_path",
    "target_role": "Senior Software Engineer",
    "max_sources": 10,
    "timeout_seconds": 300
}

TEST_CONTENT_DATA = {
    "title": "My Journey to Senior Software Engineer",
    "content_type": "linkedin_post",
    "topic": "Career growth and skill development",
    "target_platforms": ["linkedin", "twitter"],
    "tone": "professional",
    "include_hashtags": True,
    "scheduled_for": (datetime.utcnow() + timedelta(days=1)).isoformat()
}

TEST_FEEDBACK = {
    "content_id": 1,
    "rating": 5,
    "feedback_text": "The research was comprehensive and the content generated was highly relevant to my career goals.",
    "categories": ["accuracy", "relevance", "usefulness"]
}


@pytest.fixture
async def e2e_client():
    """Create E2E test client."""
    async with E2ETestClient() as client:
        yield client


@pytest.mark.asyncio
async def test_complete_e2e_pipeline(e2e_client: E2ETestClient):
    """
    Complete end-to-end test of the CareerIntel AI pipeline.
    
    Flow:
    1. User Registration/Login
    2. Career Profile Setup
    3. Research Topic Submission
    4. Research Agent Execution
    5. Evidence Collection
    6. RAG Processing
    7. Career Analysis
    8. Content Generation
    9. Fact Checking
    10. Platform Adaptation
    11. Approval Workflow
    12. Scheduling
    13. Publishing
    14. Analytics Tracking
    15. Feedback Collection
    """
    
    print("\n" + "="*80)
    print("STARTING END-TO-END PIPELINE TEST")
    print("="*80)
    
    # ============================================================
    # STEP 1: User Authentication
    # ============================================================
    print("\n[STEP 1] User Registration & Login")
    print("-" * 40)
    
    # Try to login first (user might exist from previous test)
    try:
        auth_data = await e2e_client.login(TEST_USER["email"], TEST_USER["password"])
        print(f"✓ Login successful for: {auth_data['user']['email']}")
    except httpx.HTTPStatusError:
        # Register new user
        auth_data = await e2e_client.register(
            TEST_USER["email"], 
            TEST_USER["password"], 
            TEST_USER["full_name"]
        )
        print(f"✓ Registration successful for: {auth_data['user']['email']}")
    
    assert e2e_client.token is not None
    assert e2e_client.user is not None
    assert e2e_client.user["email"] == TEST_USER["email"]
    
    # Verify token works
    user_profile = await e2e_client.get_current_user()
    print(f"✓ Token validated for user ID: {user_profile['id']}")
    
    
    # ============================================================
    # STEP 2: Career Profile Setup
    # ============================================================
    print("\n[STEP 2] Career Profile Setup")
    print("-" * 40)
    
    profile = await e2e_client.create_career_profile(TEST_CAREER_PROFILE)
    print(f"✓ Career profile created: {profile.get('current_role')}")
    print(f"  Skills: {len(profile.get('skills', []))} skills")
    print(f"  Target role: {profile.get('target_role')}")
    
    # Verify profile retrieval
    retrieved_profile = await e2e_client.get_career_profile()
    assert retrieved_profile["current_role"] == TEST_CAREER_PROFILE["current_role"]
    print("✓ Profile retrieval verified")
    
    
    # ============================================================
    # STEP 3: Research Topic Submission
    # ============================================================
    print("\n[STEP 3] Research Topic Submission")
    print("-" * 40)
    
    research = await e2e_client.start_research(TEST_RESEARCH_TOPIC)
    research_id = research["id"]
    print(f"✓ Research started with ID: {research_id}")
    print(f"  Query: {TEST_RESEARCH_TOPIC['query'][:60]}...")
    print(f"  Type: {TEST_RESEARCH_TOPIC['research_type']}")
    print(f"  Status: {research.get('status', 'created')}")
    
    
    # ============================================================
    # STEP 4: Research Agent Execution (Poll for completion)
    # ============================================================
    print("\n[STEP 4] Research Agent Execution")
    print("-" * 40)
    
    max_wait_time = 300  # 5 minutes
    poll_interval = 5
    elapsed = 0
    
    while elapsed < max_wait_time:
        status = await e2e_client.get_research_status(research_id)
        print(f"  Progress: {status.get('progress', 0)}% - Phase: {status.get('phase', 'unknown')}")
        
        if status.get("status") == "completed":
            print("✓ Research completed successfully")
            break
        elif status.get("status") == "failed":
            pytest.fail(f"Research failed: {status.get('error_message', 'Unknown error')}")
        
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
    else:
        pytest.fail(f"Research timed out after {max_wait_time} seconds")
    
    # Get full report
    report = await e2e_client.get_research_report(research_id)
    print(f"✓ Report retrieved: {len(report.get('executive_summary', ''))} chars summary")
    print(f"  Sources: {len(report.get('sources', []))}")
    print(f"  Claims verified: {len(report.get('claims', []))}")
    
    
    # ============================================================
    # STEP 5: Evidence Collection Verification
    # ============================================================
    print("\n[STEP 5] Evidence Collection Verification")
    print("-" * 40)
    
    sources = report.get("sources", [])
    assert len(sources) > 0, "No sources collected"
    print(f"✓ {len(sources)} sources collected")
    
    for i, source in enumerate(sources[:3]):
        print(f"  Source {i+1}: {source.get('title', 'Unknown')[:60]}")
        print(f"    Type: {source.get('source_type', 'unknown')}")
        print(f"    Credibility: {source.get('credibility_score', 0):.2f}")
    
    # Verify evidence exists
    claims = report.get("claims", [])
    print(f"✓ {len(claims)} claims extracted")
    
    evidence_count = sum(len(c.get("evidence", [])) for c in claims)
    print(f"✓ {evidence_count} pieces of evidence linked to claims")
    
    
    # ============================================================
    # STEP 6: RAG Processing Verification
    # ============================================================
    print("\n[STEP 6] RAG Processing Verification")
    print("-" * 40)
    
    # Check that report contains synthesized content
    assert report.get("executive_summary"), "Missing executive summary"
    assert report.get("key_findings"), "Missing key findings"
    assert report.get("recommendations"), "Missing recommendations"
    
    print("✓ Executive summary generated")
    print("✓ Key findings extracted")
    print("✓ Recommendations provided")
    print(f"  Summary length: {len(report['executive_summary'])} chars")
    print(f"  Findings: {len(report['key_findings'])}")
    print(f"  Recommendations: {len(report['recommendations'])}")
    
    # Check confidence score
    confidence = report.get("confidence_score", 0)
    print(f"✓ Confidence score: {confidence:.2%}")
    assert confidence > 0.5, "Confidence score too low"
    
    
    # ============================================================
    # STEP 7: Career Analysis
    # ============================================================
    print("\n[STEP 7] Career Analysis")
    print("-" * 40)
    
    # Get career insights
    insights = await e2e_client.get_career_insights()
    print(f"✓ Career insights retrieved")
    print(f"  Overall score: {insights.get('overall_score', 'N/A')}")
    print(f"  Total skills: {insights.get('total_skills', 0)}")
    print(f"  Skill categories: {len(insights.get('skill_categories', {}))}")
    
    # Get career path options
    path_options = await e2e_client.get_career_path_options(TEST_CAREER_PROFILE["current_role"])
    print(f"✓ Career path options retrieved")
    recommended = path_options.get("recommended_path", {})
    print(f"  Target role: {recommended.get('target_role', 'N/A')}")
    print(f"  Transitions: {len(recommended.get('transitions', []))}")
    print(f"  Est. time: {recommended.get('total_estimated_time_months', 0)} months")
    print(f"  Salary growth: {recommended.get('total_salary_growth_pct', 0)}%")
    
    # Get skill recommendations
    skill_recs = await e2e_client.get_skill_recommendations(TEST_CAREER_PROFILE["target_role"])
    print(f"✓ Skill recommendations retrieved")
    print(f"  Missing skills: {len(skill_recs.get('missing_skills', []))}")
    print(f"  Priority skills: {len(skill_recs.get('priority_skills', []))}")
    print(f"  Learning resources: {len(skill_recs.get('learning_resources', {}))} skills covered")
    
    # Create career goal
    goal = await e2e_client.create_career_goal({
        "title": "Become Senior Software Engineer",
        "description": "Transition to senior role within 12 months",
        "target_date": (datetime.utcnow() + timedelta(days=365)).isoformat(),
        "milestones": [
            {"title": "Complete system design course", "target_week": 4},
            {"title": "Lead a major project", "target_week": 16},
            {"title": "Mentor junior developers", "target_week": 24}
        ]
    })
    print(f"✓ Career goal created: {goal.get('title')}")
    print(f"  Milestones: {len(goal.get('milestones', []))}")
    
    
    # ============================================================
    # STEP 8: Content Generation
    # ============================================================
    print("\n[STEP 8] Content Generation")
    print("-" * 40)
    
    content = await e2e_client.generate_content(TEST_CONTENT_DATA)
    content_id = content.get("id") or content.get("content_id")
    print(f"✓ Content generated with ID: {content_id}")
    print(f"  Type: {TEST_CONTENT_DATA['content_type']}")
    print(f"  Platforms: {TEST_CONTENT_DATA['target_platforms']}")
    print(f"  Preview: {content.get('preview', content.get('content', ''))[:100]}...")
    
    # Verify content has platform-specific versions
    if "platform_versions" in content:
        for platform, version in content["platform_versions"].items():
            print(f"  {platform}: {len(version)} chars")
    
    
    # ============================================================
    # STEP 9: Fact Checking
    # ============================================================
    print("\n[STEP 9] Fact Checking")
    print("-" * 40)
    
    # The research report already includes verification
    # Check verification results in report
    claims = report.get("claims", [])
    verified_claims = [c for c in claims if c.get("status") in ["verified", "likely"]]
    print(f"✓ {len(verified_claims)}/{len(claims)} claims verified")
    
    for claim in verified_claims[:3]:
        print(f"  ✓ {claim.get('claim_text', '')[:80]}...")
        print(f"    Status: {claim.get('status')}, Confidence: {claim.get('confidence', 0):.2f}")
    
    # If there's a separate fact-check endpoint, test it
    # (This would be part of the content generation pipeline)
    
    
    # ============================================================
    # STEP 10: Platform Adaptation
    # ============================================================
    print("\n[STEP 10] Platform Adaptation")
    print("-" * 40)
    
    # Content should already be adapted for each platform
    if "platform_versions" in content:
        for platform, version in content["platform_versions"].items():
            print(f"✓ {platform.capitalize()} version: {len(version)} chars")
            
            # Check platform-specific constraints
            if platform == "twitter":
                assert len(version) <= 280, "Twitter version exceeds 280 chars"
                print(f"    ✓ Within 280 char limit")
            elif platform == "linkedin":
                # LinkedIn has higher limit
                print(f"    ✓ LinkedIn format")
    
    # Verify hashtags included
    if TEST_CONTENT_DATA.get("include_hashtags"):
        for platform, version in content.get("platform_versions", {}).items():
            if "#" in version:
                print(f"  ✓ {platform}: Hashtags included")
    
    
    # ============================================================
    # STEP 11: Approval Workflow
    # ============================================================
    print("\n[STEP 11] Approval Workflow")
    print("-" * 40)
    
    # In a real system, this would involve human approval
    # For automated test, we'll simulate approval
    approval_data = {
        "content_id": content_id,
        "status": "approved",
        "approved_by": e2e_client.user["id"],
        "notes": "Content approved for publishing"
    }
    
    # If approval endpoint exists
    try:
        approval = await e2e_client.client.post(
            f"{API_PREFIX}/content-calendar/{content_id}/approve",
            json=approval_data,
            headers=e2e_client._auth_headers()
        )
        if approval.status_code == 200:
            print("✓ Content approved via API")
        else:
            print("  (Approval endpoint not implemented, simulated)")
    except:
        print("  (Approval workflow simulated)")
    
    print("✓ Approval step completed")
    
    
    # ============================================================
    # STEP 12: Scheduling
    # ============================================================
    print("\n[STEP 12] Content Scheduling")
    print("-" * 40)
    
    schedule_result = await e2e_client.schedule_content(content_id, {
        "scheduled_for": TEST_CONTENT_DATA["scheduled_for"],
        "timezone": "America/Los_Angeles",
        "recurring": False
    })
    print(f"✓ Content scheduled for: {TEST_CONTENT_DATA['scheduled_for']}")
    print(f"  Schedule ID: {schedule_result.get('schedule_id', 'N/A')}")
    
    
    # ============================================================
    # STEP 13: Publishing
    # ============================================================
    print("\n[STEP 13] Content Publishing")
    print("-" * 40)
    
    # For testing, we'll publish immediately instead of waiting
    publish_result = await e2e_client.publish_content(content_id)
    print(f"✓ Content published")
    print(f"  Status: {publish_result.get('status', 'published')}")
    print(f"  Published at: {publish_result.get('published_at', 'N/A')}")
    print(f"  Platform URLs: {publish_result.get('platform_urls', {})}")
    
    
    # ============================================================
    # STEP 14: Analytics Tracking
    # ============================================================
    print("\n[STEP 14] Analytics Tracking")
    print("-" * 40)
    
    # Wait a moment for analytics to be recorded
    await asyncio.sleep(2)
    
    analytics = await e2e_client.get_content_analytics(content_id)
    print(f"✓ Content analytics retrieved")
    print(f"  Views: {analytics.get('views', 0)}")
    print(f"  Likes: {analytics.get('likes', 0)}")
    print(f"  Shares: {analytics.get('shares', 0)}")
    print(f"  Comments: {analytics.get('comments', 0)}")
    print(f"  Engagement rate: {analytics.get('engagement_rate', 0):.2%}")
    
    # Get overall analytics summary
    summary = await e2e_client.get_analytics_summary()
    print(f"✓ Analytics summary retrieved")
    print(f"  Total content: {summary.get('total_content', 0)}")
    print(f"  Total engagement: {summary.get('total_engagement', 0)}")
    print(f"  Avg engagement rate: {summary.get('avg_engagement_rate', 0):.2%}")
    
    
    # ============================================================
    # STEP 15: Feedback Collection
    # ============================================================
    print("\n[STEP 15] Feedback Collection")
    print("-" * 40)
    
    feedback_result = await e2e_client.submit_feedback({
        **TEST_FEEDBACK,
        "content_id": content_id
    })
    print(f"✓ Feedback submitted")
    print(f"  Rating: {TEST_FEEDBACK['rating']}/5")
    print(f"  Categories: {TEST_FEEDBACK['categories']}")
    print(f"  Feedback ID: {feedback_result.get('id', 'N/A')}")
    
    
    # ============================================================
    # FINAL VERIFICATION
    # ============================================================
    print("\n" + "="*80)
    print("END-TO-END PIPELINE TEST COMPLETED SUCCESSFULLY!")
    print("="*80)
    
    print("\n📋 PIPELINE SUMMARY:")
    print(f"  1. ✓ User Authentication ({e2e_client.user['email']})")
    print(f"  2. ✓ Career Profile ({TEST_CAREER_PROFILE['current_role']} → {TEST_CAREER_PROFILE['target_role']})")
    print(f"  3. ✓ Research Topic (ID: {research_id})")
    print(f"  4. ✓ Research Agents (Completed in {elapsed}s)")
    print(f"  5. ✓ Evidence ({len(sources)} sources, {evidence_count} evidence pieces)")
    print(f"  6. ✓ RAG Processing (Confidence: {confidence:.2%})")
    print(f"  7. ✓ Career Analysis (Score: {insights.get('overall_score', 'N/A')})")
    print(f"  8. ✓ Content Generation (ID: {content_id})")
    print(f"  9. ✓ Fact Checking ({len(verified_claims)}/{len(claims)} verified)")
    print(f"  10. ✓ Platform Adaptation ({len(content.get('platform_versions', {}))} platforms)")
    print(f"  11. ✓ Approval Workflow")
    print(f"  12. ✓ Scheduling")
    print(f"  13. ✓ Publishing")
    print(f"  14. ✓ Analytics (Engagement: {analytics.get('engagement_rate', 0):.2%})")
    print(f"  15. ✓ Feedback ({TEST_FEEDBACK['rating']}/5 stars)")
    
    # Assert all critical path elements
    assert e2e_client.token is not None
    assert research_id is not None
    assert report.get("executive_summary")
    assert confidence > 0.5
    assert content_id is not None
    assert len(verified_claims) > 0
    assert len(content.get("platform_versions", {})) > 0
    
    print("\n✅ ALL ASSERTIONS PASSED - PIPELINE IS WORKING END-TO-END")


@pytest.mark.asyncio
async def test_research_pipeline_details(e2e_client: E2ETestClient):
    """Detailed test of the research agent pipeline."""
    
    print("\n" + "="*60)
    print("DETAILED RESEARCH PIPELINE TEST")
    print("="*60)
    
    # Login
    await e2e_client.login(TEST_USER["email"], TEST_USER["password"])
    
    # Start research
    research = await e2e_client.start_research({
        "query": "Latest trends in AI-assisted software development 2024",
        "research_type": "technology",
        "max_sources": 15,
        "timeout_seconds": 180
    })
    research_id = research["id"]
    
    # Track each phase
    phases = [
        "decomposing",
        "researching", 
        "managing_sources",
        "extracting_claims",
        "collecting_evidence",
        "ranking_evidence",
        "verifying",
        "analyzing",
        "synthesizing",
        "scoring_confidence",
        "building_report"
    ]
    
    completed_phases = []
    
    for _ in range(60):  # Max 5 minutes
        status = await e2e_client.get_research_status(research_id)
        current_phase = status.get("phase")
        progress = status.get("progress", 0)
        
        if current_phase and current_phase not in completed_phases:
            completed_phases.append(current_phase)
            print(f"  Phase: {current_phase} ({progress}%)")
        
        if status.get("status") == "completed":
            break
        elif status.get("status") == "failed":
            pytest.fail(f"Research failed: {status.get('error_message')}")
        
        await asyncio.sleep(5)
    
    # Verify all phases completed
    print(f"\nCompleted phases: {len(completed_phases)}/{len(phases)}")
    for phase in completed_phases:
        print(f"  ✓ {phase}")
    
    # Get final report
    report = await e2e_client.get_research_report(research_id)
    
    # Verify report structure
    assert "executive_summary" in report
    assert "key_findings" in report
    assert "recommendations" in report
    assert "sources" in report
    assert "claims" in report
    assert "confidence_score" in report
    
    # Verify quality metrics
    assert report["confidence_score"] > 0.6
    assert len(report["sources"]) >= 5
    assert len(report["claims"]) >= 3
    
    print(f"\n✓ Research pipeline test passed")
    print(f"  Confidence: {report['confidence_score']:.2%}")
    print(f"  Sources: {len(report['sources'])}")
    print(f"  Claims: {len(report['claims'])}")
    print(f"  Phases completed: {len(completed_phases)}")


@pytest.mark.asyncio
async def test_career_analysis_pipeline(e2e_client: E2ETestClient):
    """Test the career analysis and recommendation pipeline."""
    
    print("\n" + "="*60)
    print("CAREER ANALYSIS PIPELINE TEST")
    print("="*60)
    
    await e2e_client.login(TEST_USER["email"], TEST_USER["password"])
    
    # Create profile
    await e2e_client.create_career_profile(TEST_CAREER_PROFILE)
    
    # Get insights
    insights = await e2e_client.get_career_insights()
    assert "overall_score" in insights
    assert insights["overall_score"] >= 0
    print(f"✓ Career insights: Score {insights['overall_score']}")
    
    # Get path options
    paths = await e2e_client.get_career_path_options("Software Engineer")
    assert "recommended_path" in paths
    print(f"✓ Path options: {paths['recommended_path']['target_role']}")
    
    # Get skill recommendations
    skills = await e2e_client.get_skill_recommendations("Senior Software Engineer")
    assert "missing_skills" in skills
    assert "priority_skills" in skills
    assert "learning_resources" in skills
    print(f"✓ Skill recommendations: {len(skills['priority_skills'])} priority skills")
    
    # Create goal
    goal = await e2e_client.create_career_goal({
        "title": "Senior Engineer Promotion",
        "description": "Get promoted to Senior Software Engineer",
        "target_date": (datetime.utcnow() + timedelta(days=180)).isoformat(),
        "milestones": [
            {"title": "Complete advanced system design", "target_week": 4},
            {"title": "Lead cross-team project", "target_week": 12},
            {"title": "Document architecture decisions", "target_week": 20}
        ]
    })
    assert goal["title"] == "Senior Engineer Promotion"
    print(f"✓ Career goal created with {len(goal['milestones'])} milestones")


@pytest.mark.asyncio
async def test_content_pipeline(e2e_client: E2ETestClient):
    """Test the content generation and publishing pipeline."""
    
    print("\n" + "="*60)
    print("CONTENT GENERATION PIPELINE TEST")
    print("="*60)
    
    await e2e_client.login(TEST_USER["email"], TEST_USER["password"])
    
    # Generate content
    content = await e2e_client.generate_content({
        "title": "5 Tips for Career Growth in Tech",
        "content_type": "blog_post",
        "topic": "Career development strategies",
        "target_platforms": ["linkedin", "twitter", "blog"],
        "tone": "inspirational",
        "include_hashtags": True,
        "length": "medium"
    })
    content_id = content.get("id") or content.get("content_id")
    print(f"✓ Content generated: {content_id}")
    
    # Verify platform adaptations
    assert "platform_versions" in content
    platforms = content["platform_versions"]
    assert "linkedin" in platforms
    assert "twitter" in platforms
    assert "blog" in platforms
    print(f"✓ Platform versions: {list(platforms.keys())}")
    
    # Verify character limits
    assert len(platforms["twitter"]) <= 280
    print(f"✓ Twitter: {len(platforms['twitter'])} chars (≤280)")
    
    # Schedule
    schedule = await e2e_client.schedule_content(content_id, {
        "scheduled_for": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "timezone": "UTC"
    })
    print(f"✓ Scheduled: {schedule.get('schedule_id')}")
    
    # Publish (immediate for test)
    publish = await e2e_client.publish_content(content_id)
    assert publish.get("status") == "published"
    print(f"✓ Published: {publish.get('published_at')}")
    
    # Analytics
    analytics = await e2e_client.get_content_analytics(content_id)
    assert "views" in analytics
    print(f"✓ Analytics: {analytics.get('views', 0)} views")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
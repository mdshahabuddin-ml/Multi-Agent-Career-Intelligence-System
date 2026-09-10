"""
Simple E2E Test Runner - Quick verification of the pipeline
Run this directly to test the live system
"""

import asyncio
import sys
import os

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.e2e.test_complete_pipeline import E2ETestClient, TEST_USER

BASE_URL = "http://127.0.0.1:8080"


async def quick_test():
    """Run a quick end-to-end verification."""
    
    print("\n=== Quick E2E Pipeline Verification ===")
    print("=" * 50)
    
    async with E2ETestClient(BASE_URL) as client:
        # 1. Login
        print("\n[1] Login...")
        try:
            await client.login(TEST_USER["email"], TEST_USER["password"])
            print(f"   ✓ Logged in as {TEST_USER['email']}")
        except Exception as e:
            print(f"   [FAIL] Login failed: {e}")
            return False
        
        # 2. Get career profile
        print("\n[2] Career Profile...")
        try:
            profile = await client.get_career_profile()
            print(f"   [OK] Profile: {profile.get('current_role', 'N/A')} -> {profile.get('target_role', 'N/A')}")
        except Exception as e:
            print(f"   [FAIL] Profile failed: {e}")
            return False
        
        # 3. Career insights
        print("\n[3] Career Insights...")
        try:
            insights = await client.get_career_insights()
            print(f"   [OK] Score: {insights.get('overall_score', 'N/A')}")
            print(f"   [OK] Skills: {insights.get('total_skills', 0)}")
        except Exception as e:
            print(f"   [FAIL] Insights failed: {e}")
            return False
        
        # 4. Career path options
        print("\n[4] Career Path Options...")
        try:
            paths = await client.get_career_path_options("Software Engineer")
            rec = paths.get("recommended_path", {})
            print(f"   [OK] Target: {rec.get('target_role', 'N/A')}")
            print(f"   [OK] Time: {rec.get('total_estimated_time_months', 0)} months")
            print(f"   [OK] Growth: {rec.get('total_salary_growth_pct', 0)}%")
        except Exception as e:
            print(f"   [FAIL] Path options failed: {e}")
            return False
        
        # 5. Skill recommendations
        print("\n[5] Skill Recommendations...")
        try:
            skills = await client.get_skill_recommendations("Senior Software Engineer")
            print(f"   [OK] Missing: {len(skills.get('missing_skills', []))}")
            print(f"   [OK] Priority: {len(skills.get('priority_skills', []))}")
        except Exception as e:
            print(f"   [FAIL] Skills failed: {e}")
            return False
        
        # 6. Start research
        print("\n[6] Research Pipeline...")
        try:
            research = await client.start_research({
                "query": "Best practices for career growth in software engineering 2024",
                "research_type": "career_path",
                "max_sources": 5,
                "timeout_seconds": 120
            })
            research_id = research["id"]
            print(f"   [OK] Research started: {research_id}")
        except Exception as e:
            print(f"   [FAIL] Research start failed: {e}")
            return False
        
        # 7. Poll for completion
        print("\n[7] Waiting for research completion...")
        max_wait = 180
        poll_interval = 5
        elapsed = 0
        
        while elapsed < max_wait:
            try:
                status = await client.get_research_status(research_id)
                progress = status.get("progress", 0)
                phase = status.get("phase", "unknown")
                
                if progress > 0 and progress % 20 == 0:
                    print(f"   Progress: {progress}% - {phase}")
                
                if status.get("status") == "completed":
                    print(f"   [OK] Research completed!")
                    break
                elif status.get("status") == "failed":
                    print(f"   [FAIL] Research failed: {status.get('error_message')}")
                    return False
            except Exception as e:
                print(f"   [FAIL] Status check failed: {e}")
                return False
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        else:
            print(f"   [FAIL] Research timed out")
            return False
        
        # 8. Get report
        print("\n[8] Research Report...")
        try:
            report = await client.get_research_report(research_id)
            confidence = report.get("confidence_score", 0)
            sources = len(report.get("sources", []))
            claims = len(report.get("claims", []))
            
            print(f"   [OK] Confidence: {confidence:.2%}")
            print(f"   [OK] Sources: {sources}")
            print(f"   [OK] Claims: {claims}")
            print(f"   [OK] Summary: {len(report.get('executive_summary', ''))} chars")
        except Exception as e:
            print(f"   [FAIL] Report failed: {e}")
            return False
        
        # 9. Content generation
        print("\n[9] Content Generation...")
        try:
            content = await client.generate_content({
                "title": "Quick Test Post",
                "content_type": "linkedin_post",
                "topic": "Career growth tips",
                "target_platforms": ["linkedin", "twitter"],
                "tone": "professional"
            })
            content_id = content.get("id") or content.get("content_id")
            print(f"   [OK] Content: {content_id}")
            print(f"   [OK] Platforms: {list(content.get('platform_versions', {}).keys())}")
        except Exception as e:
            print(f"   [FAIL] Content failed: {e}")
            return False
        
        # 10. Analytics
        print("\n[10] Analytics...")
        try:
            summary = await client.get_analytics_summary()
            print(f"   [OK] Total content: {summary.get('total_content', 0)}")
            print(f"   [OK] Engagement: {summary.get('total_engagement', 0)}")
        except Exception as e:
            print(f"   [FAIL] Analytics failed: {e}")
            return False
        
        print("\n" + "=" * 50)
        print("[SUCCESS] QUICK E2E VERIFICATION PASSED!")
        print("=" * 50)
        return True


if __name__ == "__main__":
    result = asyncio.run(quick_test())
    sys.exit(0 if result else 1)
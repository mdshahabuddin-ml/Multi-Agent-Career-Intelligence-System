#!/usr/bin/env python3
"""
E2E Test Runner for CareerIntel AI

This script runs the end-to-end tests against a running instance of the application.
Make sure the backend is running on http://localhost:8000 (or configure BASE_URL)

Usage:
    python run_e2e_tests.py [--url BASE_URL]
"""

import argparse
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.e2e.test_complete_pipeline import (
    E2ETestClient,
    test_complete_e2e_pipeline,
    test_research_pipeline_details,
    test_career_analysis_pipeline,
    test_content_pipeline,
    TEST_USER,
    TEST_CAREER_PROFILE,
    TEST_RESEARCH_TOPIC
)

# Override BASE_URL if provided via command line
import tests.e2e.test_complete_pipeline as test_module


async def run_single_test(test_func, client, name):
    """Run a single test and report results."""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print(f"{'='*60}")
    try:
        await test_func(client)
        print(f"\n✅ {name} PASSED")
        return True
    except Exception as e:
        print(f"\n❌ {name} FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    parser = argparse.ArgumentParser(description="Run E2E tests for CareerIntel AI")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend API base URL")
    parser.add_argument("--test", choices=["all", "complete", "research", "career", "content"], 
                       default="all", help="Which test to run")
    parser.add_argument("--email", default=TEST_USER["email"], help="Test user email")
    parser.add_argument("--password", default=TEST_USER["password"], help="Test user password")
    args = parser.parse_args()
    
    # Update test module BASE_URL
    test_module.BASE_URL = args.url
    
    print(f"🧪 CareerIntel AI E2E Test Runner")
    print(f"   Backend URL: {args.url}")
    print(f"   Test user: {args.email}")
    
    async with E2ETestClient(args.url) as client:
        # Login or register
        try:
            await client.login(args.email, args.password)
            print(f"✓ Logged in as {args.email}")
        except Exception:
            print(f"Registering new user...")
            await client.register(args.email, args.password, "E2E Test User")
            print(f"✓ Registered and logged in")
        
        results = []
        
        if args.test in ["all", "complete"]:
            results.append(await run_single_test(test_complete_e2e_pipeline, client, "Complete E2E Pipeline"))
        
        if args.test in ["all", "research"]:
            results.append(await run_single_test(test_research_pipeline_details, client, "Research Pipeline Details"))
        
        if args.test in ["all", "career"]:
            results.append(await run_single_test(test_career_analysis_pipeline, client, "Career Analysis Pipeline"))
        
        if args.test in ["all", "content"]:
            results.append(await run_single_test(test_content_pipeline, client, "Content Generation Pipeline"))
        
        # Summary
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        passed = sum(results)
        total = len(results)
        print(f"Passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            print("❌ SOME TESTS FAILED")
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
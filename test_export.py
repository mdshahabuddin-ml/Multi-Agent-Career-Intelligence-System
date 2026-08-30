import asyncio
from backend.main import app
from backend.database import get_db, Base, engine
from backend.models import User, Organization, OrganizationPlan, Research, ResearchStatus, ResearchType
from backend.services.research_service import ResearchService

# Drop and recreate tables
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Enable testing mode
from backend.security.config import security_config
security_config.TESTING = True

# Use the same session for everything
from sqlalchemy.orm import Session
session = Session(bind=engine)

# Create org and user
org = Organization(
    name='Test Organization',
    slug='test-org-export-3',
    plan=OrganizationPlan.PROFESSIONAL,
    max_research_per_month=500,
)
session.add(org)
session.commit()
session.refresh(org)
print(f'Org ID: {org.id}')

user = User(
    email='test-export-3@example.com',
    hashed_password='test',
    is_active=True,
    organization_id=org.id,
)
session.add(user)
session.commit()
session.refresh(user)
print(f'User ID: {user.id}')

# Create research
report_json = '{"title": "Test Report", "executive_summary": "Test summary", "key_findings": ["Finding 1", "Finding 2"], "recommendations": ["Rec 1", "Rec 2"], "methodology": "Test methodology", "limitations": ["Limitation 1"], "sources": [], "citations": [], "confidence": 0.85}'
research = Research(
    user_id=user.id,
    query='Test export',
    research_type=ResearchType.JOB_MARKET,
    status=ResearchStatus.COMPLETED,
    executive_summary='Test summary',
    key_findings=['Finding 1', 'Finding 2'],
    recommendations=['Rec 1', 'Rec 2'],
    report=report_json,
)
session.add(research)
session.commit()
session.refresh(research)
print(f'Research ID: {research.id}')

# Test export
from backend.services.research_service import ResearchService
service = ResearchService(session)

# Test export
import asyncio
result = asyncio.run(service.export_research_report(research.id, user.id, 'markdown'))
print(f'Export result: {result[:100] if result else None}...')
print(f'Research report_data: {research.report_data}')
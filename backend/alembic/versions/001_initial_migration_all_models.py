"""Initial migration - all models

Revision ID: 001
Revises: 
Create Date: 2026-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create profiles table
    op.create_table(
        'profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('headline', sa.String(length=500), nullable=True),
        sa.Column('target_role', sa.String(length=255), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('years_of_experience', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_profiles_id'), 'profiles', ['id'], unique=False)
    op.create_index(op.f('ix_profiles_user_id'), 'profiles', ['user_id'], unique=False)

    # Create skills table
    op.create_table(
        'skills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('proficiency', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skills_id'), 'skills', ['id'], unique=False)
    op.create_index(op.f('ix_skills_profile_id'), 'skills', ['profile_id'], unique=False)

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('technologies', sa.Text(), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_profile_id'), 'projects', ['profile_id'], unique=False)

    # Create experiences table
    op.create_table(
        'experiences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_experiences_id'), 'experiences', ['id'], unique=False)
    op.create_index(op.f('ix_experiences_profile_id'), 'experiences', ['profile_id'], unique=False)

    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('company_size', sa.String(length=50), nullable=True),
        sa.Column('headquarters', sa.String(length=255), nullable=True),
        sa.Column('founded_year', sa.Integer(), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('linkedin_url', sa.String(length=500), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('tech_stack', sa.JSON(), nullable=True),
        sa.Column('culture_tags', sa.JSON(), nullable=True),
        sa.Column('benefits', sa.JSON(), nullable=True),
        sa.Column('glassdoor_rating', sa.Float(), nullable=True),
        sa.Column('glassdoor_reviews_count', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_companies_domain'), 'companies', ['domain'], unique=False)
    op.create_index(op.f('ix_companies_id'), 'companies', ['id'], unique=False)
    op.create_index(op.f('ix_companies_name'), 'companies', ['name'], unique=False)
    op.create_index(op.f('ix_companies_normalized_name'), 'companies', ['normalized_name'], unique=False)

    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('is_remote', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('remote_type', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('responsibilities', sa.Text(), nullable=True),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('salary_currency', sa.String(length=10), nullable=False, server_default=sa.text("'USD'")),
        sa.Column('salary_period', sa.String(length=20), nullable=True),
        sa.Column('experience_level', sa.String(length=50), nullable=True),
        sa.Column('employment_type', sa.String(length=50), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default=sa.text("'other'")),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('source_job_id', sa.String(length=255), nullable=True),
        sa.Column('posted_date', sa.DateTime(), nullable=True),
        sa.Column('expires_date', sa.DateTime(), nullable=True),
        sa.Column('application_url', sa.String(length=1000), nullable=True),
        sa.Column('application_email', sa.String(length=255), nullable=True),
        sa.Column('skills', sa.JSON(), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_company_id'), 'jobs', ['company_id'], unique=False)
    op.create_index(op.f('ix_jobs_id'), 'jobs', ['id'], unique=False)
    op.create_index(op.f('ix_jobs_title'), 'jobs', ['title'], unique=False)

    # Create resumes table
    op.create_table(
        'resumes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'uploaded'")),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('parsed_data', sa.JSON(), nullable=True),
        sa.Column('sections', sa.JSON(), nullable=True),
        sa.Column('extracted_skills', sa.JSON(), nullable=True),
        sa.Column('extracted_projects', sa.JSON(), nullable=True),
        sa.Column('extracted_experience', sa.JSON(), nullable=True),
        sa.Column('extracted_education', sa.JSON(), nullable=True),
        sa.Column('ats_score', sa.Float(), nullable=True),
        sa.Column('ats_feedback', sa.JSON(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_resumes_id'), 'resumes', ['id'], unique=False)
    op.create_index(op.f('ix_resumes_user_id'), 'resumes', ['user_id'], unique=False)

    # Create applications table
    op.create_table(
        'applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('resume_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'draft'")),
        sa.Column('cover_letter', sa.Text(), nullable=True),
        sa.Column('application_answers', sa.JSON(), nullable=True),
        sa.Column('applied_date', sa.DateTime(), nullable=True),
        sa.Column('response_date', sa.DateTime(), nullable=True),
        sa.Column('interview_date', sa.DateTime(), nullable=True),
        sa.Column('interview_notes', sa.Text(), nullable=True),
        sa.Column('offer_details', sa.JSON(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('follow_up_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('external_application_id', sa.String(length=255), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_applications_id'), 'applications', ['id'], unique=False)
    op.create_index(op.f('ix_applications_job_id'), 'applications', ['job_id'], unique=False)
    op.create_index(op.f('ix_applications_user_id'), 'applications', ['user_id'], unique=False)

    # Create research table
    op.create_table(
        'research',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('research_type', sa.String(length=50), nullable=False, server_default=sa.text("'general'")),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'created'")),
        sa.Column('research_plan', sa.JSON(), nullable=True),
        sa.Column('target_role', sa.String(length=255), nullable=True),
        sa.Column('target_company', sa.String(length=255), nullable=True),
        sa.Column('target_location', sa.String(length=255), nullable=True),
        sa.Column('max_sources', sa.Integer(), nullable=False, server_default=sa.text('10')),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default=sa.text('300')),
        sa.Column('report', sa.Text(), nullable=True),
        sa.Column('executive_summary', sa.Text(), nullable=True),
        sa.Column('key_findings', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('source_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('verified_claim_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_research_id'), 'research', ['id'], unique=False)
    op.create_index(op.f('ix_research_user_id'), 'research', ['user_id'], unique=False)

    # Create research_sources table
    op.create_table(
        'research_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('research_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=False, server_default=sa.text("'web'")),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('published_date', sa.DateTime(), nullable=True),
        sa.Column('retrieved_date', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('credibility_score', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('relevance_score', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('source_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['research_id'], ['research.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_research_sources_id'), 'research_sources', ['id'], unique=False)
    op.create_index(op.f('ix_research_sources_research_id'), 'research_sources', ['research_id'], unique=False)

    # Create research_claims table
    op.create_table(
        'research_claims',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('research_id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('claim_text', sa.Text(), nullable=False),
        sa.Column('claim_type', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'extracted'")),
        sa.Column('confidence', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('verified_by_sources', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('conflicting_sources', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('claim_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['research_id'], ['research.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['research_sources.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_research_claims_id'), 'research_claims', ['id'], unique=False)
    op.create_index(op.f('ix_research_claims_research_id'), 'research_claims', ['research_id'], unique=False)
    op.create_index(op.f('ix_research_claims_source_id'), 'research_claims', ['source_id'], unique=False)

    # Create research_evidence table
    op.create_table(
        'research_evidence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('research_id', sa.Integer(), nullable=False),
        sa.Column('claim_id', sa.Integer(), nullable=True),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('evidence_text', sa.Text(), nullable=False),
        sa.Column('evidence_type', sa.String(length=50), nullable=False, server_default=sa.text("'other'")),
        sa.Column('supports_claim', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('relevance_score', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('citation_context', sa.Text(), nullable=True),
        sa.Column('evidence_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['claim_id'], ['research_claims.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['research_id'], ['research.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['research_sources.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_research_evidence_claim_id'), 'research_evidence', ['claim_id'], unique=False)
    op.create_index(op.f('ix_research_evidence_id'), 'research_evidence', ['id'], unique=False)
    op.create_index(op.f('ix_research_evidence_research_id'), 'research_evidence', ['research_id'], unique=False)
    op.create_index(op.f('ix_research_evidence_source_id'), 'research_evidence', ['source_id'], unique=False)

    # Create interviews table
    op.create_table(
        'interviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('interview_type', sa.String(length=50), nullable=False, server_default=sa.text("'mock'")),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'scheduled'")),
        sa.Column('target_role', sa.String(length=255), nullable=True),
        sa.Column('target_company', sa.String(length=255), nullable=True),
        sa.Column('questions', sa.JSON(), nullable=True),
        sa.Column('answers', sa.JSON(), nullable=True),
        sa.Column('evaluations', sa.JSON(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('strengths', sa.JSON(), nullable=True),
        sa.Column('weaknesses', sa.JSON(), nullable=True),
        sa.Column('improvement_areas', sa.JSON(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_interviews_application_id'), 'interviews', ['application_id'], unique=False)
    op.create_index(op.f('ix_interviews_id'), 'interviews', ['id'], unique=False)
    op.create_index(op.f('ix_interviews_user_id'), 'interviews', ['user_id'], unique=False)

    # Create learning_plans table
    op.create_table(
        'learning_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('target_role', sa.String(length=255), nullable=False),
        sa.Column('skill_gaps', sa.JSON(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('estimated_weeks', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('resources', sa.JSON(), nullable=True),
        sa.Column('milestones', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'not_started'")),
        sa.Column('progress_percentage', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('target_completion_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_learning_plans_id'), 'learning_plans', ['id'], unique=False)
    op.create_index(op.f('ix_learning_plans_user_id'), 'learning_plans', ['user_id'], unique=False)

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False, server_default=sa.text("'system'")),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default=sa.text("'medium'")),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('action_url', sa.String(length=500), nullable=True),
        sa.Column('action_label', sa.String(length=100), nullable=True),
        sa.Column('notification_metadata', sa.JSON(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('learning_plans')
    op.drop_table('interviews')
    op.drop_table('research_evidence')
    op.drop_table('research_claims')
    op.drop_table('research_sources')
    op.drop_table('research')
    op.drop_table('applications')
    op.drop_table('resumes')
    op.drop_table('jobs')
    op.drop_table('companies')
    op.drop_table('experiences')
    op.drop_table('projects')
    op.drop_table('skills')
    op.drop_table('profiles')
    op.drop_table('users')
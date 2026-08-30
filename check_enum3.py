from backend.database import engine, Base
from backend.models import user, profile, job, company, resume, application, research_claim, research_evidence, research_source, research, experience, project, skill, learning_plan, notification, interview, organization, monitoring, preference
Base.metadata.create_all(bind=engine)
print('Tables recreated successfully')

from backend.models.job import JobSource
print('JobSource enum values:')
for e in JobSource:
    print(f'  {e.name} = {e.value}')

from sqlalchemy import inspect
inspector = inspect(engine)
columns = inspector.get_columns('jobs')
for col in columns:
    if col['name'] == 'source':
        print('Source column type:', col['type'])
        if hasattr(col['type'], 'enums'):
            print('  Enum values:', col['type'].enums)
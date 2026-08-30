from backend.database import engine, Base
from backend.models import user, profile, job, company, resume, application, research_claim, research_evidence, research_source, research, experience, project, skill, learning_plan, notification, interview, organization, monitoring, preference
from backend.models.job import JobSource, Job
from sqlalchemy import inspect

Base.metadata.create_all(bind=engine)
print('Tables recreated successfully')

# Check enum values
print('JobSource enum values:')
for e in JobSource:
    print(f'  {e.name} = {e.value}')

# Check the actual enum values in the database
inspector = inspect(engine)
columns = inspector.get_columns('jobs')
for col in columns:
    if col['name'] == 'source':
        print(f'Source column type: {col["type"]}')
        if hasattr(col['type'], 'enums'):
            print(f'  Enum values: {col["type"].enums}')
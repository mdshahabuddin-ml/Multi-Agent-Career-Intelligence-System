import sys
# Import all API modules to see which ones have routers
from backend.api import auth, health, resume, jobs, research, career, applications, evaluation, security, data_pipeline, personalization, organization, monitoring, admin, rate_limits

modules = {
    'auth': auth,
    'health': health,
    'resume': resume,
    'jobs': jobs,
    'research': research,
    'career': career,
    'applications': applications,
    'evaluation': evaluation,
    'security': security,
    'data_pipeline': data_pipeline,
    'personalization': personalization,
    'organization': organization,
    'monitoring': monitoring,
    'admin': admin,
    'rate_limits': rate_limits,
}

for name, mod in modules.items():
    if hasattr(mod, 'router'):
        print(f'Module: {name}')
        print(f'  File: {mod.__file__}')
        for r in mod.router.routes:
            print(f'  {r.path} - {r.methods}')
        print()
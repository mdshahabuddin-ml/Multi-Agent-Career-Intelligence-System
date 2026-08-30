with open('backend/agents/application/application_answer_agent.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 381 (index 380)
# The issue is the extra ) at the end of the f-string
fixed_line = "                return f\"I have {years} years of experience as a {exp.get('role', 'professional')}. At {exp.get('company', 'my company')}, I {exp.get('description', 'worked on various projects using ' + ', '.join([s.get('name', '') for s in skills[:3]])}. Key achievement: {profile.get('achievements', ['delivered significant results'])[0]}.\"\n"

lines[380] = fixed_line

with open('backend/agents/application/application_answer_agent.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed application_answer_agent.py line 381')
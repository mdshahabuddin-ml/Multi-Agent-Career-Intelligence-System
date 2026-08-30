with open('backend/agents/application/application_answer_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The problematic line has an extra ) at the end of the f-string
# Find and replace the exact problematic line
old = '''                return f"I have {years} years of experience as a {exp.get('role', 'professional')}. At {exp.get('company', 'my company')}, I {exp.get('description', 'worked on various projects using ' + ', '.join([s.get('name', '') for s in skills[:3]])}. Key achievement: {profile.get('achievements', ['delivered significant results'])[0]}."'''

new = '''                # Build description with skills
                skill_names = ", ".join([s.get("name", "") for s in skills[:3]])
                desc_default = f"worked on various projects using {skill_names}"
                description = exp.get("description", desc_default)
                key_achievement = profile.get("achievements", ["delivered significant results"])[0]
                return f"I have {years} years of experience as a {exp.get('role', 'professional')}. At {exp.get('company', 'my company')}, I {description}. Key achievement: {key_achievement}."'''

with open('backend/agents/application/application_answer_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(old, new)

with open('backend/agents/application/application_answer_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed line 381')
with open('backend/agents/application/application_answer_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the problematic line
old_line = "                return f\"I have {years} years of experience as a {exp.get('role', 'professional')}. At {exp.get('company', 'my company')}, I {exp.get('description', 'worked on various projects using ' + ', '.join([s.get('name', '') for s in skills[:3]])}. Key achievement: {profile.get('achievements', ['delivered significant results'])[0]}.\""

new_lines = [
    '            if experiences:\n',
    '                exp = experiences[0]\n',
    '                # Build description with skills\n',
    '                skill_names = ", ".join([s.get("name", "") for s in skills[:3]])\n',
    '                desc_default = f"worked on various projects using {skill_names}"\n',
    '                description = exp.get("description", desc_default)\n',
    '                key_achievement = profile.get("achievements", ["delivered significant results"])[0]\n',
    '                return f"I have {years} years of experience as a {exp.get(\'role\', \'professional\')}. At {exp.get(\'company\', \'my company\')}, I {description}. Key achievement: {key_achievement}."\n',
]

# Replace the problematic block
import re
pattern = r'if experiences:\s+exp = experiences\[0\]\s+return f"I have \{years\} years of experience as a \{exp\.get\(\'role\', \'professional\'\)\}\. At \{exp\.get\(\'company\', \'my company\'\)\}, I \{exp\.get\(\'description\', \'worked on various projects using \' \+ \', \'\.join\(\[s\.get\(\'name\', \'\'\) for s in skills\[:3\]\)\)\}\. Key achievement: \{profile\.get\(\'achievements\', \[\'delivered significant results\'\]\)\[0\]\}\."'
replacement = '''            if experiences:
                exp = experiences[0]
                # Build description with skills
                skill_names = ", ".join([s.get("name", "") for s in skills[:3]])
                desc_default = f"worked on various projects using {skill_names}"
                description = exp.get("description", desc_default)
                key_achievement = profile.get("achievements", ["delivered significant results"])[0]
                return f"I have {years} years of experience as a {exp.get('role', 'professional')}. At {exp.get('company', 'my company')}, I {description}. Key achievement: {key_achievement}."'''

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('backend/agents/application/application_answer_agent.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Fixed application_answer_agent.py')
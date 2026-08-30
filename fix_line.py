with open('backend/agents/application/application_answer_agent.py', 'rb') as f:
    content = f.read()
lines = content.split(b'\n')

# Fix line 381 (index 380)
fixed_line = b'                return f"I have {years} years of experience as a {exp.get(\'role\', \'professional\')}. At {exp.get(\'company\', \'my company\')}, I {exp.get(\'description\', \'worked on various projects using \' + \', \'.join([s.get(\'name\', \'\') for s in skills[:3]])}. Key achievement: {profile.get(\'achievements\', [\'delivered significant results\'])[0]}."'
lines[380] = fixed_line

content = b'\n'.join(lines)
with open('backend/agents/application/application_answer_agent.py', 'wb') as f:
    f.write(content)
print('Fixed line 381')
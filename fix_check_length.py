with open('backend/agents/application/ats_resume_agent.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Replace lines 495-512 (indices 494-511) with a clean version
new_lines = lines[:494]  # up to line 494 (empty line before if)

new_method = [
    '        if word_count < 300:\n',
    '            issues.append(ATSIssue(\n',
    '                type=ATSIssueType.LENGTH,\n',
    '                severity=ATSIssueSeverity.MEDIUM,\n',
    '                title="Resume too short",\n',
    '                description=f"Only {word_count} words. Resume may lack sufficient detail.",\n',
    '                suggestion="Expand on experience, projects, and skills. Aim for 400-800 words for most roles.",\n',
    '            ))\n',
    '        elif word_count > 1000:\n',
    '            issues.append(ATSIssue(\n',
    '                type=ATSIssueType.LENGTH,\n',
    '                severity=ATSIssueSeverity.MEDIUM,\n',
    '                title="Resume too long",\n',
    '                description=f"{word_count} words exceeds recommended length for most roles.",\n',
    '                suggestion="Condense to 1-2 pages. Focus on recent, relevant experience. Remove outdated information.",\n',
    '            ))\n',
    '\n',
    '        return issues\n',
    '\n',
]

# Replace lines 495-512 (indices 494-511)
new_content = lines[:494] + new_method + lines[512:]

with open('backend/agents/application/ats_resume_agent.py', 'w', encoding='utf-8') as f:
    f.writelines(new_content)

print('Rewrote _check_length method')
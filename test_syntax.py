import ast

code = '''class Test:
    def _check_length(self, text: str) -> List[ATSIssue]:
        """Check resume length."""
        issues = []
        word_count = len(text.split())

        if word_count < 300:
            issues.append(ATSIssue(
                type=ATSIssueType.LENGTH,
                severity=ATSIssueSeverity.MEDIUM,
                title="Resume too short",
                description=f"Only {word_count} words. Resume may lack sufficient detail.",
                suggestion="Expand on experience, projects, and skills. Aim for 400-800 words for most roles.",
            ))
        elif word_count > 1000:
            issues.append(ATSIssue(
                type=ATSIssueType.LENGTH,
                severity=ATSIssueSeverity.MEDIUM,
                title="Resume too long",
                description=f"{word_count} words exceeds recommended length for most roles.",
                suggestion="Condense to 1-2 pages. Focus on recent, relevant experience. Remove outdated information.",
            ))

        return issues
'''

try:
    ast.parse(code)
    print('Isolated method parses OK')
except SyntaxError as e:
    print(f'Error: {e}')
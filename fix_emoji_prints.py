#!/usr/bin/env python3
"""Comment out emoji print statements in auth_routes.py"""

import re

# Read the file
with open('backend/app/routes/auth_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace print statements with emoji with logger calls or comments
# Match print(...) statements that contain non-ASCII characters
replacements = [
    # Replace print(...emoji...) with logger.info(...) or logger.debug(...)
    (r'print\(f?"([^"]*[^\x00-\x7F][^"]*)"\)', r'logger.debug("...")'),  # This is too simplistic
]

# Better approach: use a regex to find and replace print statements with high unicode values
lines = content.split('\n')
new_lines = []

for i, line in enumerate(lines):
    # If line contains a print statement with non-ASCII chars, comment it out
    if 'print(' in line and any(ord(c) > 127 for c in line):
        new_lines.append('    # ' + line.lstrip() if line.startswith(' ') else '# ' + line)
    else:
        new_lines.append(line)

# Write back
with open('backend/app/routes/auth_routes.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("Done! Commented out emoji print statements")

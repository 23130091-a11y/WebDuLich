#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to fix ai_engine.py neutral soft handling"""

import re

# Read file
with open('travel/ai_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the dampen value from 0.35 to 0.15
# Also change weights from 0.40/0.60 to 0.30/0.70
old_pattern = r'combined = 0\.40 \* phobert_score \+ 0\.60 \* rule_score\s+dampened = combined \* 0\.35'
new_code = 'combined = 0.30 * phobert_score + 0.70 * rule_score\n            dampened = combined * 0.15'

# Check if pattern exists
if re.search(old_pattern, content):
    content = re.sub(old_pattern, new_code, content)
    with open('travel/ai_engine.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Updated neutral soft damping from 0.35 to 0.15')
else:
    # Try simpler replacement
    if '0.40 * phobert_score + 0.60 * rule_score' in content:
        # Find the specific occurrence (second one, around line 422)
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '0.40 * phobert_score + 0.60 * rule_score' in line and i > 415 and i < 430:
                lines[i] = line.replace('0.40 * phobert_score + 0.60 * rule_score', 
                                        '0.30 * phobert_score + 0.70 * rule_score')
                print(f'Updated line {i+1}: weights changed to 0.30/0.70')
            if 'dampened = combined * 0.35' in line and i > 415 and i < 430:
                lines[i] = line.replace('dampened = combined * 0.35', 
                                        'dampened = combined * 0.15')
                print(f'Updated line {i+1}: damping changed to 0.15')
        
        content = '\n'.join(lines)
        with open('travel/ai_engine.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('SUCCESS: File updated')
    else:
        print('Pattern not found - checking file content...')
        lines = content.split('\n')
        for i in range(418, 428):
            if i < len(lines):
                print(f'{i+1}: {lines[i]}')

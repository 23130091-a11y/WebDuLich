
import os
import re

file_path = r"e:\DuLich2\WebDuLich\travel\templates\travel\search.html"

if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # We need to join lines where {% endif %} is split
    # Pattern: {% endif(\s+)%}
    # We replace with {% endif %}
    
    # Also handle {% if ... %} split if any
    
    # Regex to fix split tag closing
    # matches: some content, then newline/spaces, then %} -> replace with %} 
    # But only if it looks like a tag end.
    
    # Specific fix for the known issues:
    # 1. {% endif \n\s+%}> -> {% endif %}>
    
    new_content = re.sub(r"{% endif\s+%}>", "{% endif %}>", content)
    
    # Also fix the start tag if it was split: {% if ... \n ... %} (less likely based on error)
    
    # Fix the == spacing again just in case, though likely done.
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Fixed split template tags.")
    else:
        print("No split tags found matching pattern.")

    # Verification: check for any remaining split tags
    remaining = re.findall(r"{%[^%]*\n[^%]*%}", new_content)
    if remaining:
        print(f"Warning: {len(remaining)} split tags remain.")
        for r in remaining[:3]:
            print(f"Sample: {r!r}")

else:
    print(f"File not found: {file_path}")

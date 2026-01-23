
import os
import re

file_path = r"e:\DuLich2\WebDuLich\travel\templates\travel\search.html"

if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Generic replace for equality operators in django tags
    # This regex looks for {% if ... ==... %} and ensures spaces
    # But carefully.
    
    # Specific replacements based on view_file
    replacements = [
        ("filters.location==loc", "filters.location == loc"),
        ("filters.travel_type==type", "filters.travel_type == type"),
        ("filters.max_price=='500000'", "filters.max_price == '500000'"),
        ("filters.max_price=='1000000'", "filters.max_price == '1000000'"),
        ("filters.max_price=='2000000'", "filters.max_price == '2000000'"),
        ("filters.max_price=='5000000'", "filters.max_price == '5000000'"),
        ("filters.min_rating=='5'", "filters.min_rating == '5'"),
        ("filters.min_rating=='4'", "filters.min_rating == '4'"),
        ("filters.min_rating=='3'", "filters.min_rating == '3'"),
    ]

    new_content = content
    for old, new in replacements:
        new_content = new_content.replace(old, new)
    
    # Also try a regex for any other cases I missed: something==something inside {% %}
    # Regex: ({%[^%]*?)(\S)==(\S)(.*%}) -> \1\2 == \3\4
    # But python's re is tricky with overlapping. Let's stick to explicit replacements first.
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed {file_path}")
    else:
        print(f"No changes needed for {file_path}")
else:
    print(f"File not found: {file_path}")

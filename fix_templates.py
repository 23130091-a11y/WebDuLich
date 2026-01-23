
import os

files_to_fix = [
    r"e:\DuLich2\WebDuLich\travel\templates\travel\all_tours.html",
    r"e:\DuLich2\WebDuLich\travel\templates\travel\search.html"
]

replacements = {
    "all_tours.html": [
        ("category_filter==cat.slug", "category_filter == cat.slug"),
        ("location_filter==loc", "location_filter == loc")
    ],
    "search.html": [
        ("search_type=='tour'", "search_type == 'tour'"),
        ("search_type=='destination'", "search_type == 'destination'")
    ]
}

for file_path in files_to_fix:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.basename(file_path)
        new_content = content
        if filename in replacements:
            for old, new in replacements[filename]:
                new_content = new_content.replace(old, new)
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Fixed {filename}")
        else:
            print(f"No changes needed for {filename}")
    else:
        print(f"File not found: {file_path}")

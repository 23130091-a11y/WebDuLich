import os
import shutil

# Xóa database
if os.path.exists('db.sqlite3'):
    os.remove('db.sqlite3')
    print("Đã xóa db.sqlite3")

# Xóa migrations trong travel app (giữ lại __init__.py)
migrations_dir = 'travel/migrations'
for file in os.listdir(migrations_dir):
    if file.startswith('0') and file.endswith('.py'):
        file_path = os.path.join(migrations_dir, file)
        os.remove(file_path)
        print(f"Đã xóa {file_path}")

# Xóa __pycache__
pycache_dir = os.path.join(migrations_dir, '__pycache__')
if os.path.exists(pycache_dir):
    shutil.rmtree(pycache_dir)
    print(f"Đã xóa {pycache_dir}")

print("\nHoàn tất! Bây giờ chạy:")
print("python manage.py makemigrations")
print("python manage.py migrate")

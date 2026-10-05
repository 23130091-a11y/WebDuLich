release: python manage.py migrate
web: gunicorn myproject.wsgi --workers 2 --timeout 120 --bind 0.0.0.0:$PORT

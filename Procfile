web: gunicorn thailand_events.wsgi
worker: python manage.py monitor_events --interval=300
release: python manage.py collectstatic --noinput
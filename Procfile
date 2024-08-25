worker: celery -A witswin worker -B
beat: celery -A witswin beat -S redbeat.RedBeatScheduler --loglevel=info
release: python manage.py migrate
web: daphne -b 0.0.0.0 -p 4444 witswin.asgi:application
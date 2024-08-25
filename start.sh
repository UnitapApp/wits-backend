python manage.py migrate

daphne -b 0.0.0.0 -p 4444 witswin.asgi:application & celery -A witswin worker -B & celery -A witswin beat -S redbeat.RedBeatScheduler --loglevel=info
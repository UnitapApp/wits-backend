python manage.py migrate

daphne -b 0.0.0.0 -p 80 witswin.asgi:application & celery -A witswin worker -B & celery -A witswin beat -S redbeat.RedBeatScheduler --loglevel=info
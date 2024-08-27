python manage.py migrate

daphne -b 0.0.0.0 -p ${PORT:-5000} witswin.asgi:application
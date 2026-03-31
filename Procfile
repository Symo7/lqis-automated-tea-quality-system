web: gunicorn lqis_project.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --preload
worker: python lqis_project/manage.py qcluster
release: python lqis_project/manage.py migrate --noinput

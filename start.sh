#!/usr/bin/env bash
# start.sh
# Run background worker and the web server in the exact same container to avoid paying for two machines.

echo "Starting Django Q Cluster in the background..."
python lqis_project/manage.py qcluster &

echo "Starting Gunicorn Web Server..."
cd lqis_project && gunicorn lqis_project.wsgi:application --bind 0.0.0.0:$PORT

# LF Enforced for Render

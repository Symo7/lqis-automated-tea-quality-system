#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
cd lqis_project
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Run the seed data command during the build phase so we don't need the paid Shell
python manage.py seed_demo_data

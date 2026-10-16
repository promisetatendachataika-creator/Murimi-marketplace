#!/usr/bin/env bash
# What the hosting company runs each time you deploy. On Render: set this as the Build Command.
# If any line fails the deploy stops, so a broken version never replaces a working one.
set -o errexit

pip install -r requirements.txt

# Gather every CSS, JS and image file into staticfiles/ for WhiteNoise to serve.
python manage.py collectstatic --no-input

# Bring the database tables up to date. Safe every time: already-applied ones are skipped.
python manage.py migrate

# The table that holds rate-limit counts, when DJANGO_CACHE_TABLE is set.
# Harmless if it already exists, and does nothing when that setting is absent.
python manage.py createcachetable

# NEVER run seed_demo, seed_market or seed_orders here. They are sample data for a laptop,
# and seed_demo would create a staff account whose password is public in this repository.

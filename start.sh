#!/bin/bash
# Run database migrations
flask db upgrade
gunicorn --worker-class eventlet --workers 1 'main:app'

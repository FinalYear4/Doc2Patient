#!/bin/bash
# Run database migrations
flask db upgrade
gunicorn 'main:app'
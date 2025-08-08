# main.py

import eventlet
# This is the crucial step: it patches the standard libraries.
eventlet.monkey_patch()

# Now, import your app and socketio objects AFTER patching.
from app import app, socketio

# The main entry point for running the application.
if __name__ == '__main__':
    socketio.run(app, debug=True)
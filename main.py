# main.py
import eventlet
# This is the crucial step: it patches standard libraries to be asynchronous.
eventlet.monkey_patch()

# Now, import your app and socketio objects AFTER patching.
from app import app, socketio

# This check is not strictly necessary for gunicorn but is good practice.
if __name__ == '__main__':
    socketio.run(app, debug=True)
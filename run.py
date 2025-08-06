# run.py

from app import app, socketio # import socketio

if __name__ == '__main__':
    socketio.run(app, debug=True) # use socketio.run
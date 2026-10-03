# app/__init__.py

from flask import Flask, session, request  # <-- ADDED 'request' HERE
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel, _
from flask_socketio import SocketIO
import mistune  # This is for our custom markdown filter
import re
from flask_mail import Mail

from app.translate import translate_text

def get_locale():
    # This now works because 'request' is imported
    return session.get('language', request.accept_languages.best_match(app.config['LANGUAGES']))

app = Flask(__name__)
app.config.from_object(Config)
app.config['LANGUAGES'] = ['en', 'fr', 'ak_GH']

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")
mail = Mail(app)
babel = Babel(app, locale_selector=get_locale)

@app.after_request
def add_security_headers(response):
    response.headers.setdefault(
        'Content-Security-Policy',
        "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.socket.io; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
        "connect-src 'self' wss: ws:; frame-src https://www.youtube.com; "
        "frame-ancestors 'self'; base-uri 'self'; form-action 'self'"
    )
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault(
        'Permissions-Policy',
        'camera=(self), microphone=(self), geolocation=()'
    )
    return response

# The line 'Markdown(app)' has been removed because we use a custom filter below.

@app.template_filter()
def trans(text):
    """A filter to translate dynamic content using our service."""
    target_language = get_locale()
    if target_language == 'en' or not text:
        return text
    return translate_text(text, target_language)

@app.template_filter('markdown')
def markdown_filter(text):
    """This is our custom filter that correctly handles markdown."""
    return mistune.html(text)

@app.template_filter('youtube_id')
def youtube_id_from_url(url):
    if not url:
        return None
    regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None

from app import routes, models

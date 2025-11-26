import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """
    Application configuration settings.
    - Loads sensitive data from environment variables for security.
    - Provides sensible defaults for local development.
    """
    # --- CORE CONFIGURATION ---
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-secret-key-for-local-development'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')

    # --- DATABASE CONFIGURATION ---
    # This is the key change for Render deployment.
    # It checks for a 'DATABASE_URL' provided by Render. If it exists, it's used.
    # Otherwise, it defaults to the local SQLite database for development.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')

    # --- EMAIL CONFIGURATION ---
    # These settings will be pulled from the environment variables you set on Render.
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    # This now correctly uses the MAIL_USERNAME as the admin email.
    ADMINS = [os.environ.get('MAIL_USERNAME')]

    # --- HUBTEL SMS CONFIGURATION ---
    # These settings will also be pulled from your Render environment variables.
    HUBTEL_CLIENT_ID = os.environ.get('HUBTEL_CLIENT_ID')
    HUBTEL_CLIENT_SECRET = os.environ.get('HUBTEL_CLIENT_SECRET')
    HUBTEL_SENDER_ID = os.environ.get('HUBTEL_SENDER_ID')

    # --- DEVELOPER ADMIN CONFIG ---
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
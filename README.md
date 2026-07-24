# Doc2Patient

Doc2Patient is a Flask-based teleconsultation and patient engagement platform designed to connect patients with doctors, facilitate follow-up care, and support health education.

## Project Overview

This application provides a complete digital clinic workflow with:

- patient registration and login
- doctor and patient dashboards
- appointment booking and management
- secure consultation room and real-time chat
- patient vitals logging and health monitoring
- health article publishing and a health library
- patient issue reporting and admin review
- two-factor authentication (2FA)
- multilingual support for English, French, and Akan

## Tech Stack

- Python 3
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-Login
- Flask-SocketIO
- Flask-WTF
- SQLite for local development (with support for `DATABASE_URL` for deployment)
- PostgreSQL-compatible deployment setup via environment configuration

## Project Structure

- `app/` – main application package containing routes, models, forms, email/SMS utilities, and templates
- `migrations/` – Alembic migration files
- `uploads/` – uploaded files and patient documents
- `config.py` – application configuration and environment variable loading
- `main.py` – entry point for running the application with Socket.IO support
- `run.py` – alternative application runner
- `seed_articles.py` – helper script to seed sample health articles
- `start.sh` – deployment/start script for Gunicorn

## Features

### For Patients
- create an account and log in securely
- search for doctors and request appointments
- view appointments and follow-up details
- submit and monitor vitals records
- use the consultation room for doctor communication
- access a health library with educational articles
- leave reviews after completed appointments

### For Doctors
- manage appointments and consultation workflows
- create and publish health articles
- review patient vitals and follow-up information
- respond to patient consultations and post-consultation notes

### For Admins
- manage user accounts
- review patient-reported issues
- view doctor activity reports

## Local Setup

1. Clone the project and move into the project directory.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with the required environment variables. Example:

```env
SECRET_KEY=your-secret-key
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=1
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
DATABASE_URL=sqlite:///app.db
```

If `DATABASE_URL` is not set, the app falls back to a local SQLite database.

## Database Setup

Apply migrations before starting the app:

```bash
flask db upgrade
```

## Running the App

For local development:

```bash
python main.py
```

Or run the application directly with:

```bash
python run.py
```

For production-style serving:

```bash
gunicorn 'main:app'
```

## Seeding Sample Articles

To add sample health articles to the database:

```bash
python seed_articles.py
```

## Notes

- The project uses Eventlet for Socket.IO compatibility.
- 2FA support is built in for user accounts.
- The app includes multilingual templates and translation support.
- Static assets such as profile pictures and uploaded documents are stored under the `uploads` and `app/static` directories.



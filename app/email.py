# app/email.py
from flask_mail import Message
from app import app, mail
from flask import render_template
from threading import Thread

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, sender, recipients, text_body, html_body):
    if not app.config.get('MAIL_SERVER') or not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        app.logger.error('Email notification skipped: SMTP configuration is incomplete')
        return False
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(app, msg)).start()
    return True

def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(
        'Doc2Patient - Reset Your Password',
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user.email],
        text_body=render_template('email/reset_password.txt', user=user, token=token),
        html_body=render_template('email/reset_password.html', user=user, token=token)
    )

# --- ADD THIS NEW FUNCTION AT THE END ---
def send_new_appointment_email(doctor, patient, appointment):
    send_email(
        '[Doc2Patient] New Appointment Request',
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=[doctor.email],
        text_body=render_template('email/new_appointment_alert.txt',
                                  doctor=doctor, patient=patient, appointment=appointment),
        html_body=render_template('email/new_appointment_alert.html',
                                  doctor=doctor, patient=patient, appointment=appointment)
    )

def send_appointment_confirmation_email(patient, doctor, appointment, code):
    send_email(
        '[Doc2Patient] Appointment confirmed - verification code',
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=[patient.email],
        text_body=render_template('email/appointment_confirmation.txt', patient=patient, doctor=doctor, appointment=appointment, code=code),
        html_body=render_template('email/appointment_confirmation.html', patient=patient, doctor=doctor, appointment=appointment, code=code)
    )

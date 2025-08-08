# app/email.py
from flask_mail import Message
from app import app, mail
from flask import render_template
from threading import Thread

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    Thread(target=send_async_email, args=(app, msg)).start()

def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(
        'Doc2Patient - Reset Your Password',
        sender=app.config['ADMINS'][0],
        recipients=[user.email],
        text_body=render_template('email/reset_password.txt', user=user, token=token),
        html_body=render_template('email/reset_password.html', user=user, token=token)
    )

# --- ADD THIS NEW FUNCTION AT THE END ---
def send_new_appointment_email(doctor, patient, appointment):
    send_email(
        '[Doc2Patient] New Appointment Request',
        sender=app.config['ADMINS'][0],
        recipients=[doctor.email],
        text_body=render_template('email/new_appointment_alert.txt',
                                  doctor=doctor, patient=patient, appointment=appointment),
        html_body=render_template('email/new_appointment_alert.html',
                                  doctor=doctor, patient=patient, appointment=appointment)
    )
import requests
from app import app
from threading import Thread

def send_async_sms(app, url):
    with app.app_context():
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes
            print(f"SMS sent successfully! Response: {response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending SMS: {e}")

def send_sms(to, message):
    if not all([app.config['HUBTEL_CLIENT_ID'], app.config['HUBTEL_CLIENT_SECRET'], app.config['HUBTEL_SENDER_ID']]):
        print("Hubtel SMS config is missing.")
        return

    base_url = "https://smsc.hubtel.com/v1/messages/send"
    params = {
        "clientsecret": app.config['HUBTEL_CLIENT_SECRET'],
        "clientid": app.config['HUBTEL_CLIENT_ID'],
        "from": app.config['HUBTEL_SENDER_ID'],
        "to": to,
        "content": message
    }
    
    # Build the URL with parameters
    url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    # Send in a background thread to not slow down the application
    Thread(target=send_async_sms, args=(app, url)).start()

# --- ADD THIS NEW FUNCTION ---
def send_new_appointment_sms(doctor, patient, appointment):
    if doctor.phone_number:
        message = (
            f"New Doc2Patient Appointment Request from {patient.username} "
            f"for {appointment.appointment_time.strftime('%b %d @ %H:%M')}. "
            f"Please log in to your dashboard to respond."
        )
        send_sms(to=doctor.phone_number, message=message)
# ---------------------------
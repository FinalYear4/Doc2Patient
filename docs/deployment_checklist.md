# Deployment checklist (Render)

This checklist covers deploying the `video-interface` branch, which adds the WebRTC
hardening, appointment OTP, responsive layout, and the consultation room redesign.

## 1. Service configuration

| Setting | Value |
|---|---|
| Branch | `video-interface` |
| Build command | `pip install -r requirements.txt` (plus `npm ci && npm run build:css` if you rebuild the stylesheet on the server) |
| Start command | `bash start.sh` |
| Python version | 3.13 (the repository tracks 3.13 bytecode) |

`start.sh` already runs the migration and then the Socket.IO server:

```bash
flask db upgrade
gunicorn --worker-class eventlet --workers 1 'main:app'
```

Do not use the plain `gunicorn 'main:app'` form. Standard synchronous workers do not
provide WebSocket support, which is what previously broke the consultation room
signalling while the rest of the site kept working. Keep `--workers 1` because
Flask-SocketIO is not using a shared message queue yet.

## 2. Environment variables

Set these in the Render dashboard (Environment tab). Never commit them.

Required:

- `SECRET_KEY`
- `DATABASE_URL` (Render injects this for a managed Postgres instance; do not set it manually)
- `SESSION_COOKIE_SECURE=1` (the deployed site is HTTPS)
- `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`

Email (doctor appointment alerts and the patient confirmation OTP):

- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`
- `MAIL_DEFAULT_SENDER`

SMS (doctor appointment alerts and the patient confirmation OTP):

- `HUBTEL_CLIENT_ID`, `HUBTEL_CLIENT_SECRET`, `HUBTEL_SENDER_ID`

WebRTC (needed for calls between different networks):

- `WEBRTC_TURN_URL`
- `WEBRTC_TURN_USERNAME`
- `WEBRTC_TURN_CREDENTIAL`

Without TURN, calls only work when both peers can reach each other directly. Symptoms are
a call that connects on the same Wi-Fi but hangs at "Connecting" across mobile data or
different networks.

## 3. Database

The new migration adds the appointment confirmation OTP columns:

```
migrations/versions/7f2c1d4e8a90_add_appointment_confirmation_otp.py
```

`start.sh` applies it via `flask db upgrade`. Confirm the deploy log shows the upgrade
running without error.

## 4. Post-deploy verification

1. **Signalling** — open the consultation room as two users on two different networks and
   confirm the badge reaches "Connected" and the timer starts on both sides.
2. **Media** — confirm each participant sees and hears the other.
3. **TURN** — if the call stays at "Connecting" across networks, the TURN credentials are
   missing or wrong.
4. **Doctor alert** — book an appointment as a patient and confirm the doctor receives the
   email and SMS.
5. **Appointment OTP** — confirm the appointment as the doctor, then check the patient
   receives the six-digit code by SMS and email, and that joining the room requires it.
6. **Security headers** — confirm the response still carries the CSP, X-Frame-Options,
   X-Content-Type-Options, Referrer-Policy, and Permissions-Policy headers.

## 5. Known deployment notes

- The consultation room requires HTTPS for camera and microphone access. Render provides
  this by default; do not test over plain HTTP.
- Two participants must be logged in as different users to exercise the call.
- The free Render instance sleeps when idle, so the first request after a pause is slow.

# app/routes.py
import pyotp
import qrcode
import io
import base64
from flask import session

# --- Core Imports ---
import secrets
import os
from PIL import Image
from werkzeug.utils import secure_filename
from flask import (send_from_directory, render_template, flash, redirect, 
                   url_for, request, session)
from flask_login import current_user, login_user, logout_user, login_required
from flask_socketio import send, emit, join_room, leave_room
from urllib.parse import urlparse

# --- Application-Specific Imports ---
from app import app, db, socketio
from app.models import (User, Appointment, ChatMessage, HealthArticle, 
                        ArticleRecommendation, VitalsRecord, Review, AdminUser, UserReport)
from app.forms import (LoginForm, RegistrationForm, AppointmentForm, UpdateProfileForm, 
                       VitalsForm, RequestPasswordResetForm, ResetPasswordForm, ArticleForm, ReviewForm, TwoFactorForm, ReportIssueForm, AdminResponseForm, DoctorReportForm)
from app.email import send_password_reset_email
from app.sms import send_sms
from sqlalchemy import or_
from sqlalchemy import func
from functools import wraps # <-- IMPORT FOR DECORATOR
from datetime import datetime, time # Add this import at the top

from app.email import send_new_appointment_email
from app.sms import send_new_appointment_sms

# =============================================================================
# TOP-LEVEL & LANGUAGE ROUTES
# =============================================================================
# --- THIS IS THE MISSING DECORATOR DEFINITION ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
# -----------------------------------------------


@app.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # This query now correctly limits the results to a maximum of 3
    testimonials = Review.query.filter_by(is_featured=True).order_by(Review.timestamp.desc()).limit(3).all()
            
    return render_template('landing.html', testimonials=testimonials)

@app.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html', title='How It Works')

@app.route('/faq')
def faq():
    return render_template('faq.html', title='Frequently Asked Questions')

@app.route('/contact')
def contact():
    return render_template('contact.html', title='Contact Us')

@app.route('/set_language/<language>')
def set_language(language):
    # Store the selected language in the user's session
    session['language'] = language
    # Redirect the user back to the page they were on
    return redirect(request.referrer)

@app.route('/index')
@login_required
def index():
    # This route is the internal "home" that directs to the correct dashboard
    if hasattr(current_user, 'is_admin') and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    elif current_user.role == 'patient':
        return redirect(url_for('patient_dashboard'))
    
    # A fallback just in case
    return redirect(url_for('landing'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    # This line now standardizes the file extension to lowercase
    f_ext = os.path.splitext(form_picture.filename)[1].lower()
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (150, 150)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

# =============================================================================
# DASHBOARD ROUTES
# =============================================================================

@app.route('/doctor_dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    appointments = current_user.appointments_as_doctor.order_by(Appointment.appointment_time.asc()).all()
    
    # This query now correctly limits the results to a maximum of 5
    reviews = current_user.reviews_received.order_by(Review.timestamp.desc()).limit(5).all()
    
    return render_template(
        'doctor_dashboard.html', 
        title='Doctor Dashboard', 
        appointments=appointments,
        reviews=reviews
    )

@app.route('/create_article', methods=['GET', 'POST'])
@login_required
def create_article():
    # Security check: Only doctors can create articles
    if current_user.role != 'doctor':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    form = ArticleForm()
    if form.validate_on_submit():
        article = HealthArticle(
            title=form.title.data,
            category=form.category.data,
            content=form.content.data,
            author=current_user  # This links the article to the logged-in doctor
        )
        db.session.add(article)
        db.session.commit()
        flash('Your article has been published successfully!', 'success')
        # Redirect to the new article so the doctor can see it
        return redirect(url_for('view_article', article_id=article.id))
        
    return render_template('create_article.html', title='Create New Article', form=form)

@app.route('/patient_dashboard', methods=['GET', 'POST'])
@login_required
def patient_dashboard():
    if current_user.role != 'patient':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    form = AppointmentForm()
    
    # --- SEARCH AND FILTER LOGIC ---
    search_query = request.args.get('search', '').strip()
    doctors_query = User.query.filter_by(role='doctor')
    if search_query:
        search_term = f"%{search_query}%"
        doctors_query = doctors_query.filter(
            or_(User.username.ilike(search_term), User.speciality.ilike(search_term))
        )
    doctors = doctors_query.order_by(User.username).all()
    
    # Set the choices for the form field for both GET and POST requests
    form.doctor_id.choices = [(d.id, d.username) for d in doctors]

    # --- HANDLE FORM SUBMISSION ---
    if form.validate_on_submit():
        # Create and save the new appointment
        appointment = Appointment(
            doctor_id=form.doctor_id.data,
            patient_id=current_user.id,
            appointment_time=form.appointment_time.data,
            notes=form.notes.data,
            status='pending'
        )
        db.session.add(appointment)
        db.session.commit()

        # --- NEW DOCTOR NOTIFICATION LOGIC ---
        doctor = User.query.get(appointment.doctor_id)
        if doctor:
            # Send Email Notification to the doctor
            send_new_appointment_email(doctor=doctor, patient=current_user, appointment=appointment)
            
            # Send SMS Notification to the doctor (if they have a phone number)
            send_new_appointment_sms(doctor=doctor, patient=current_user, appointment=appointment)
        # ------------------------------------
        
        flash('Your appointment request has been sent! The doctor has been notified.', 'success')
        return redirect(url_for('patient_dashboard'))

    # --- FETCH DATA FOR DISPLAY ---
    # Get active appointments (pending, confirmed, or declined)
    active_appointments = Appointment.query.filter(
        Appointment.patient_id == current_user.id,
        Appointment.status.in_(['pending', 'confirmed', 'declined'])
    ).order_by(Appointment.appointment_time.asc()).all()
    
    # Get completed appointments for the follow-up section
    completed_appointments = Appointment.query.filter_by(
        patient_id=current_user.id, 
        status='completed'
    ).order_by(Appointment.appointment_time.desc()).all()

    return render_template(
        'patient_dashboard.html', 
        title='Patient Dashboard', 
        form=form, 
        appointments=active_appointments,
        completed_appointments=completed_appointments,
        doctors=doctors,
        search_query=search_query
    )

@app.route('/view_patient_vitals/<int:patient_id>')
@login_required
def view_patient_vitals(patient_id):
    # Security check: Only doctors can access this page
    if current_user.role != 'doctor':
        flash('This page is for doctors only.', 'warning')
        return redirect(url_for('index'))
    
    # Find the patient in the database
    patient = User.query.get_or_404(patient_id)
    
    # Ensure the user is actually a patient
    if patient.role != 'patient':
        flash('Invalid patient ID.', 'danger')
        return redirect(url_for('doctor_dashboard'))
    
    # Get the patient's vitals records, ordered by most recent
    records = patient.vitals_records.order_by(VitalsRecord.timestamp.desc()).all()
    
    return render_template('view_patient_vitals.html', 
                           title=f"{patient.username}'s Vitals",
                           patient=patient, 
                           records=records)

# Add this new route for users
@app.route('/report-issue', methods=['GET', 'POST'])
@login_required
def report_issue():
    form = ReportIssueForm()
    if form.validate_on_submit():
        report = UserReport(
            subject=form.subject.data,
            description=form.description.data,
            author=current_user
        )
        db.session.add(report)
        db.session.commit()
        flash('Your issue has been reported successfully. We will get back to you shortly.', 'success')
        return redirect(url_for('my_reports'))
    return render_template('report_issue.html', title='Report an Issue', form=form)

@app.route('/my-reports')
@login_required
def my_reports():
    reports = current_user.reports.order_by(UserReport.timestamp.desc()).all()
    return render_template('my_reports.html', title='My Reported Issues', reports=reports)

# --- ADMIN ROUTES ---
@app.route('/admin/dashboard')
@login_required
@admin_required # This will now work correctly
def admin_dashboard():
    users = User.query.filter(User.is_admin == False).order_by(User.id).all()
    reports = UserReport.query.order_by(UserReport.timestamp.desc()).all()
    return render_template('admin/dashboard.html', title='Admin Dashboard', users=users, reports=reports)

@app.route('/admin/user/<int:user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required # This will now work correctly
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash(f"User {user.username}'s account has been {'activated' if user.is_active else 'deactivated'}.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required # This will now work correctly
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Admin accounts cannot be deleted.', 'danger')
        return redirect(url_for('admin_dashboard'))
    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.username}'s account has been permanently deleted.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/report/<int:report_id>', methods=['GET', 'POST'])
@login_required
@admin_required # This will now work correctly
def view_report(report_id):
    report = UserReport.query.get_or_404(report_id)
    form = AdminResponseForm()
    if form.validate_on_submit():
        report.admin_response = form.response.data
        report.status = form.status.data
        db.session.commit()
        flash('Your response has been sent to the user.', 'success')
        return redirect(url_for('admin_dashboard'))
    elif request.method == 'GET':
        form.response.data = report.admin_response
        form.status.data = report.status
    return render_template('admin/view_report.html', title='View Report', report=report, form=form)

# In app/routes.py

@app.route('/admin/reports', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_reports():
    form = DoctorReportForm() # We still pass the form to the template
    
    # --- STEP 1: Get all doctors ---
    doctors = User.query.filter_by(role='doctor').order_by(User.username).all()

    # --- STEP 2: Explicitly build the report data with guaranteed integers ---
    # This simple loop is easy to verify and cannot produce the wrong data type.
    report_data = []
    for doctor in doctors:
        # For each doctor, get the count of their appointments. count() returns an integer.
        consultation_count = doctor.appointments_as_doctor.count()
        report_data.append({'doctor': doctor, 'count': consultation_count})

    # --- STEP 3: Explicitly build the chart data from the clean report data ---
    chart_data = None
    if report_data:
        # Sort for a visually appealing chart (highest bar first)
        sorted_report_data = sorted(report_data, key=lambda x: x['count'], reverse=True)
        
        # Create simple lists of strings and integers, which are guaranteed to be JSON serializable.
        chart_labels = [f"Dr. {data['doctor'].username}" for data in sorted_report_data]
        chart_values = [data['count'] for data in sorted_report_data]
        
        chart_data = {
            'labels': chart_labels,
            'values': chart_values
        }

    return render_template('admin/reports.html', title='Doctor Reports', 
                           form=form, report_data=report_data, chart_data=chart_data)

# =============================================================================
# APPOINTMENT & FOLLOW-UP ROUTES
# =============================================================================

@app.route('/confirm_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def confirm_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if current_user.role != 'doctor' or current_user.id != appointment.doctor_id:
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('index'))
    appointment.status = 'confirmed'
    db.session.commit()
    patient = User.query.get(appointment.patient_id)
    if patient and patient.phone_number:
        message = f"Hi {patient.username}, your appointment with Dr. {current_user.username} for {appointment.appointment_time.strftime('%b %d at %H:%M')} has been confirmed."
        send_sms(to=patient.phone_number, message=message)
    flash('Appointment confirmed.', 'success')
    return redirect(url_for('doctor_dashboard'))

@app.route('/decline_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def decline_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if current_user.role != 'doctor' or current_user.id != appointment.doctor_id:
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('index'))
    appointment.status = 'declined'
    db.session.commit()
    flash('Appointment declined.', 'warning')
    return redirect(url_for('doctor_dashboard'))

@app.route('/post_consultation/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def post_consultation(appointment_id):
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
    appointment = Appointment.query.get_or_404(appointment_id)
    if current_user.id != appointment.doctor_id:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        appointment.custom_follow_up_notes = request.form.get('custom_notes')
        appointment.youtube_video_url = request.form.get('youtube_url')
        if 'document' in request.files:
            file = request.files['document']
            if file.filename != '':
                filename = secure_filename(file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                appointment.uploaded_document_filename = filename
        ArticleRecommendation.query.filter_by(appointment_id=appointment.id).delete()
        selected_ids = request.form.getlist('articles')
        for article_id in selected_ids:
            rec = ArticleRecommendation(appointment_id=appointment.id, article_id=int(article_id))
            db.session.add(rec)
        appointment.status = 'completed'
        db.session.commit()
        flash('Follow-up recommendations saved and appointment marked as complete.', 'success')
        return redirect(url_for('doctor_dashboard'))
    
    articles = HealthArticle.query.all()
    return render_template('post_consultation.html', title='Follow-Up', appointment=appointment, articles=articles)

@app.route('/download_document/<int:appointment_id>')
@login_required
def download_document(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if current_user.id not in [appointment.patient_id, appointment.doctor_id]:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))
    if not appointment.uploaded_document_filename:
        flash('No document found for this appointment.', 'warning')
        return redirect(url_for('patient_dashboard'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], appointment.uploaded_document_filename, as_attachment=True)

@app.route('/doctors')
@login_required # Make sure user is logged in to see doctors
def doctors():
    doctors = User.query.filter_by(role='doctor').order_by(User.username).all()
    return render_template('doctors.html', title='Meet Our Doctors', doctors=doctors)

# =============================================================================
# AUTHENTICATION & PROFILE ROUTES
# =============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # --- Admin Check (Unchanged) ---
        submitted_username = form.username.data
        submitted_password = form.password.data
        if (submitted_username == app.config['ADMIN_USERNAME'] or submitted_username == app.config['ADMIN_EMAIL']) and submitted_password == app.config['ADMIN_PASSWORD']:
            admin_user = AdminUser()
            login_user(admin_user, remember=form.remember_me.data)
            return redirect(url_for('admin_dashboard'))

        # --- Normal User Login with NEW Active Check ---
        user = User.query.filter_by(username=submitted_username).first()
        if user is None or not user.check_password(submitted_password):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))

        # --- THIS IS THE NEW CHECK ---
        if not user.is_active:
            if user.role == 'doctor':
                flash('Your account has not been approved by an administrator yet. Please check back later.', 'warning')
            else:
                flash('Your account has been deactivated. Please contact support.', 'danger')
            return redirect(url_for('login'))
        # ---------------------------

        if user.otp_enabled:
            session['user_id_for_2fa'] = user.id
            session['next_url_for_2fa'] = request.args.get('next')
            return redirect(url_for('login_2fa'))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
        
    return render_template('login.html', title='Sign In', form=form)

@app.route('/login/2fa', methods=['GET', 'POST'])
def login_2fa():
    if 'user_id_for_2fa' not in session:
        return redirect(url_for('login'))
    
    form = TwoFactorForm()
    if form.validate_on_submit():
        user_id = session['user_id_for_2fa']
        user = User.query.get(user_id)
        if user and pyotp.TOTP(user.otp_secret).verify(form.code.data):
            # Clean up session
            session.pop('user_id_for_2fa')
            next_url = session.pop('next_url_for_2fa', None)
            
            login_user(user, remember=True) # Log the user in
            
            if not next_url or urlparse(next_url).netloc != '':
                next_url = url_for('index')
            return redirect(next_url)
        else:
            flash('Invalid 2FA code.', 'danger')
    
    return render_template('login_2fa.html', title='Verify 2FA', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('landing'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data, 
            email=form.email.data, 
            role=form.role.data
        )
        user.set_password(form.password.data)

        # --- NEW DOCTOR APPROVAL LOGIC ---
        if user.role == 'doctor':
            user.is_active = False  # Deactivate doctor accounts by default
            db.session.add(user)
            db.session.commit()
            flash('Your registration is complete. Your doctor account is now pending administrative approval. You will be notified once it is activated.', 'info')
            return redirect(url_for('login'))
        # ---------------------------------
        
        # Patients are activated immediately
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html', title='Register', form=form)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # --- NEW: PREVENT ADMINS FROM EDITING A PROFILE ---
    if current_user.is_admin:
        flash('Admin profile is not editable.', 'info')
        return redirect(url_for('admin_dashboard'))
    # ----------------------------------------------------
    form = UpdateProfileForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        
        current_user.username = form.username.data
        current_user.email = form.email.data
        
        # Save role-specific fields
        if current_user.role == 'doctor':
            current_user.speciality = form.speciality.data
            current_user.experience_years = form.experience_years.data
            current_user.bio = form.bio.data
        elif current_user.role == 'patient':
            current_user.phone_number = form.phone_number.data
            current_user.region = form.region.data
            
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('profile'))
        
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        
        # Pre-populate role-specific fields
        if current_user.role == 'doctor':
            form.speciality.data = current_user.speciality
            form.experience_years.data = current_user.experience_years
            form.bio.data = current_user.bio
        elif current_user.role == 'patient':
            form.phone_number.data = current_user.phone_number
            form.region.data = current_user.region
    
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('profile.html', title='Edit Profile',
                           form=form, image_file=image_file)

@app.route('/2fa/enable', methods=['GET', 'POST'])
@login_required
def enable_2fa():
    # Generate a new secret key for the user
    if 'otp_secret' not in session:
        session['otp_secret'] = pyotp.random_base32()
    
    # Create the provisioning URI for the authenticator app
    totp_uri = pyotp.totp.TOTP(session['otp_secret']).provisioning_uri(
        name=current_user.email,
        issuer_name='Doc2Patient'
    )
    
    # Generate the QR code
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert image to a data URI to display in the template
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    qr_code_data_uri = f"data:image/png;base64,{img_str}"

    # If the user submits the verification code
    if request.method == 'POST':
        code = request.form.get('code')
        totp = pyotp.TOTP(session['otp_secret'])
        if totp.verify(code):
            # Code is valid, enable 2FA for the user
            current_user.otp_secret = session['otp_secret']
            current_user.otp_enabled = True
            db.session.commit()
            session.pop('otp_secret') # Clean up session
            flash('2FA has been successfully enabled!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Invalid verification code. Please try again.', 'danger')

    return render_template('enable_2fa.html', title='Enable 2FA', qr_code=qr_code_data_uri, secret=session['otp_secret'])

@app.route('/2fa/disable') # Changed to a GET route for simplicity
@login_required
def disable_2fa():
    current_user.otp_enabled = False
    current_user.otp_secret = None
    db.session.commit()
    flash('2FA has been disabled.', 'success')
    return redirect(url_for('profile'))

@app.route('/leave_review/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def leave_review(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    # Security Checks:
    # 1. Ensure current user is the patient for this appointment
    if current_user.id != appointment.patient_id:
        flash('You are not authorized to review this appointment.', 'danger')
        return redirect(url_for('patient_dashboard'))
    # 2. Ensure the appointment is completed
    if appointment.status != 'completed':
        flash('You can only leave a review for completed appointments.', 'warning')
        return redirect(url_for('patient_dashboard'))
    # 3. Ensure a review has not already been submitted
    if appointment.review:
        flash('You have already submitted a review for this appointment.', 'info')
        return redirect(url_for('patient_dashboard'))
        
    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            rating=form.rating.data,
            testimonial=form.testimonial.data,
            is_featured=form.is_featured.data,
            patient_id=current_user.id,
            doctor_id=appointment.doctor_id,
            appointment_id=appointment.id
        )
        db.session.add(review)
        db.session.commit()
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('patient_dashboard'))
        
    return render_template('leave_review.html', title='Leave a Review', form=form, appointment=appointment)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password', 'info')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html', title='Reset Password', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)

# =============================================================================
# PATIENT DATA ROUTES
# =============================================================================

@app.route('/health_library')
@login_required
def health_library():
    articles = HealthArticle.query.order_by(HealthArticle.title).all()
    return render_template('health_library.html', title='Health Library', articles=articles)

@app.route('/health_library/article/<int:article_id>')
@login_required
def view_article(article_id):
    article = HealthArticle.query.get_or_404(article_id)
    return render_template('view_article.html', title=article.title, article=article)

@app.route('/my_vitals', methods=['GET', 'POST'])
@login_required
def my_vitals():
    if current_user.role != 'patient':
        flash('This page is for patients only.', 'warning')
        return redirect(url_for('index'))
    
    form = VitalsForm()
    if form.validate_on_submit():
        vitals_record = VitalsRecord(
            patient_id=current_user.id,
            height=form.height.data,
            weight=form.weight.data,
            temperature=form.temperature.data,
            blood_pressure_systolic=form.blood_pressure_systolic.data,
            blood_pressure_diastolic=form.blood_pressure_diastolic.data,
            heart_rate=form.heart_rate.data,
            oxygen_saturation=form.oxygen_saturation.data,
            blood_sugar=form.blood_sugar.data
        )
        db.session.add(vitals_record)
        db.session.commit()
        flash('Your vitals have been logged successfully!', 'success')
        return redirect(url_for('my_vitals'))

    # --- NEW HEALTH ANALYSIS LOGIC ---
    latest_record = current_user.vitals_records.order_by(VitalsRecord.timestamp.desc()).first()
    vitals_history = current_user.vitals_records.order_by(VitalsRecord.timestamp.desc()).limit(10).all()
    analysis = {}

    if latest_record:
        # 1. BMI Calculation and Advice
        if latest_record.height and latest_record.weight:
            try:
                height_m = float(latest_record.height) / 100
                bmi = float(latest_record.weight) / (height_m * height_m)
                analysis['bmi'] = {'value': round(bmi, 1)}
                if bmi < 18.5:
                    analysis['bmi']['category'] = 'Underweight'
                    analysis['bmi']['color'] = 'blue'
                    analysis['bmi']['advice'] = 'Your BMI is in the underweight range. Consider consulting with a nutritionist to ensure you are getting enough nutrients for your body to thrive. A balanced diet with adequate protein and healthy fats is important.'
                elif 18.5 <= bmi < 25:
                    analysis['bmi']['category'] = 'Normal'
                    analysis['bmi']['color'] = 'green'
                    analysis['bmi']['advice'] = 'Excellent! Your BMI is in the normal range. Continue to maintain your healthy lifestyle with a balanced diet and regular physical activity to support your long-term well-being.'
                elif 25 <= bmi < 30:
                    analysis['bmi']['category'] = 'Overweight'
                    analysis['bmi']['color'] = 'yellow'
                    analysis['bmi']['advice'] = 'Your BMI is in the overweight range. Focusing on portion control, incorporating more whole foods, and increasing physical activity can make a significant difference. Small, consistent changes are key.'
                else:
                    analysis['bmi']['category'] = 'Obese'
                    analysis['bmi']['color'] = 'red'
                    analysis['bmi']['advice'] = 'Your BMI is in the obese range, which can increase the risk for several health conditions. We highly recommend discussing a personalized weight management plan with a doctor or nutritionist.'
            except (ValueError, TypeError, ZeroDivisionError):
                pass # Fail silently if data is invalid

        # 2. Vitals Alert System
        analysis['vitals'] = []
        if latest_record.blood_pressure_systolic and latest_record.blood_pressure_diastolic:
            systolic = latest_record.blood_pressure_systolic
            diastolic = latest_record.blood_pressure_diastolic
            status, color = ('High', 'red') if systolic > 130 or diastolic > 80 else (('Low', 'yellow') if systolic < 90 or diastolic < 60 else ('Normal', 'green'))
            analysis['vitals'].append({'name': 'Blood Pressure', 'value': f'{systolic}/{diastolic}', 'status': status, 'color': color})
        
        if latest_record.heart_rate:
            hr = latest_record.heart_rate
            status, color = ('High', 'yellow') if hr > 100 else (('Low', 'yellow') if hr < 60 else ('Normal', 'green'))
            analysis['vitals'].append({'name': 'Heart Rate', 'value': f'{hr} BPM', 'status': status, 'color': color})

        if latest_record.oxygen_saturation:
            spo2 = latest_record.oxygen_saturation
            status, color = ('Low', 'yellow') if spo2 < 95 else ('Normal', 'green')
            analysis['vitals'].append({'name': 'Oxygen Saturation', 'value': f'{spo2}%', 'status': status, 'color': color})

        if latest_record.temperature:
            temp = latest_record.temperature
            status, color = ('High', 'red') if temp > 37.5 else (('Low', 'yellow') if temp < 36.1 else ('Normal', 'green'))
            analysis['vitals'].append({'name': 'Temperature', 'value': f'{temp}°C', 'status': status, 'color': color})
            
    return render_template('my_vitals.html', title='My Vitals', form=form, 
                           vitals_history=vitals_history, analysis=analysis)

# =============================================================================
# LIVE CONSULTATION ROUTE & SOCKET.IO HANDLERS
# =============================================================================

@app.route('/consultation/<int:appointment_id>')
@login_required
def consultation(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if current_user.id not in [appointment.patient_id, appointment.doctor_id]:
        flash('You are not authorized to view this consultation.', 'danger')
        return redirect(url_for('index'))
    if appointment.status != 'confirmed':
        flash('This appointment has not been confirmed yet.', 'warning')
        return redirect(url_for('index'))
    previous_messages = appointment.chat_messages.order_by(ChatMessage.timestamp.asc()).all()
    return render_template('consultation_room.html', appointment=appointment, previous_messages=previous_messages)

@socketio.on('join')
def on_join(data):
    username = current_user.username
    room = data['room']
    join_room(room)
    if current_user.role == 'doctor':
        appointment = Appointment.query.get(int(room))
        if appointment:
            patient = User.query.get(appointment.patient_id)
            if patient and patient.phone_number:
                message = f"Dr. {current_user.username} has just joined your consultation room. You can join now."
                send_sms(to=patient.phone_number, message=message)
    send({'username': 'System', 'msg': f'{username} has entered the room.'}, to=room)

@socketio.on('i_am_ready')
def on_ready(data):
    room = data['room']
    emit('peer_is_ready', to=room, include_self=False)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    appointment_id = int(room)
    new_message = ChatMessage(appointment_id=appointment_id, user_id=current_user.id, username=data['username'], message=data['msg'])
    db.session.add(new_message)
    db.session.commit()
    send(data, to=room)

@socketio.on('fetch_latest_vitals')
def handle_fetch_vitals(data):
    room = data['room']
    if current_user.role == 'patient':
        latest_vitals = VitalsRecord.query.filter_by(patient_id=current_user.id).order_by(VitalsRecord.timestamp.desc()).first()
        vitals_data = {}
        if latest_vitals:
            vitals_data = {
                'temperature': latest_vitals.temperature or '--', 'pulse': latest_vitals.heart_rate or '--',
                'bp': f"{latest_vitals.blood_pressure_systolic or '--'}/{latest_vitals.blood_pressure_diastolic or '--'}",
                'respiratory_rate': latest_vitals.respiratory_rate or '--', 'oxygen_saturation': latest_vitals.oxygen_saturation or '--',
                'blood_sugar': latest_vitals.blood_sugar or '--', 'height': latest_vitals.height or '--', 'weight': latest_vitals.weight or '--'
            }
        else:
            vitals_data = {
                'temperature': 'No Data', 'pulse': 'No Data', 'bp': 'No Data', 'respiratory_rate': 'No Data',
                'oxygen_saturation': 'No Data', 'blood_sugar': 'No Data', 'height': 'No Data', 'weight': 'No Data'
            }
        emit('vitals_update', vitals_data, to=room)

@socketio.on('hang_up')
def on_hang_up(data):
    room = data['room']
    emit('peer_left', to=room, include_self=False)

@socketio.on('offer')
def handle_offer(data):
    room = data['room']
    emit('offer', data['offer'], to=room, include_self=False)

@socketio.on('answer')
def handle_answer(data):
    room = data['room']
    emit('answer', data['answer'], to=room, include_self=False)

@socketio.on('candidate')
def handle_candidate(data):
    room = data['room']
    emit('candidate', data['candidate'], to=room, include_self=False)
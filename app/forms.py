# app/forms.py

from flask_wtf.file import FileField, FileAllowed
from wtforms import TextAreaField
from app.models import User
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField, TextAreaField, RadioField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from wtforms import DecimalField, IntegerField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Optional, NumberRange
from app.models import User, Appointment
from wtforms import TextAreaField
from wtforms.fields import DateTimeLocalField
from flask_login import current_user
from datetime import timedelta

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class TwoFactorForm(FlaskForm):
    code = StringField('6-Digit Code', validators=[DataRequired()])
    submit = SubmitField('Verify')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number (e.g., 233... without +)', validators=[DataRequired()]) # New field
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Register as', choices=[('patient', 'Patient'), ('doctor', 'Doctor')], validators=[DataRequired()])
    submit = SubmitField('Register')

    # ... (validation methods) ...
    def validate_phone_number(self, phone_number):
        user = User.query.filter_by(phone_number=phone_number.data).first()
        if user is not None:
            raise ValidationError('This phone number is already registered.')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

# Replace the entire AppointmentForm class
class AppointmentForm(FlaskForm):
    doctor_id = RadioField('Select a Doctor', coerce=int, validators=[DataRequired()])
    appointment_time = DateTimeLocalField('Preferred Date and Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    notes = TextAreaField('Reason for consultation', validators=[DataRequired()])
    submit = SubmitField('Request Appointment')

    def validate(self, extra_validators=None):
        initial_validation = super(AppointmentForm, self).validate(extra_validators)
        if not initial_validation:
            return False

        doctor_id = self.doctor_id.data
        appointment_time = self.appointment_time.data

        if doctor_id and appointment_time:
            # Check a 30-minute window before and after the requested time
            time_window_start = appointment_time - timedelta(minutes=29)
            time_window_end = appointment_time + timedelta(minutes=29)

            existing_appointment = Appointment.query.filter(
                Appointment.doctor_id == doctor_id,
                Appointment.status.in_(['confirmed', 'pending']),
                Appointment.appointment_time.between(time_window_start, time_window_end)
            ).first()
            
            if existing_appointment:
                self.appointment_time.errors.append('Doctor is unavailable within 30 mins of this slot. Please choose another time.')
                return False
        
        return True

class UpdateProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    
    # --- ADD THESE PATIENT-SPECIFIC FIELDS ---
    phone_number = StringField('Phone Number (e.g., 024xxxxxxx)', validators=[Optional()])
    region = SelectField('Region of Residence', choices=[
        ('', '--- Select Your Region ---'),
        ('Ahafo', 'Ahafo'), ('Ashanti', 'Ashanti'), ('Bono', 'Bono'),
        ('Bono East', 'Bono East'), ('Central', 'Central'), ('Eastern', 'Eastern'),
        ('Greater Accra', 'Greater Accra'), ('North East', 'North East'),
        ('Northern', 'Northern'), ('Oti', 'Oti'), ('Savannah', 'Savannah'),
        ('Upper East', 'Upper East'), ('Upper West', 'Upper West'),
        ('Volta', 'Volta'), ('Western', 'Western'), ('Western North', 'Western North')
    ], validators=[Optional()])
    # --------------------------------------

    # Doctor-specific fields
    speciality = StringField('Your Speciality (e.g., General Practice, Cardiology)', validators=[Optional()])
    experience_years = IntegerField('Years of Experience', validators=[Optional(), NumberRange(min=0, max=60)])
    bio = TextAreaField('A little note about yourself (for patients)', validators=[Optional()])
    
    # This field is now for everyone
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'jpeg', 'png'])])
    
    submit = SubmitField('Update')

    # ... (validation methods are unchanged, but we should add one for phone number) ...
    def validate_phone_number(self, phone_number):
        if phone_number.data and phone_number.data != current_user.phone_number:
            user = User.query.filter_by(phone_number=phone_number.data).first()
            if user:
                raise ValidationError('That phone number is already registered. Please use a different one.')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=self.username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=self.email.data).first()
            if user:
                raise ValidationError('That email is already registered. Please choose a different one.')

class VitalsForm(FlaskForm):
    # New fields for BMI calculation
    height = DecimalField('Height (cm)', validators=[Optional(), NumberRange(min=100, max=250)])
    weight = DecimalField('Weight (kg)', validators=[Optional(), NumberRange(min=30, max=300)])
    
    # Existing fields
    temperature = DecimalField('Temperature (°C)', validators=[Optional(), NumberRange(min=35, max=43)])
    blood_pressure_systolic = IntegerField('Blood Pressure (Systolic)', validators=[Optional(), NumberRange(min=70, max=250)])
    blood_pressure_diastolic = IntegerField('Blood Pressure (Diastolic)', validators=[Optional(), NumberRange(min=40, max=150)])
    heart_rate = IntegerField('Heart Rate (BPM)', validators=[Optional(), NumberRange(min=40, max=200)])
    oxygen_saturation = IntegerField('Oxygen Saturation (SpO2 %)', validators=[Optional(), NumberRange(min=80, max=100)])
    blood_sugar = DecimalField('Blood Sugar (mg/dL)', validators=[Optional(), NumberRange(min=50, max=500)])
    submit = SubmitField('Log My Vitals')

# Add these two new forms at the end of the file
class RequestPasswordResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

# --- ADD THIS NEW FORM CLASS AT THE END OF THE FILE ---
class ArticleForm(FlaskForm):
    title = StringField('Article Title', validators=[DataRequired()])
    category = StringField('Category (e.g., Diabetes, Nutrition, Mental Health)', validators=[DataRequired()])
    content = TextAreaField('Content (Markdown is supported)', validators=[DataRequired()])
    submit = SubmitField('Publish Article')
# -----------------------------------------------------

# --- ADD THIS NEW FORM CLASS AT THE END OF THE FILE ---
class ReviewForm(FlaskForm):
    rating = RadioField('Your Rating (1=Poor, 5=Excellent)', choices=[
        ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')
    ], validators=[DataRequired()], coerce=int)
    testimonial = TextAreaField('Your Testimonial (Optional)', validators=[Optional()])
    is_featured = BooleanField('Allow this testimonial to be featured on the homepage?')
    submit = SubmitField('Submit Review')
# -----------------------------------------------------

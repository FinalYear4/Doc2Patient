# app/models.py

from sqlalchemy import UniqueConstraint # <-- Add this import at the top
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from time import time
from flask import current_app # Import current_app

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    
    # --- THIS LINE IS MODIFIED (unique=True is removed) ---
    phone_number = db.Column(db.String(20), nullable=True)
    region = db.Column(db.String(50), nullable=True)
    
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), index=True, default='patient')
    speciality = db.Column(db.String(100), nullable=True)
    experience_years = db.Column(db.Integer, nullable=True)
    image_file = db.Column(db.String(20), nullable=False, server_default='default.jpg', default='default.jpg')
    bio = db.Column(db.Text, nullable=True)

    appointments_as_doctor = db.relationship('Appointment', foreign_keys='Appointment.doctor_id', backref='doctor', lazy='dynamic')
    appointments_as_patient = db.relationship('Appointment', foreign_keys='Appointment.patient_id', backref='patient', lazy='dynamic')
    vitals_records = db.relationship('VitalsRecord', backref='user', lazy='dynamic', cascade="all, delete-orphan")

    # --- NEW RELATIONSHIPS FOR REVIEWS ---
    reviews_written = db.relationship('Review', foreign_keys='Review.patient_id', backref='author', lazy='dynamic')
    reviews_received = db.relationship('Review', foreign_keys='Review.doctor_id', backref='doctor_reviewed', lazy='dynamic')
    # ------------------------------------

    # --- NEW PROPERTY TO CALCULATE AVERAGE RATING ---
    def average_rating(self):
        if self.role == 'doctor':
            reviews = self.reviews_received.all()
            if not reviews:
                return 0
            return sum(r.rating for r in reviews) / len(reviews)
        return 0
    # ----------------------------------------------
    # --- THIS BLOCK IS ADDED TO EXPLICITLY NAME THE CONSTRAINT ---
    __table_args__ = (
        UniqueConstraint('phone_number', name='uq_user_phone_number'),
    )
    # ----------------------------------------------------------------

    def get_reset_password_token(self, expires_in=600):
        # ... (rest of the User model is unchanged) ...
        import jwt
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        # ... (rest of the User model is unchanged) ...
        import jwt
        from app.models import User
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return None
        return User.query.get(id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    def __repr__(self):
        return f'<User {self.username}>'

# --- Appointment, ChatMessage, HealthArticle, ArticleRecommendation models remain the same ---
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    appointment_time = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    notes = db.Column(db.Text)
    custom_follow_up_notes = db.Column(db.Text, nullable=True)
    uploaded_document_filename = db.Column(db.String(200), nullable=True)
    youtube_video_url = db.Column(db.String(200), nullable=True)
    chat_messages = db.relationship('ChatMessage', backref='appointment', lazy='dynamic', cascade="all, delete-orphan")
    recommended_articles = db.relationship('ArticleRecommendation', backref='appointment', lazy='dynamic', cascade="all, delete-orphan")
    # --- NEW RELATIONSHIP FOR REVIEWS (One-to-one) ---
    review = db.relationship('Review', backref='appointment', uselist=False, cascade="all, delete-orphan")
    # ------------------------------------------------
    def __repr__(self):
        return f'<Appointment {self.id}>'
# --- NEW MODEL FOR REVIEWS ---
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False) # e.g., 1 to 5 stars
    testimonial = db.Column(db.Text, nullable=True)
    is_featured = db.Column(db.Boolean, default=False) # For showing on the landing page
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    
    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False, unique=True)

    def __repr__(self):
        return f'<Review {self.id} - {self.rating} stars>'
# -----------------------------


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    username = db.Column(db.String(64), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    def __repr__(self):
        return f'<ChatMessage {self.message}>'

class HealthArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User')
    def __repr__(self):
        return f'<HealthArticle {self.title}>'

class ArticleRecommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('health_article.id'), nullable=False)
    article = db.relationship('HealthArticle')

# --- NEW MODEL FOR MANUAL VITALS ENTRY ---
class VitalsRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    # All vitals are optional (nullable=True)
    temperature = db.Column(db.Float, nullable=True) # Celsius
    blood_pressure_systolic = db.Column(db.Integer, nullable=True) # Upper number
    blood_pressure_diastolic = db.Column(db.Integer, nullable=True) # Lower number
    heart_rate = db.Column(db.Integer, nullable=True) # BPM
    respiratory_rate = db.Column(db.Integer, nullable=True) # Breaths per minute
    oxygen_saturation = db.Column(db.Integer, nullable=True) # SpO2 %
    blood_sugar = db.Column(db.Float, nullable=True) # mg/dL or mmol/L
    height = db.Column(db.Float, nullable=True) # cm
    weight = db.Column(db.Float, nullable=True) # kg

    def __repr__(self):
        return f'<VitalsRecord {self.id} for patient {self.patient_id}>'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))
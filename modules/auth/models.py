from flask_login import UserMixin
from datetime import datetime
import bcrypt

#local imports
from core.database import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='user', nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirmed_on = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    memberships = db.relationship('Membership', back_populates='user', cascade='all, delete-orphan')
    events_attended = db.relationship('EventAttendance', back_populates='user')
    announcements = db.relationship('Announcement', back_populates='author')
    contributions = db.relationship('Contribution', back_populates='user')

    def set_password(self, password):
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def has_role(self, role):
        return self.role == role
    
    @property
    def is_admin(self):
        return self.role == 'admin'

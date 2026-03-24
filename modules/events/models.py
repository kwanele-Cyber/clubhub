from core.database import db
from datetime import datetime

class Event(db.Model):
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    event_type = db.Column(db.String(50))  # 'meeting', 'workshop', 'social', 'fundraiser'
    location = db.Column(db.String(200))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    max_attendees = db.Column(db.Integer)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    club = db.relationship('Club', back_populates='events')
    attendance = db.relationship('EventAttendance', back_populates='event', cascade='all, delete-orphan')
    
    @property
    def attendee_count(self):
        return len([a for a in self.attendance if a.status == 'attended'])

class EventAttendance(db.Model):
    __tablename__ = 'event_attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='registered')  # 'registered', 'attended', 'cancelled'
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    checked_in_at = db.Column(db.DateTime)
    
    # Relationships
    event = db.relationship('Event', back_populates='attendance')
    user = db.relationship('User', back_populates='events_attended')
    
    __table_args__ = (db.UniqueConstraint('event_id', 'user_id', name='unique_attendance'),)
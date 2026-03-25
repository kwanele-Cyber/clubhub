from core.database import db
from datetime import datetime

class Badge(db.Model):
    __tablename__ = 'badges'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(200))  # Icon class or URL
    category = db.Column(db.String(50))  # 'attendance', 'contribution', 'leadership', 'achievement'
    points_required = db.Column(db.Integer)  # Points needed to earn this badge
    events_required = db.Column(db.Integer)  # Events needed to attend
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user_badges = db.relationship('UserBadge', back_populates='badge')

class UserBadge(db.Model):
    __tablename__ = 'user_badges'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='badges')
    badge = db.relationship('Badge', back_populates='user_badges')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'badge_id', name='unique_user_badge'),)

class Contribution(db.Model):
    __tablename__ = 'contributions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)
    points = db.Column(db.Integer, nullable=False)
    contribution_type = db.Column(db.String(50))  # 'event_attendance', 'event_creation', 'announcement', 'referral'
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='contributions')
    club = db.relationship('Club')
    event = db.relationship('Event')

class Leaderboard(db.Model):
    __tablename__ = 'leaderboards'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=True)  # NULL for global
    period = db.Column(db.String(20))  # 'weekly', 'monthly', 'all_time'
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Store leaderboard data as JSON
    rankings = db.Column(db.JSON)
    
    # Relationships
    club = db.relationship('Club')
from core.database import db
from datetime import datetime

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='medium')  # 'low', 'medium', 'high'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'in-progress', 'completed'
    due_date = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    club = db.relationship('Club', back_populates='tasks')
    creator_user = db.relationship('User', foreign_keys=[created_by], backref='tasks_created')
    assigned_user = db.relationship('User', foreign_keys=[assigned_to], backref='tasks_assigned')

from core.database import db

class Event(db.Model):
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Relationships
    club = db.relationship('Club', backref='events')
    creator = db.relationship('User', backref='events')
    
    def __repr__(self):
        return f'<Event {self.title}>'
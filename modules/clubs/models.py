from core.database import db
from datetime import datetime
import json

class Club(db.Model):
    __tablename__ = 'clubs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=True)  # Public vs Private request-only clubs
    logo_url = db.Column(db.String(200))
    banner_url = db.Column(db.String(200))
    max_members = db.Column(db.Integer, nullable=True)
    forum_moderation_required = db.Column(db.Boolean, default=False)
    
    # Relationships
    memberships = db.relationship('Membership', back_populates='club', cascade='all, delete-orphan')
    events = db.relationship('Event', back_populates='club', cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', back_populates='club', cascade='all, delete-orphan')
    tasks = db.relationship('Task', back_populates='club', cascade='all, delete-orphan')
    roles = db.relationship('ClubRole', back_populates='club', cascade='all, delete-orphan')

class ClubRole(db.Model):
    __tablename__ = 'club_roles'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    
    # Permissions stored as JSON string: {"manage_members": true, "post_announcements": true, ...}
    permissions_json = db.Column(db.Text, default='{}')
    
    is_default = db.Column(db.Boolean, default=False) # e.g. Leader, Officer, Member
    
    # Relationships
    club = db.relationship('Club', back_populates='roles')
    memberships = db.relationship('Membership', back_populates='club_role')

    @property
    def permissions(self):
        try:
            return json.loads(self.permissions_json)
        except:
            return {}

    @permissions.setter
    def permissions(self, value):
        self.permissions_json = json.dumps(value)

    def has_permission(self, perm):
        perms = self.permissions
        return perms.get(perm, False) or perms.get('all', False)

class Membership(db.Model):
    __tablename__ = 'memberships'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('club_roles.id'), nullable=True) # Link to custom role
    
    # Deprecated but kept for quick checks / legacy fallback
    role = db.Column(db.String(50), default='member')  # 'leader', 'officer', 'member' 
    
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    joined_at = db.Column(db.DateTime)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='memberships')
    club = db.relationship('Club', back_populates='memberships')
    club_role = db.relationship('ClubRole', back_populates='memberships')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'club_id', name='unique_membership'),)

    def has_perm(self, perm):
        if self.status != 'approved':
            return False
        # Special case for hardcoded 'leader' if role_id is somehow missing
        if self.role == 'leader':
            return True
        if self.club_role:
            return self.club_role.has_permission(perm)
        return False
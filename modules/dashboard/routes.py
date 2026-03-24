from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func

#local import
from core.database import db
from modules.clubs.models import Club, Membership
from modules.events.models import Event, EventAttendance
from modules.announcements.models import Announcement
from modules.dashboard.models import Contribution, UserBadge


dashboard_bp = Blueprint('dashboard', __name__,template_folder='templates')


@dashboard_bp.route('/dashoard/')
@login_required
def index():
    return render_template('index.html')

@dashboard_bp.route('/dashboard/profile')
@login_required
def profile():
    # Get user's statistics
    club_count = Membership.query.filter_by(
        user_id=current_user.id,
        status='approved'
    ).count()
    
    event_count = EventAttendance.query.filter_by(
        user_id=current_user.id,
        status='attended'
    ).count()
    
    total_points = db.session.query(func.sum(Contribution.points)).filter(
        Contribution.user_id == current_user.id
    ).scalar() or 0
    
    # Get user's badges
    badges = UserBadge.query.filter_by(user_id=current_user.id).all()
    
    # Get recent activity
    recent_contributions = Contribution.query.filter_by(
        user_id=current_user.id
    ).order_by(Contribution.created_at.desc()).limit(5).all()
    
    return render_template('profile.html',
                         club_count=club_count,
                         event_count=event_count,
                         total_points=total_points,
                         badges=badges,
                         recent_contributions=recent_contributions)

@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    # Get user's clubs
    club_count = Membership.query.filter_by(
        user_id=current_user.id,
        status='approved'
    ).count()
    
    # Get upcoming events count
    event_count = Event.query.join(Membership, Event.club_id == Membership.club_id).filter(
        Membership.user_id == current_user.id,
        Membership.status == 'approved',
        Event.start_time >= datetime.utcnow(),
        Event.is_active == True
    ).count()
    
    # Get total points
    total_points = db.session.query(func.sum(Contribution.points)).filter(
        Contribution.user_id == current_user.id
    ).scalar() or 0
    
    # Get recent announcements count
    announcement_count = Announcement.query.join(Membership, Announcement.club_id == Membership.club_id).filter(
        Membership.user_id == current_user.id,
        Membership.status == 'approved',
        Announcement.is_active == True
    ).count()
    
    return jsonify({
        'club_count': club_count,
        'event_count': event_count,
        'total_points': total_points,
        'announcement_count': announcement_count
    })
     
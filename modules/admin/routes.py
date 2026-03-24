from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func


from core.database import db
from modules.auth.models import User
from modules.clubs.models import Club, Membership
from modules.events.models import Event, EventAttendance
from modules.announcements.models import Announcement

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
def check_admin():
    if not current_user.is_admin:
        return render_template('403.html'), 403

@admin_bp.route('/admin/')
def dashboard():
    return render_template('dashboard.html')

@admin_bp.route('/api/stats')
def api_stats():
    # Total counts
    total_users = User.query.count()
    total_clubs = Club.query.count()
    total_events = Event.query.count()
    total_announcements = Announcement.query.count()
    
    # Active users (last 30 days)
    month_ago = datetime.utcnow() - timedelta(days=30)
    active_users = User.query.filter(User.last_login >= month_ago).count()
    
    # New users (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users = User.query.filter(User.created_at >= week_ago).count()
    
    # Events this month
    events_this_month = Event.query.filter(
        Event.start_time >= month_ago
    ).count()
    
    # Membership stats
    total_memberships = Membership.query.filter_by(status='approved').count()
    pending_requests = Membership.query.filter_by(status='pending').count()
    
    # Attendance stats
    total_attendance = EventAttendance.query.filter_by(status='attended').count()
    
    # Clubs by category
    clubs_by_category = db.session.query(
        Club.category, func.count(Club.id)
    ).group_by(Club.category).all()
    
    return jsonify({
        'total_users': total_users,
        'total_clubs': total_clubs,
        'total_events': total_events,
        'total_announcements': total_announcements,
        'active_users': active_users,
        'new_users': new_users,
        'events_this_month': events_this_month,
        'total_memberships': total_memberships,
        'pending_requests': pending_requests,
        'total_attendance': total_attendance,
        'clubs_by_category': dict(clubs_by_category)
    })

@admin_bp.route('/admin/users')
def users_report():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=users)

@admin_bp.route('/admin/clubs')
def clubs_report():
    clubs = Club.query.all()
    club_stats = []
    
    for club in clubs:
        stats = {
            'club': club,
            'member_count': Membership.query.filter_by(club_id=club.id, status='approved').count(),
            'event_count': Event.query.filter_by(club_id=club.id).count(),
            'announcement_count': Announcement.query.filter_by(club_id=club.id).count()
        }
        club_stats.append(stats)
    
    return render_template('clubs.html', club_stats=club_stats)

@admin_bp.route('/admin/engagement')
def engagement_report():
    # Get top clubs by engagement
    top_clubs = db.session.query(
        Club.id,
        Club.name,
        func.count(EventAttendance.id).label('attendance_count')
    ).join(Event, Club.id == Event.club_id
    ).join(EventAttendance, Event.id == EventAttendance.event_id
    ).filter(EventAttendance.status == 'attended'
    ).group_by(Club.id, Club.name
    ).order_by(func.count(EventAttendance.id).desc()
    ).limit(10).all()
    
    # Get top users by points
    from app.models.gamification import Contribution
    top_users = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        func.sum(Contribution.points).label('total_points')
    ).join(Contribution, User.id == Contribution.user_id
    ).group_by(User.id, User.first_name, User.last_name
    ).order_by(func.sum(Contribution.points).desc()
    ).limit(10).all()
    
    return render_template('engagement.html',
                         top_clubs=top_clubs,
                         top_users=top_users)
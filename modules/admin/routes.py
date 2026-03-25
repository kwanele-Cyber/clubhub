from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user, login_required

# local imports
from core.database import db
from modules.auth.models import User
from modules.clubs.models import Club
from modules.events.models import Event

admin_bp = Blueprint('admin', __name__, template_folder='templates')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    user_count = User.query.count()
    club_count = Club.query.count()
    event_count = Event.query.count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    users = User.query.all()
    return render_template('admin/dashboard.html', users=users, user_count=user_count, club_count=club_count, event_count=event_count, recent_users=recent_users)

@admin_bp.route('/user/<int:user_id>/toggle_admin')
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.role = 'admin' if user.role == 'user' else 'user'
    db.session.commit()
    flash(f'{user.full_name}\'s role has been updated.', 'success')
    return redirect(url_for('admin.dashboard'))

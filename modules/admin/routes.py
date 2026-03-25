from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user, login_required

# local imports
from core.database import db
from modules.auth.models import User

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
    users = User.query.all()
    return render_template('admin/dashboard.html', users=users)

@admin_bp.route('/user/<int:user_id>/toggle_admin')
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    user.role = 'admin' if user.role == 'user' else 'user'
    db.session.commit()
    flash(f'{user.full_name}\'s role has been updated.', 'success')
    return redirect(url_for('admin.dashboard'))

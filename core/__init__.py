from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect

from dotenv import load_dotenv
import os

# local imports
from core.config import Config
from core.database import db, migrate

# Initialize extensions
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()

# Load environment variables from .env file
load_dotenv()

def create_app(config_class=Config):
    app = Flask(__name__, template_folder='templates', static_folder='../static')

    app.config.from_object(config_class)


    # Configuration from environment variables
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///club_management.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Mail configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

    
    
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    
    # Configure login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Import and register modules
    from modules.auth.routes import auth_bp
    from modules.clubs.routes import clubs_bp
    from modules.events.routes import events_bp
    from modules.dashboard.routes import dashboard_bp
    from modules.admin.routes import admin_bp
    from modules.tasks.routes import tasks_bp
    from modules.forum.routes import forum_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(clubs_bp, url_prefix='/clubs')
    app.register_blueprint(events_bp, url_prefix='/events')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(forum_bp, url_prefix='/forum')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    # Root route
    @app.route('/')
    def index():
        if current_user.is_authenticated and current_user.has_role('admin'):
            return redirect(url_for('admin.dashboard'))
    
        return redirect(url_for('dashboard.index'))
    
    from modules.auth.models import User
    from modules.clubs.models import Membership

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_user_clubs():
        if current_user.is_authenticated:
            user_memberships = Membership.query.filter_by(
                user_id=current_user.id, 
                status='approved'
            ).all()
            user_clubs = [m.club for m in user_memberships]
            return dict(user_clubs=user_clubs)
        return dict(user_clubs=[])
        
    return app

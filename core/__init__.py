from flask import Flask, redirect, url_for, render_template
from flask_mail import Mail
from flask_login import LoginManager
from dotenv import load_dotenv
import os


from core.config import Config
from core.database import db, migrate


# Initialize extensions
login_manager = LoginManager()
mail = Mail()

# Load environment variables from .env file
load_dotenv()

def create_app(config_class=Config):
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='../static')
    app.config.from_object(config_class)


     # Configuration from environment variables
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///club_management.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Mail configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    
    # Optional: Add debug output to verify configuration (remove in production)
    print("=== App Configuration ===")
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Mail Server: {app.config['MAIL_SERVER']}")
    print(f"Mail Username: {app.config['MAIL_USERNAME']}")
    print("=========================")
    
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Configure login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'


    # Import and register modules
    from modules.auth import auth_bp
    from modules.clubs import clubs_bp
    from modules.events import events_bp
    from modules.dashboard import dashboard_bp
    from modules.admin.routes import admin_bp
    from modules.tasks import tasks_bp
    from modules.forum import forum_bp

    app.register_blueprint(auth_bp,) #kwanele
    app.register_blueprint(clubs_bp, ) #user2
    app.register_blueprint(events_bp, ) #member3
    app.register_blueprint(admin_bp,) #member4
    app.register_blueprint(dashboard_bp,) #member5
    app.register_blueprint(tasks_bp,) #member6
    app.register_blueprint(forum_bp,) #member7
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    # Root route
    @app.route('/')
    def index():
        if current_user.is_admin:
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
        from flask_login import current_user
        if current_user.is_authenticated:
            user_memberships = Membership.query.filter_by(
                user_id=current_user.id, 
                status='approved'
            ).all()
            user_clubs = [m.club for m in user_memberships]
            return dict(user_clubs=user_clubs)
        return dict(user_clubs=[])
    return app
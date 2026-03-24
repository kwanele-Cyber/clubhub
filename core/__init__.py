from flask import Flask, render_template
from flask_login import LoginManager
from core.config import Config
from core.database import db, migrate

# Initialize extensions
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='../static')
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Configure login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Import and register modules
    from modules.auth import auth_bp
    #from modules.clubs import clubs_bp
    #from modules.events import events_bp
    
    app.register_blueprint(auth_bp)
    #app.register_blueprint(clubs_bp, url_prefix='/clubs')
    #app.register_blueprint(events_bp, url_prefix='/events')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404
    
    return app
    

from modules.auth.models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
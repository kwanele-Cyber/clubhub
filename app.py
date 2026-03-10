#region imports

from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from dotenv import load_dotenv

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
#endregion



load_dotenv()
app = Flask(__name__)




#region config

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'developmennt-secret-key'

#endregion


#region init_extentions

#database setup
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#flask-login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth/login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


#endregion

#region db_models

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    password_hash = db.Column(db.String(200),nullable=False)

    full_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, server_default=db.func.now())


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username}>'

#endregion

#region form_models
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[DataRequired()])
    password = PasswordField('Password',validators=[DataRequired()])
    password2 = PasswordField('Confirm Password',validators=[DataRequired(),EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose another.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use another or login.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


#endregion



#region routes


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/users')
def users():
    users = User.query.all()
    return render_template('users/index.html', users=users)

@app.route('/auth/signup', methods=['GET', 'POST'])
def signup():
    #when user logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Check if user exists
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username not available, Please choose another one.')
            return redirect(url_for('signup'))
        
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name = form.full_name.data
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()
        
        flash('SignUp successful! Proceed to login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/signup.html', form=form)

@app.route('/auth/login', methods=["GET","POST"])
def login():
    #when user logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password_hash(form.password.data):
            login_user(user, remeber=form.remeber_me.data)
            user.update_last_login()

            flash(f"Welcom back, {user.fulname}!", "Success")

            #redirect to the page the user wanted to access, or dashboard
            next_page=request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('auth/login.html',form=form)

@app.route('/auth/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required #nobody can access without login
def dashboard():
    return render_template('dashboard.html')

@app.route('/auth/profile')
def profile():
    render_template('auth/profile.html', user=current_user)

#TODO:isolate this s that it wont be available during production
@app.route('/dev/create-test-user')
def create_test_user():
    """Helper route to create a test user"""
    # Check if test user already exists
    test_user = User.query.filter_by(username='testuser').first()
    if test_user:
        return "Test user already exists! <a href='/login'>Go to Login</a>"
    
    # Create test user
    user = User(
        username='testuser',
        email='test@example.com',
        full_name='Test User'
    )
    user.set_password('Test123!')  # Password: Test123!
    
    db.session.add(user)
    db.session.commit()
    
    return "Test user created! Username: testuser, Password: Test123! <a href='/login'>Go to Login</a>"




#endregion


if __name__ == '__main__':
    app.run(debug=True)

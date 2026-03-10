#region imports

from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from dotenv import load_dotenv

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email

#endregion



load_dotenv()
app = Flask(__name__)




#region config

#database Config
#---------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'developmennt-secret-key'

#endregion


#region init_extentions

#database setup
#--------------
db = SQLAlchemy(app)
migrate = Migrate(app, db)


#endregion

#region db_models

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    def __repr__(self):
        return f'<User {self.username}>'

#endregion

#region form_models
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Register')


#endregion

#region routes

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

#region users_crud
@app.route('/users')
def list_users():
    users = User.query.all()
    return render_template('users/index.html', users=users)

@app.route('/auth/signup', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Check if user exists
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            return "Username already taken!"
        
        # Create new user
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        db.session.add(user)
        db.session.commit()
        
        return f"User {user.username} created! <a href='/users'>View Users</a>"
    
    return render_template('auth/signup.html', form=form)

#endregion



#endregion


if __name__ == '__main__':
    app.run(debug=True)

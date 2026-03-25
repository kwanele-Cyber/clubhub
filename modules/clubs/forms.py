from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Length, ValidationError, Optional
from modules.clubs.models import Club

class ClubCreateForm(FlaskForm):
    name = StringField('Club Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=20, max=2000)])
    category = SelectField('Category', choices=[
        ('academic', 'Academic'),
        ('sports', 'Sports'),
        ('cultural', 'Cultural'),
        ('arts', 'Arts'),
        ('technology', 'Technology'),
        ('community', 'Community Service'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    max_members = IntegerField('Maximum Members (Optional)', validators=[Optional()])
    is_public = BooleanField('Public Club (Anyone can join without approval)', default=True)
    submit = SubmitField('Create Club')
    
    def validate_name(self, name):
        club = Club.query.filter_by(name=name.data).first()
        if club:
            raise ValidationError('A club with this name already exists.')

class MembershipRequestForm(FlaskForm):
    reason = TextAreaField('Reason for Joining', validators=[Length(max=500)])
    submit = SubmitField('Send Request')
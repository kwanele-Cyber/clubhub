from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length
from modules.clubs.models import Club

class EventForm(FlaskForm):
    title = StringField('Event Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[Length(max=500)])
    date = DateTimeField('Date and Time', validators=[DataRequired()], format='%Y-%m-%d %H:%M')
    location = StringField('Location', validators=[Length(max=200)])
    club_id = SelectField('Club', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Create Event')
    
    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.club_id.choices = [(club.id, club.name) for club in Club.query.all()]
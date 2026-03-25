from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from datetime import datetime

class EventCreateForm(FlaskForm):
    title = StringField('Event Title', validators=[DataRequired(), Length(min=3, max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=20, max=5000)])
    event_type = SelectField('Event Type', choices=[
        ('meeting', 'Meeting'),
        ('workshop', 'Workshop'),
        ('social', 'Social Event'),
        ('fundraiser', 'Fundraiser'),
        ('competition', 'Competition'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired(), Length(max=200)])
    start_time = DateTimeField('Start Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_time = DateTimeField('End Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    max_attendees = IntegerField('Maximum Attendees (Optional)', validators=[Optional()])
    submit = SubmitField('Create Event')
    
    def validate_end_time(self, field):
        if field.data <= self.start_time.data:
            raise ValidationError('End time must be after start time.')
        
    def validate_start_time(self, field):
        if field.data < datetime.now():
            raise ValidationError('Start time cannot be in the past.')
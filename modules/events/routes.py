from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from core.database import db
from modules.events.models import Event
from modules.events.forms import EventForm

events_bp = Blueprint('events', __name__, template_folder='templates')

@events_bp.route('/')
def list():
    events = Event.query.all()
    return render_template('list.html', title='Events', events=events)

@events_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            title=form.title.data,
            description=form.description.data,
            date=form.date.data,
            location=form.location.data,
            club_id=form.club_id.data,
            created_by=current_user.id
        )
        db.session.add(event)
        db.session.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('events.list'))
    
    return render_template('create.html', title='Create Event', form=form)
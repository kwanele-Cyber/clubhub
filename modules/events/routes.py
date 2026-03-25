<<<<<<< HEAD
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
=======
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from wtforms.validators import DataRequired


#local imports
from core.database import db
from modules.events.models import Event, EventAttendance
from modules.events.forms import EventCreateForm
from modules.clubs.models import Club, Membership
from modules.auth.models import User  

events_bp = Blueprint('events', __name__,template_folder='templates')

@events_bp.route('/')
@login_required
def list_events():
    # Get filter parameters
    filter_type = request.args.get('filter', 'upcoming')
    club_id = request.args.get('club_id', type=int)
    
    # Base query
    query = Event.query.filter_by(is_active=True)
    
    # Apply filters
    now = datetime.utcnow()
    if filter_type == 'upcoming':
        query = query.filter(Event.start_time >= now)
    elif filter_type == 'past':
        query = query.filter(Event.end_time < now)
    elif filter_type == 'today':
        today_start = datetime(now.year, now.month, now.day)
        tomorrow_start = today_start.replace(day=today_start.day + 1)
        query = query.filter(Event.start_time >= today_start, Event.start_time < tomorrow_start)
    elif filter_type == 'this_week':
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=7)
        query = query.filter(Event.start_time >= week_start, Event.start_time < week_end)
    
    if club_id:
        query = query.filter(Event.club_id == club_id)
    
    # Order by date
    if filter_type == 'past':
        events = query.order_by(Event.start_time.desc()).all()
    else:
        events = query.order_by(Event.start_time).all()
    
    # Get user's clubs for filter dropdown
    user_clubs = Club.query.join(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.status == 'approved'
    ).all()
    
    # Get user's registrations
    user_registrations = {
        a.event_id: a for a in EventAttendance.query.filter_by(user_id=current_user.id).all()
    }
    
    return render_template('events/list.html',
                         events=events,
                         user_clubs=user_clubs,
                         user_registrations=user_registrations,
                         current_filter=filter_type,
                         current_club=club_id)

@events_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_event():
    form = EventCreateForm()
    
    # Get clubs where user is leader
    led_clubs = Club.query.join(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.role == 'leader',
        Membership.status == 'approved'
    ).all()
    
    if not led_clubs:
        flash('You must be a club leader to create events.', 'warning')
        return redirect(url_for('events.list_events'))
    
    # Add club selection to form dynamically
    from wtforms import SelectField
    form.club_id = SelectField('Club', choices=[(c.id, c.name) for c in led_clubs], validators=[DataRequired()])
    
    if form.validate_on_submit():
        event = Event(
            club_id=form.club_id.data,
            title=form.title.data,
            description=form.description.data,
            event_type=form.event_type.data,
            location=form.location.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            max_attendees=form.max_attendees.data,
            created_by=current_user.id
        )
        
        db.session.add(event)
        db.session.commit()
        
        flash(f'Event "{event.title}" created successfully!', 'success')
        return redirect(url_for('events.view_event', event_id=event.id))
    
    return render_template('events/create.html', form=form, led_clubs=led_clubs)

@events_bp.route('/<int:event_id>')
@login_required
def view_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Check if user is registered
    registration = EventAttendance.query.filter_by(
        event_id=event_id,
        user_id=current_user.id
    ).first()
    
    # Get attendees
    attendees = db.session.query(User, EventAttendance).join(
        EventAttendance, User.id == EventAttendance.user_id
    ).filter(
        EventAttendance.event_id == event_id,
        EventAttendance.status.in_(['registered', 'attended'])
    ).all()
    
    # Check if user can manage (club leader)
    can_manage = False
    if current_user.is_authenticated:
        membership = Membership.query.filter_by(
            user_id=current_user.id,
            club_id=event.club_id,
            role='leader',
            status='approved'
        ).first()
        can_manage = membership is not None
    
    return render_template('events/view.html',
                         event=event,
                         registration=registration,
                         attendees=attendees,
                         can_manage=can_manage)

@events_bp.route('/<int:event_id>/register', methods=['POST'])
@login_required
def register_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Check if event is in the future
    if event.start_time < datetime.utcnow():
        flash('Cannot register for past events.', 'danger')
        return redirect(url_for('events.view_event', event_id=event_id))
    
    # Check if already registered
    existing = EventAttendance.query.filter_by(
        event_id=event_id,
        user_id=current_user.id
    ).first()
    
    if existing:
        if existing.status == 'cancelled':
            # Reactivate cancelled registration
            existing.status = 'registered'
            existing.registered_at = datetime.utcnow()
            db.session.commit()
            flash('Your registration has been reactivated!', 'success')
        else:
            flash('You are already registered for this event.', 'info')
        return redirect(url_for('events.view_event', event_id=event_id))
    
    # Check attendee limit
    if event.max_attendees:
        current_attendees = EventAttendance.query.filter_by(
            event_id=event_id,
            status='registered'
        ).count()
        if current_attendees >= event.max_attendees:
            flash('This event has reached its maximum capacity.', 'danger')
            return redirect(url_for('events.view_event', event_id=event_id))
    
    # Create registration
    registration = EventAttendance(
        event_id=event_id,
        user_id=current_user.id,
        status='registered'
    )
    
    db.session.add(registration)
    db.session.commit()
    
    flash('You have successfully registered for this event!', 'success')
    return redirect(url_for('events.view_event', event_id=event_id))

@events_bp.route('/<int:event_id>/cancel', methods=['POST'])
@login_required
def cancel_registration(event_id):
    event = Event.query.get_or_404(event_id)
    
    registration = EventAttendance.query.filter_by(
        event_id=event_id,
        user_id=current_user.id,
        status='registered'
    ).first_or_404()
    
    registration.status = 'cancelled'
    db.session.commit()
    
    flash('Your registration has been cancelled.', 'success')
    return redirect(url_for('events.view_event', event_id=event_id))

@events_bp.route('/<int:event_id>/check-in/<int:user_id>', methods=['POST'])
@login_required
def check_in_attendee(event_id, user_id):
    # Check if user can manage (club leader)
    event = Event.query.get_or_404(event_id)
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=event.club_id,
        role='leader',
        status='approved'
    ).first()
    
    if not membership:
        flash('You do not have permission to check in attendees.', 'danger')
        return redirect(url_for('events.view_event', event_id=event_id))
    
    registration = EventAttendance.query.filter_by(
        event_id=event_id,
        user_id=user_id,
        status='registered'
    ).first_or_404()
    
    registration.status = 'attended'
    registration.checked_in_at = datetime.utcnow()
    
    # Award points for attendance
    from app.models.gamification import Contribution
    points = Contribution(
        user_id=user_id,
        club_id=event.club_id,
        event_id=event_id,
        points=10,  # Base points for attendance
        contribution_type='event_attendance',
        description=f'Attended event: {event.title}'
    )
    
    db.session.add(points)
    db.session.commit()
    
    flash('Attendee checked in successfully!', 'success')
    return redirect(url_for('events.view_event', event_id=event_id))

@events_bp.route('/api/events/upcoming')
@login_required
def api_upcoming_events():
    """API endpoint for real-time dashboard updates"""
    events = Event.query.filter(
        Event.start_time >= datetime.utcnow(),
        Event.is_active == True
    ).order_by(Event.start_time).limit(10).all()
    
    events_data = [{
        'id': e.id,
        'title': e.title,
        'club': e.club.name,
        'start_time': e.start_time.isoformat(),
        'location': e.location
    } for e in events]
    
    return jsonify(events_data)

@events_bp.route('/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Check if user can edit (club leader)
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=event.club_id,
        role='leader',
        status='approved'
    ).first()
    
    if not membership:
        flash('You do not have permission to edit this event.', 'danger')
        return redirect(url_for('events.view_event', event_id=event_id))
    
    form = EventCreateForm()
    
    if form.validate_on_submit():
        event.title = form.title.data
        event.description = form.description.data
        event.event_type = form.event_type.data
        event.location = form.location.data
        event.start_time = form.start_time.data
        event.end_time = form.end_time.data
        event.max_attendees = form.max_attendees.data
        
        db.session.commit()
        flash('Event updated successfully!', 'success')
        return redirect(url_for('events.view_event', event_id=event_id))
    
    # Pre-populate form
    if request.method == 'GET':
        form.title.data = event.title
        form.description.data = event.description
        form.event_type.data = event.event_type
        form.location.data = event.location
        form.start_time.data = event.start_time
        form.end_time.data = event.end_time
        form.max_attendees.data = event.max_attendees
    
    return render_template('events/edit.html', form=form, event=event)

from datetime import timedelta
>>>>>>> 720ddde7f028556e55d54ea73c0da8d172ad6708

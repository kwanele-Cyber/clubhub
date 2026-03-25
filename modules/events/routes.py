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
    
    # Get clubs where user has 'create_events' permission
    all_memberships = Membership.query.filter_by(
        user_id=current_user.id,
        status='approved'
    ).all()
    
    authorized_clubs = [m.club for m in all_memberships if m.has_perm('create_events')]
    
    if not authorized_clubs:
        flash('You do not have permission to create events in any club.', 'warning')
        return redirect(url_for('events.list_events'))
    
    # Add club selection to form dynamically
    from wtforms import SelectField
    form.club_id = SelectField('Club', choices=[(c.id, c.name) for c in authorized_clubs], validators=[DataRequired()])
    
    if form.validate_on_submit():
        # Double check permission for selected club
        target_membership = Membership.query.filter_by(
            user_id=current_user.id,
            club_id=form.club_id.data,
            status='approved'
        ).first()
        
        if not target_membership or not target_membership.has_perm('create_events'):
            flash('Unauthorized for this club.', 'danger')
            return redirect(url_for('events.list_events'))

        event = Event(
            club_id=form.club_id.data,
            title=form.title.data,
            description=form.description.data,
            event_type=form.event_type.data,
            location=form.location.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            max_attendees=form.max_attendees.data,
            price=form.price.data,
            created_by=current_user.id
        )
        
        db.session.add(event)
        db.session.commit()
        
        flash(f'Event "{event.title}" created successfully!', 'success')
        return redirect(url_for('events.view_event', event_id=event.id))
    
    return render_template('events/create.html', form=form, led_clubs=authorized_clubs)

@events_bp.route('/<int:event_id>')
@login_required
def view_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    registration = EventAttendance.query.filter_by(
        event_id=event_id,
        user_id=current_user.id
    ).first()
    
    attendees = db.session.query(User, EventAttendance).join(
        EventAttendance, User.id == EventAttendance.user_id
    ).filter(
        EventAttendance.event_id == event_id,
        EventAttendance.status.in_(['registered', 'attended'])
    ).all()
    
    # Permission checks using new system
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=event.club_id,
        status='approved'
    ).first()
    can_manage = membership and membership.has_perm('create_events')
    
    return render_template('events/view.html',
                         event=event,
                         registration=registration,
                         attendees=attendees,
                         can_manage=can_manage,
                         now=datetime.utcnow())

@events_bp.route('/<int:event_id>/register', methods=['POST'])
@login_required
def register_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    if event.start_time < datetime.utcnow():
        flash('Cannot register for past events.', 'danger')
        return redirect(url_for('events.view_event', event_id=event_id))
    
    existing = EventAttendance.query.filter_by(
        event_id=event_id,
        user_id=current_user.id
    ).first()
    
    # Generate unique ticket ID
    import uuid
    ticket_id = f"TKT-{event.id}-{current_user.id}-{uuid.uuid4().hex[:8].upper()}"
    
    if existing:
        if existing.status == 'cancelled':
            existing.status = 'registered'
            existing.registered_at = datetime.utcnow()
            if not existing.ticket_id:
                existing.ticket_id = ticket_id
            db.session.commit()
            flash('Your registration has been reactivated!', 'success')
        else:
            flash('You are already registered for this event.', 'info')
        return redirect(url_for('events.view_event', event_id=event_id))
    
    if event.max_attendees:
        current_attendees = EventAttendance.query.filter_by(
            event_id=event_id,
            status='registered'
        ).count()
        if current_attendees >= event.max_attendees:
            flash('This event has reached its maximum capacity.', 'danger')
            return redirect(url_for('events.view_event', event_id=event_id))
    
    registration = EventAttendance(
        event_id=event_id,
        user_id=current_user.id,
        status='registered',
        ticket_id=ticket_id
    )
    
    db.session.add(registration)
    db.session.commit()
    
    flash('You have successfully registered for this event! Your ticket is in your Wallet.', 'success')
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
    event = Event.query.get_or_404(event_id)
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=event.club_id,
        status='approved'
    ).first()
    
    if not membership or not membership.has_perm('create_events'): # use create_events perm for management
        flash('Unauthorized', 'danger')
        return redirect(url_for('events.view_event', event_id=event_id))
    
    registration = EventAttendance.query.filter_by(
        event_id=event_id,
        user_id=user_id,
        status='registered'
    ).first_or_404()
    
    registration.status = 'attended'
    registration.checked_in_at = datetime.utcnow()
    db.session.commit()
    
    flash('Attendee checked in!', 'success')
    return redirect(url_for('events.view_event', event_id=event_id))

@events_bp.route('/api/events/upcoming')
@login_required
def api_upcoming_events():
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

@events_bp.route('/wallet')
@login_required
def wallet():
    # Fetch all user's active event registrations (excluding cancelled)
    tickets = EventAttendance.query.join(Event).filter(
        EventAttendance.user_id == current_user.id,
        EventAttendance.status.in_(['registered', 'attended'])
    ).order_by(Event.start_time.desc()).all()
    
    return render_template('events/wallet.html', tickets=tickets)

@events_bp.route('/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=event.club_id,
        status='approved'
    ).first()
    
    if not membership or not membership.has_perm('create_events'):
        flash('Unauthorized', 'danger')
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
        event.price = form.price.data
        db.session.commit()
        flash('Event updated!', 'success')
        return redirect(url_for('events.view_event', event_id=event_id))
    
    if request.method == 'GET':
        form.title.data = event.title
        form.description.data = event.description
        form.event_type.data = event.event_type
        form.location.data = event.location
        form.start_time.data = event.start_time
        form.end_time.data = event.end_time
        form.max_attendees.data = event.max_attendees
    
    return render_template('events/edit.html', form=form, event=event)
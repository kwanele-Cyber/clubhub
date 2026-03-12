#region imports

from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, url_for, abort, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import text, or_
import os
from dotenv import load_dotenv

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, PasswordField, BooleanField, TextAreaField, SelectField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
#endregion



load_dotenv()
app = Flask(__name__)

os.makedirs(app.instance_path, exist_ok=True)
os.makedirs(os.path.join(app.instance_path, 'uploads'), exist_ok=True)




#region config

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'developmennt-secret-key'
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB

#endregion


#region init_extentions

#database setup
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#flask-login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


# Permission helpers
def is_admin(user):
    return bool(user and (user.role == 'admin' or user.is_admin))


def is_leader(user):
    return bool(user and user.role == 'leader')


def can_create_event(user):
    return bool(user and (is_admin(user) or is_leader(user)))


def can_manage_club_requests(user, membership):
    return bool(user and (is_admin(user) or (membership and (membership.role in ['owner', 'admin'] or user.role == 'leader'))))




ALLOWED_UPLOAD_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

#region db_models

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    password_hash = db.Column(db.String(200),nullable=False)

    full_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default='student')
    last_login = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    memberships = db.relationship('Membership', back_populates='user', cascade='all, delete-orphan')
    events = db.relationship('Event', back_populates='creator', cascade='all, delete-orphan')
    invites_sent = db.relationship('EventInvite', back_populates='inviter', foreign_keys='EventInvite.invited_by', cascade='all, delete-orphan')
    invites_received = db.relationship('EventInvite', back_populates='invitee', foreign_keys='EventInvite.user_id', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username}>'


class Club(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    members = db.relationship('Membership', back_populates='club', cascade='all, delete-orphan')
    events = db.relationship('Event', back_populates='club', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Club {self.name}>'


class Membership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=False)
    role = db.Column(db.String(50), default='member')
    status = db.Column(db.String(20), default='pending')
    proof_document = db.Column(db.String(255))
    joined_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship('User', back_populates='memberships')
    club = db.relationship('Club', back_populates='members')

    __table_args__ = (db.UniqueConstraint('user_id', 'club_id', name='uq_membership_user_club'),)

    def __repr__(self):
        return f'<Membership user={self.user_id} club={self.club_id}>'


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(120))
    event_date = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    club = db.relationship('Club', back_populates='events')
    creator = db.relationship('User', back_populates='events')
    invites = db.relationship('EventInvite', back_populates='event', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Event {self.title}>'


class EventInvite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invited_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    sent_at = db.Column(db.DateTime, server_default=db.func.now())
    responded_at = db.Column(db.DateTime)

    event = db.relationship('Event', back_populates='invites')
    invitee = db.relationship('User', back_populates='invites_received', foreign_keys=[user_id])
    inviter = db.relationship('User', back_populates='invites_sent', foreign_keys=[invited_by])

    __table_args__ = (db.UniqueConstraint('event_id', 'user_id', name='uq_event_invite_user_event'),)

    def __repr__(self):
        return f'<EventInvite event={self.event_id} user={self.user_id}>'


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by_role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    author = db.relationship('User')

    def __repr__(self):
        return f'<Announcement {self.title}>'

#endregion

# Ensure tables exist in dev runs (use migrations in production)
with app.app_context():
    db.create_all()

    # Lightweight dev schema upgrades for SQLite (avoids manual DB resets)
    try:
        if db.engine.dialect.name == 'sqlite':
            user_cols = [row[1] for row in db.session.execute(text("PRAGMA table_info(user)")).fetchall()]
            if 'role' not in user_cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'student'"))
                db.session.execute(text("UPDATE user SET role='student' WHERE role IS NULL"))

            if 'registration_proof' not in user_cols:
                db.session.execute(text("ALTER TABLE user ADD COLUMN registration_proof VARCHAR(255)"))

            membership_cols = [row[1] for row in db.session.execute(text("PRAGMA table_info(membership)")).fetchall()]
            if 'status' not in membership_cols:
                db.session.execute(text("ALTER TABLE membership ADD COLUMN status VARCHAR(20) DEFAULT 'pending'"))
                db.session.execute(text("UPDATE membership SET status='approved' WHERE status IS NULL"))

            if 'proof_document' not in membership_cols:
                db.session.execute(text("ALTER TABLE membership ADD COLUMN proof_document VARCHAR(255)"))

            db.session.commit()
    except Exception:
        db.session.rollback()

#region form_models
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[DataRequired()])
    role = SelectField('Role', choices=[('student', 'Student'), ('leader', 'Leader'), ('admin', 'Admin')], validators=[DataRequired()])
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



class ClubForm(FlaskForm):
    name = StringField('Club Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    submit = SubmitField('Create Club')


class EventForm(FlaskForm):
    club_id = SelectField('Club', coerce=int, validators=[DataRequired()])
    title = StringField('Event Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    location = StringField('Location')
    event_date = DateTimeLocalField('Event Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    submit = SubmitField('Create Event')

class EventInviteForm(FlaskForm):
    user_id = SelectField('Invite Member', coerce=int, validators=[DataRequired()])
    message = TextAreaField('Message')
    submit = SubmitField('Send Invite')

class AnnouncementForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    body = TextAreaField('Announcement', validators=[DataRequired()])
    submit = SubmitField('Post Announcement')

#endregion



#region routes


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/users')
def users():
    users = User.query.all()
    return render_template('users/index.html', users=users)

@app.route('/admin')
@login_required
def admin_dashboard():
    if not is_admin(current_user):
        abort(403)

    total_users = User.query.count()
    total_students = User.query.filter_by(role='student').count()
    total_leaders = User.query.filter_by(role='leader').count()
    total_admins = User.query.filter_by(role='admin').count()

    total_clubs = Club.query.count()
    total_memberships = Membership.query.filter_by(status='approved').count()
    pending_requests = Membership.query.filter_by(status='pending').count()

    total_events = Event.query.count()
    total_invites = EventInvite.query.count()
    pending_invites = EventInvite.query.filter_by(status='pending').count()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_students=total_students,
        total_leaders=total_leaders,
        total_admins=total_admins,
        total_clubs=total_clubs,
        total_memberships=total_memberships,
        pending_requests=pending_requests,
        total_events=total_events,
        total_invites=total_invites,
        pending_invites=pending_invites
    )


@app.route('/admin/users')
@login_required
def admin_users():
    if not is_admin(current_user):
        abort(403)
    users = User.query.order_by(User.username.asc()).all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/users/<int:user_id>/role', methods=['POST'])
@login_required
def admin_update_role(user_id):
    if not is_admin(current_user):
        abort(403)

    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', '').strip()
    if new_role not in ['student', 'leader', 'admin']:
        flash('Invalid role.', 'warning')
        return redirect(url_for('admin_users'))

    user.role = new_role
    user.is_admin = (new_role == 'admin')
    db.session.commit()

    flash(f"Updated {user.username} to {new_role}.", 'success')
    return redirect(url_for('admin_users'))



@app.route('/clubs')
@login_required
def clubs():
    query = request.args.get('q', '').strip()
    base = Club.query
    if query:
        like = f"%{query}%"
        base = base.filter(or_(Club.name.ilike(like), Club.description.ilike(like)))
    clubs = base.order_by(Club.name.asc()).all()

    approved_memberships = [m for m in current_user.memberships if m.status == 'approved']
    pending_memberships = [m for m in current_user.memberships if m.status == 'pending']

    member_club_ids = {m.club_id for m in approved_memberships}
    pending_club_ids = {m.club_id for m in pending_memberships}

    pending_counts = {}
    can_manage = {}
    for club in clubs:
        pending_counts[club.id] = Membership.query.filter_by(club_id=club.id, status='pending').count()
        membership = next((m for m in current_user.memberships if m.club_id == club.id), None)
        can_manage[club.id] = bool(membership and (membership.role in ['owner', 'admin'] or current_user.role in ['admin', 'leader']))

    return render_template('clubs/index.html', clubs=clubs, member_club_ids=member_club_ids, pending_club_ids=pending_club_ids, pending_counts=pending_counts, can_manage=can_manage, query=query)


@app.route('/clubs/create', methods=['GET', 'POST'])
@login_required
def create_club():
    form = ClubForm()
    if form.validate_on_submit():
        existing = Club.query.filter_by(name=form.name.data.strip()).first()
        if existing:
            flash('A club with that name already exists.', 'warning')
            return redirect(url_for('create_club'))

        club = Club(
            name=form.name.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
            created_by=current_user.id
        )
        db.session.add(club)
        db.session.flush()

        membership = Membership(user_id=current_user.id, club_id=club.id, role='owner', status='approved')
        db.session.add(membership)
        db.session.commit()

        flash('Club created successfully!', 'success')
        return redirect(url_for('clubs'))

    return render_template('clubs/create.html', form=form)


@app.route('/clubs/<int:club_id>/join', methods=['POST'])
@login_required
def join_club(club_id):
    if current_user.role != 'student':
        flash('Only students can request to join clubs.', 'warning')
        return redirect(url_for('clubs'))

    club = Club.query.get_or_404(club_id)
    existing = Membership.query.filter_by(user_id=current_user.id, club_id=club.id).first()
    if existing:
        if existing.status == 'approved':
            flash('You are already a member of this club.', 'info')
            return redirect(url_for('clubs'))
        if existing.status == 'pending':
            flash('Your join request is still pending.', 'info')
            return redirect(url_for('clubs'))
        if existing.status == 'declined':
            existing.status = 'pending'
            db.session.commit()
            flash('Your join request was re-submitted.', 'info')
            return redirect(url_for('clubs'))

    proof_filename = None
    if current_user.role == 'student':
        proof_file = request.files.get('proof_document')
        if not proof_file or proof_file.filename == '':
            flash('Proof of registration is required for students.', 'danger')
            return redirect(url_for('clubs'))

        ext = proof_file.filename.rsplit('.', 1)[-1].lower()
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            flash('Invalid file type. Upload PDF, PNG, JPG, or JPEG.', 'danger')
            return redirect(url_for('clubs'))

        safe_name = secure_filename(proof_file.filename)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{current_user.username}_{safe_name}"
        proof_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        proof_file.save(proof_path)
        proof_filename = filename

    membership = Membership(user_id=current_user.id, club_id=club.id, role='member', status='pending', proof_document=proof_filename)
    db.session.add(membership)
    db.session.commit()

    flash(f'Join request sent to {club.name}.', 'info')
    return redirect(url_for('clubs'))


@app.route('/clubs/requests/<int:membership_id>/proof')
@login_required
def download_request_proof(membership_id):
    req = Membership.query.get_or_404(membership_id)
    club = Club.query.get_or_404(req.club_id)
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club.id).first()
    can_manage = can_manage_club_requests(current_user, membership)
    if not can_manage:
        abort(403)

    if not req.proof_document:
        flash('No proof document found for this request.', 'info')
        return redirect(url_for('club_requests', club_id=club.id))

    return send_from_directory(app.config['UPLOAD_FOLDER'], req.proof_document, as_attachment=True)


@app.route('/clubs/<int:club_id>/requests')
@login_required
def club_requests(club_id):
    club = Club.query.get_or_404(club_id)
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club.id).first()
    can_manage = can_manage_club_requests(current_user, membership)
    if not can_manage:
        abort(403)

    requests = Membership.query.filter_by(club_id=club.id, status='pending').order_by(Membership.joined_at.asc()).all()
    return render_template('clubs/requests.html', club=club, requests=requests)


@app.route('/clubs/<int:club_id>/requests/<int:membership_id>/approve', methods=['POST'])
@login_required
def approve_request(club_id, membership_id):
    club = Club.query.get_or_404(club_id)
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club.id).first()
    can_manage = can_manage_club_requests(current_user, membership)
    if not can_manage:
        abort(403)

    request_member = Membership.query.get_or_404(membership_id)
    if request_member.club_id != club.id or request_member.status != 'pending':
        flash('Invalid request.', 'warning')
        return redirect(url_for('club_requests', club_id=club.id))

    request_member.status = 'approved'
    db.session.commit()
    flash('Request approved.', 'success')
    return redirect(url_for('club_requests', club_id=club.id))


@app.route('/clubs/<int:club_id>/requests/<int:membership_id>/decline', methods=['POST'])
@login_required
def decline_request(club_id, membership_id):
    club = Club.query.get_or_404(club_id)
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club.id).first()
    can_manage = can_manage_club_requests(current_user, membership)
    if not can_manage:
        abort(403)

    request_member = Membership.query.get_or_404(membership_id)
    if request_member.club_id != club.id or request_member.status != 'pending':
        flash('Invalid request.', 'warning')
        return redirect(url_for('club_requests', club_id=club.id))

    request_member.status = 'declined'
    db.session.commit()
    flash('Request declined.', 'info')
    return redirect(url_for('club_requests', club_id=club.id))


@app.route('/events')
@login_required
def events():
    if is_admin(current_user):
        events = Event.query.order_by(Event.event_date.asc()).all()
    else:
        member_club_ids = [m.club_id for m in current_user.memberships if m.status == 'approved']
        if not member_club_ids:
            events = []
        else:
            events = Event.query.filter(Event.club_id.in_(member_club_ids)).order_by(Event.event_date.asc()).all()

    event_permissions = {}
    for event in events:
        membership = next((m for m in current_user.memberships if m.club_id == event.club_id and m.status == 'approved'), None)
        can_invite = (can_create_event(current_user) and membership and (event.created_by == current_user.id or membership.role in ['owner', 'admin'] or current_user.role == 'leader'))
        event_permissions[event.id] = bool(can_invite)

    return render_template('events/index.html', events=events, event_permissions=event_permissions)


@app.route('/events/create', methods=['GET', 'POST'])
@login_required
def create_event():
    if not can_create_event(current_user):
        flash('Only leaders or admins can create events.', 'danger')
        return redirect(url_for('events'))

    memberships = [m for m in current_user.memberships if m.status == 'approved']
    if not memberships:
        flash('Join a club before creating an event.', 'warning')
        return redirect(url_for('clubs'))

    form = EventForm()
    form.club_id.choices = [(m.club.id, m.club.name) for m in memberships]

    if form.validate_on_submit():
        event = Event(
            club_id=form.club_id.data,
            title=form.title.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
            location=form.location.data.strip() if form.location.data else None,
            event_date=form.event_date.data,
            created_by=current_user.id
        )
        db.session.add(event)
        db.session.commit()

        flash('Event created successfully!', 'success')
        return redirect(url_for('events'))

    return render_template('events/create.html', form=form)


@app.route('/events/<int:event_id>/invite', methods=['GET', 'POST'])
@login_required
def invite_event(event_id):
    event = Event.query.get_or_404(event_id)
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=event.club_id, status='approved').first()
    can_invite = (can_create_event(current_user) and membership and (event.created_by == current_user.id or membership.role in ['owner', 'admin'] or current_user.role == 'leader'))
    if not can_invite:
        flash('You do not have permission to invite members to this event.', 'danger')
        return redirect(url_for('events'))

    form = EventInviteForm()
    existing_invite_ids = {i.user_id for i in event.invites}
    eligible_members = [m for m in event.club.members if m.status == 'approved' and m.user_id not in existing_invite_ids and m.user_id != current_user.id]
    form.user_id.choices = [(m.user.id, f"{m.user.full_name} (@{m.user.username})") for m in eligible_members]

    if not form.user_id.choices:
        flash('No eligible members to invite for this event.', 'info')

    if form.validate_on_submit():
        invite = EventInvite(
            event_id=event.id,
            user_id=form.user_id.data,
            invited_by=current_user.id,
            message=form.message.data.strip() if form.message.data else None
        )
        db.session.add(invite)
        db.session.commit()
        flash('Invitation sent!', 'success')
        return redirect(url_for('invite_event', event_id=event.id))

    invites = EventInvite.query.filter_by(event_id=event.id).order_by(EventInvite.sent_at.desc()).all()
    return render_template('events/invite.html', form=form, event=event, invites=invites)


@app.route('/invites')
@login_required
def invites():
    if is_admin(current_user):
        invites = EventInvite.query.order_by(EventInvite.sent_at.desc()).all()
    else:
        invites = EventInvite.query.filter_by(user_id=current_user.id).order_by(EventInvite.sent_at.desc()).all()
    return render_template('invites/index.html', invites=invites)


@app.route('/invites/<int:invite_id>/accept', methods=['POST'])
@login_required
def accept_invite(invite_id):
    invite = EventInvite.query.get_or_404(invite_id)
    if invite.user_id != current_user.id:
        abort(403)
    if invite.status != 'pending':
        flash('This invite is already responded to.', 'info')
        return redirect(url_for('invites'))

    invite.status = 'accepted'
    invite.responded_at = datetime.utcnow()
    db.session.commit()
    flash('Invite accepted.', 'success')
    return redirect(url_for('invites'))


@app.route('/announcements')
@login_required
def announcements():
    if current_user.role == 'admin':
        ann = Announcement.query.filter_by(created_by=current_user.id).order_by(Announcement.created_at.desc()).all()
    elif current_user.role == 'leader':
        ann = Announcement.query.filter(
            (Announcement.created_by_role == 'admin') | (Announcement.created_by == current_user.id)
        ).order_by(Announcement.created_at.desc()).all()
    else:
        ann = Announcement.query.filter(Announcement.created_by_role.in_(['admin', 'leader'])).order_by(Announcement.created_at.desc()).all()

    return render_template('announcements/index.html', announcements=ann)


@app.route('/announcements/new', methods=['GET', 'POST'])
@login_required
def new_announcement():
    if current_user.role not in ['admin', 'leader']:
        abort(403)

    form = AnnouncementForm()
    if form.validate_on_submit():
        announcement = Announcement(
            title=form.title.data.strip(),
            body=form.body.data.strip(),
            created_by=current_user.id,
            created_by_role=current_user.role
        )
        db.session.add(announcement)
        db.session.commit()
        flash('Announcement posted.', 'success')
        return redirect(url_for('announcements'))

    return render_template('announcements/new.html', form=form)


@app.route('/invites/<int:invite_id>/decline', methods=['POST'])
@login_required
def decline_invite(invite_id):
    invite = EventInvite.query.get_or_404(invite_id)
    if invite.user_id != current_user.id:
        abort(403)
    if invite.status != 'pending':
        flash('This invite is already responded to.', 'info')
        return redirect(url_for('invites'))

    invite.status = 'declined'
    invite.responded_at = datetime.utcnow()
    db.session.commit()
    flash('Invite declined.', 'warning')
    return redirect(url_for('invites'))



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
            full_name = form.full_name.data,
            role=form.role.data
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

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            user.update_last_login()

            flash(f"Welcome back, {user.full_name}!", "success")

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
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)

#TODO:isolate this s that it wont be available during production
@app.route('/dev/create-test-user')
def create_test_user():
    """Helper route to create a test user"""
    # Check if test user already exists
    test_user = User.query.filter_by(username='testuser').first()
    if test_user:
        return f"Test user already exists! <a href='{url_for('login')}'>Go to Login</a>"
    # Create test user
    user = User(
        username='testuser',
        email='test@example.com',
        full_name='Test User',
        role='student'
    )
    user.set_password('Test123!')  # Password: Test123!
    
    db.session.add(user)
    db.session.commit()
    
    return f"Test user created! Username: testuser, Password: Test123! <a href='{url_for('login')}'>Go to Login</a>"




#endregion


if __name__ == '__main__':
    app.run(debug=True)


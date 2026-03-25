from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from core.database import db
from modules.clubs.models import Club, Membership, ClubRole
from modules.clubs.forms import ClubCreateForm, MembershipRequestForm
from modules.auth.models import User
from modules.events.models import Event
from modules.announcements.models import Announcement
from datetime import datetime
import json

clubs_bp = Blueprint('clubs', __name__,template_folder='templates')

DEFAULT_PERMISSIONS = {
    'leader': {
        'manage_members': True,
        'post_announcements': True,
        'manage_tasks': True,
        'create_events': True,
        'moderate_forum': True,
        'create_polls': True,
        'all': True
    },
    'officer': {
        'manage_members': False,
        'post_announcements': True,
        'manage_tasks': True,
        'create_events': True,
        'moderate_forum': True,
        'create_polls': True
    },
    'member': {
        'manage_members': False,
        'post_announcements': False,
        'manage_tasks': False,
        'create_events': False,
        'moderate_forum': False,
        'create_polls': False
    }
}

def init_club_roles(club_id):
    roles = []
    # Leader
    leader = ClubRole(club_id=club_id, name='Leader', is_default=True)
    leader.permissions = DEFAULT_PERMISSIONS['leader']
    roles.append(leader)
    
    # Officer
    officer = ClubRole(club_id=club_id, name='Officer', is_default=True)
    officer.permissions = DEFAULT_PERMISSIONS['officer']
    roles.append(officer)
    
    # Member
    member = ClubRole(club_id=club_id, name='Member', is_default=True)
    member.permissions = DEFAULT_PERMISSIONS['member']
    roles.append(member)
    
    for r in roles:
        db.session.add(r)
    db.session.commit()
    return leader, officer, member

@clubs_bp.route('/clubs')
@login_required
def list_clubs():
    q = request.args.get('q', '')
    category = request.args.get('category', '')
    
    query = Club.query
    if q:
        query = query.filter(Club.name.ilike(f'%{q}%') | Club.description.ilike(f'%{q}%'))
    if category:
        query = query.filter_by(category=category)
        
    clubs = query.all()
    user_memberships = {m.club_id: m for m in current_user.memberships}
    
    categories = db.session.query(Club.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    return render_template('club/list.html', clubs=clubs, user_memberships=user_memberships, q=q, category=category, categories=categories)

@clubs_bp.route('/clubs/create', methods=['GET', 'POST'])
@login_required
def create_club():
    form = ClubCreateForm()
    if form.validate_on_submit():
        club = Club(
            name=form.name.data,
            description=form.description.data,
            category=form.category.data,
            max_members=form.max_members.data,
            is_public=form.is_public.data,
            created_by=current_user.id
        )
        db.session.add(club)
        db.session.flush() # Get club ID
        
        # Initialize default roles
        leader_role, _, _ = init_club_roles(club.id)
        
        # Creator becomes a leader
        membership = Membership(
            user_id=current_user.id,
            club_id=club.id,
            role_id=leader_role.id,
            role='leader', # Fallback
            status='approved',
            joined_at=datetime.utcnow()
        )
        db.session.add(membership)
        db.session.commit()
        
        flash(f'Club "{club.name}" created successfully!', 'success')
        return redirect(url_for('clubs.view_club', club_id=club.id))
    
    return render_template('club/create.html', form=form)

@clubs_bp.route('/clubs/<int:club_id>/join', methods=['POST'])
@login_required
def join_club(club_id):
    club = Club.query.get_or_404(club_id)
    
    # Check if membership exists
    existing_membership = Membership.query.filter_by(user_id=current_user.id, club_id=club.id).first()
    if existing_membership:
        flash('You have already joined or requested to join this club.', 'info')
        return redirect(url_for('clubs.view_club', club_id=club.id))
        
    # Check max members if public
    if club.is_public and club.max_members:
        current_members = Membership.query.filter_by(club_id=club.id, status='approved').count()
        if current_members >= club.max_members:
            flash(f'{club.name} has reached its maximum member limit.', 'warning')
            return redirect(url_for('clubs.view_club', club_id=club.id))
            
    status = 'approved' if club.is_public else 'pending'
    role_id = ClubRole.query.filter_by(club_id=club.id, name='Member').first().id
    
    membership = Membership(
        user_id=current_user.id,
        club_id=club.id,
        role_id=role_id,
        role='member',
        status=status,
        joined_at=datetime.utcnow() if status == 'approved' else None
    )
    db.session.add(membership)
    db.session.commit()
    
    if status == 'approved':
        flash(f'You successfully joined {club.name}!', 'success')
    else:
        flash(f'Your request to join {club.name} has been sent for approval.', 'info')
        
    return redirect(url_for('clubs.view_club', club_id=club.id))

@clubs_bp.route('/clubs/<int:club_id>')
@login_required
def view_club(club_id):
    club = Club.query.get_or_404(club_id)
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club_id).first()
    
    members = db.session.query(User, Membership).join(
        Membership, User.id == Membership.user_id
    ).filter(
        Membership.club_id == club_id,
        Membership.status == 'approved'
    ).all()
    
    events = Event.query.filter_by(club_id=club_id).filter(
        Event.start_time >= datetime.utcnow()
    ).order_by(Event.start_time).all()
    
    announcements = Announcement.query.filter_by(club_id=club_id).order_by(
        Announcement.created_at.desc()
    ).limit(5).all()
    
    # Permission checks
    can_manage_members = membership and membership.has_perm('manage_members')
    can_post_announcement = membership and membership.has_perm('post_announcements')
    can_view_tasks = membership and membership.has_perm('manage_tasks')
    
    # Pending members for those who can manage them
    pending_members = []
    if can_manage_members:
        pending = Membership.query.filter_by(club_id=club_id, status='pending').all()
        pending_members = [(m_p, User.query.get(m_p.user_id)) for m_p in pending]
    
    # Get all available roles for the role change dropdown
    club_roles = ClubRole.query.filter_by(club_id=club_id).all()
    
    # Legacy flag for "Leader" UI visibility
    is_leader = membership and (membership.role == 'leader' or (membership.club_role and membership.club_role.name == 'Leader'))

    tasks = []
    forum_topics = []
    polls = []
    if membership and membership.status == 'approved':
        from modules.tasks.models import Task
        from modules.forum.models import ForumTopic, Poll
        tasks = Task.query.filter_by(club_id=club_id).all()
        forum_topics = ForumTopic.query.filter_by(club_id=club_id, status='approved').all()
        polls = Poll.query.filter_by(club_id=club_id, is_active=True).all()
    
    return render_template('/club/view.html',
                         club=club,
                         membership=membership,
                         members=members,
                         events=events,
                         announcements=announcements,
                         tasks=tasks,
                         forum_topics=forum_topics,
                         polls=polls,
                         club_roles=club_roles,
                         can_manage_members=can_manage_members,
                         can_post_announcement=can_post_announcement,
                         can_view_tasks=can_view_tasks,
                         is_leader=is_leader,
                         pending_members=pending_members)

@clubs_bp.route('/clubs/<int:club_id>/members/<int:user_id>/approve', methods=['POST'])
@login_required
def approve_member(club_id, user_id):
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club_id, status='approved').first()
    if not membership or not membership.has_perm('manage_members'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('clubs.view_club', club_id=club_id))
    
    pending = Membership.query.filter_by(user_id=user_id, club_id=club_id, status='pending').first_or_404()
    
    # Assign default member role if exists
    member_role = ClubRole.query.filter_by(club_id=club_id, name='Member').first()
    if member_role:
        pending.role_id = member_role.id
        pending.role = 'member'
        
    pending.status = 'approved'
    pending.joined_at = datetime.utcnow()
    db.session.commit()
    flash('Member approved!', 'success')
    return redirect(url_for('clubs.view_club', club_id=club_id))

@clubs_bp.route('/clubs/<int:club_id>/members/<int:user_id>/remove', methods=['POST'])
@login_required
def remove_member(club_id, user_id):
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club_id, status='approved').first()
    if not membership or not membership.has_perm('manage_members'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('clubs.view_club', club_id=club_id))
    
    # Cannot remove yourself (the requester)
    if user_id == current_user.id:
        flash('You cannot remove yourself.', 'warning')
        return redirect(url_for('clubs.view_club', club_id=club_id))
        
    target = Membership.query.filter_by(user_id=user_id, club_id=club_id).first_or_404()
    
    # If target is leader, only other leaders (if any) or admin should theoretically be able to remove, 
    # but for simplicity now, let's just allow anyone with manage_members (usually leaders/officers)
    # to remove anyone else.
    
    db.session.delete(target)
    db.session.commit()
    flash('Member removed from club.', 'info')
    return redirect(url_for('clubs.view_club', club_id=club_id))

@clubs_bp.route('/clubs/<int:club_id>/announcements/create', methods=['POST'])
@login_required
def create_announcement(club_id):
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club_id, status='approved').first()
    if not membership or not membership.has_perm('post_announcements'):
        flash('Only authorized members can create announcements.', 'danger')
        return redirect(url_for('clubs.view_club', club_id=club_id))
    
    title = request.form.get('title')
    content = request.form.get('content')
    priority = request.form.get('priority', 'normal')
    
    announcement = Announcement(club_id=club_id, author_id=current_user.id, title=title, content=content, priority=priority)
    db.session.add(announcement)
    db.session.commit()
    flash('Announcement posted!', 'success')
    return redirect(url_for('clubs.view_club', club_id=club_id))

@clubs_bp.route('/clubs/<int:club_id>/members/<int:user_id>/role', methods=['POST'])
@login_required
def change_role(club_id, user_id):
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club_id, status='approved').first()
    if not membership or not membership.has_perm('manage_members'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('clubs.view_club', club_id=club_id))
        
    target = Membership.query.filter_by(user_id=user_id, club_id=club_id, status='approved').first_or_404()
    role_id = request.form.get('role_id')
    
    if role_id:
        new_role = ClubRole.query.get_or_404(role_id)
        if new_role.club_id != club_id:
            flash('Invalid role', 'danger')
            return redirect(url_for('clubs.view_club', club_id=club_id))
            
        target.role_id = new_role.id
        target.role = new_role.name.lower()
        db.session.commit()
        flash(f'Role updated to {new_role.name}!', 'success')
    
    return redirect(url_for('clubs.view_club', club_id=club_id))

@clubs_bp.route('/clubs/<int:club_id>/roles/create', methods=['POST'])
@login_required
def create_custom_role(club_id):
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club_id, status='approved').first()
    if not membership or not membership.has_perm('manage_members'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('clubs.view_club', club_id=club_id))
        
    name = request.form.get('name')
    if not name:
        flash('Role name is required', 'danger')
        return redirect(url_for('clubs.view_club', club_id=club_id))
        
    perms = {
        'manage_members': 'perm_members' in request.form,
        'post_announcements': 'perm_announce' in request.form,
        'manage_tasks': 'perm_tasks' in request.form,
        'create_events': 'perm_events' in request.form,
        'moderate_forum': 'perm_forum' in request.form,
        'create_polls': 'perm_polls' in request.form
    }
    
    new_role = ClubRole(club_id=club_id, name=name)
    new_role.permissions = perms
    db.session.add(new_role)
    db.session.commit()
    
    flash(f'Custom role "{name}" created!', 'success')
    return redirect(url_for('clubs.view_club', club_id=club_id))
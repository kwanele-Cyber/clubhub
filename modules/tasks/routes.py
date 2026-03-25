from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from core.database import db
from modules.tasks.models import Task
from modules.clubs.models import Club, Membership
from modules.auth.models import User

tasks_bp = Blueprint('tasks', __name__, template_folder='templates')

@tasks_bp.route('/club/<int:club_id>/tasks')
@login_required
def list_tasks(club_id):
    club = Club.query.get_or_404(club_id)
    
    # Check membership
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=club_id,
        status='approved'
    ).first()
    
    if not membership or not membership.has_perm('manage_tasks'):
        flash("Unauthorized access to the task board.", "danger")
        return redirect(url_for('clubs.view_club', club_id=club_id))
        
    tasks = Task.query.filter_by(club_id=club_id).order_by(Task.due_date.asc()).all()
    
    # Get approved members for assignment dropdown
    club_members = db.session.query(User).join(Membership, User.id == Membership.user_id).filter(
        Membership.club_id == club_id,
        Membership.status == 'approved'
    ).all()
    
    return render_template('tasks/list.html', club=club, tasks=tasks, club_members=club_members)

@tasks_bp.route('/club/<int:club_id>/tasks/create', methods=['POST'])
@login_required
def create_task(club_id):
    club = Club.query.get_or_404(club_id)
    
    # Check if user can create tasks (with manage_tasks permission)
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=club_id,
        status='approved'
    ).first()
    
    if not membership or not membership.has_perm('manage_tasks'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    title = request.form.get('title')
    description = request.form.get('description')
    due_date_str = request.form.get('due_date')
    priority = request.form.get('priority', 'medium')
    assigned_to = request.form.get('assigned_to')
    
    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            due_date = None
            
    assigned_to_id = int(assigned_to) if assigned_to and assigned_to.isdigit() else None
        
    new_task = Task(
        club_id=club_id,
        title=title,
        description=description,
        due_date=due_date,
        priority=priority,
        created_by=current_user.id,
        assigned_to=assigned_to_id
    )
    
    db.session.add(new_task)
    db.session.commit()
    
    flash('Task created successfully!', 'success')
    return redirect(url_for('tasks.list_tasks', club_id=club_id))

@tasks_bp.route('/tasks/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    # Check if user has permission
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=task.club_id,
        status='approved'
    ).first()
    
    if not membership or not membership.has_perm('manage_tasks'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    if task.status == 'completed':
        task.status = 'pending'
        task.completed_at = None
    else:
        task.status = 'completed'
        task.completed_at = datetime.utcnow()
        
    db.session.commit()
    return jsonify({
        'status': task.status, 
        'completed_at': task.completed_at.isoformat() if task.completed_at else None
    })

@tasks_bp.route('/tasks/<int:task_id>/edit', methods=['POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    club = Club.query.get(task.club_id)
    
    # Check if user is creator or club owner
    is_creator = task.created_by == current_user.id
    is_owner = club.created_by == current_user.id
    
    if not (is_creator or is_owner):
        flash("You only have permission to edit tasks you created or if you are the club owner.", "danger")
        return redirect(url_for('tasks.list_tasks', club_id=task.club_id))
        
    task.title = request.form.get('title')
    task.description = request.form.get('description')
    due_date_str = request.form.get('due_date')
    task.priority = request.form.get('priority', 'medium')
    assigned_to = request.form.get('assigned_to')
    
    if due_date_str:
        try:
            task.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            pass
            
    task.assigned_to = int(assigned_to) if assigned_to and assigned_to.isdigit() else None
        
    db.session.commit()
    flash('Task updated successfully!', 'success')
    return redirect(url_for('tasks.list_tasks', club_id=task.club_id))

@tasks_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    club = Club.query.get(task.club_id)
    
    # Check if user is creator or club owner
    is_creator = task.created_by == current_user.id
    is_owner = club.created_by == current_user.id
    
    if not (is_creator or is_owner):
        flash("You only have permission to delete tasks you created or if you are the club owner.", "danger")
        return redirect(url_for('tasks.list_tasks', club_id=task.club_id))
        
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('tasks.list_tasks', club_id=task.club_id))

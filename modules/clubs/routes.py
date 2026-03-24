from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from core.database import db
from modules.clubs.models import Club
from modules.clubs.forms import ClubForm

clubs_bp = Blueprint('clubs', __name__, template_folder='templates')

@clubs_bp.route('/')
def list():
    clubs = Club.query.all()
    return render_template('list.html', title='Clubs', clubs=clubs)

@clubs_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = ClubForm()
    if form.validate_on_submit():
        club = Club(
            name=form.name.data,
            description=form.description.data,
            created_by=current_user.id
        )
        db.session.add(club)
        db.session.commit()
        flash('Club created successfully!', 'success')
        return redirect(url_for('clubs.list'))
    
    return render_template('create.html', title='Create Club', form=form)

@clubs_bp.route('/<int:club_id>')
def detail(club_id):
    club = Club.query.get_or_404(club_id)
    return render_template('detail.html', title=club.name, club=club)

@clubs_bp.route('/<int:club_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(club_id):
    club = Club.query.get_or_404(club_id)
    if club.created_by != current_user.id:
        abort(403)
    
    form = ClubForm()
    if form.validate_on_submit():
        club.name = form.name.data
        club.description = form.description.data
        db.session.commit()
        flash('Club updated successfully!', 'success')
        return redirect(url_for('clubs.detail', club_id=club.id))
    elif request.method == 'GET':
        form.name.data = club.name
        form.description.data = club.description
    
    return render_template('create.html', title='Edit Club', form=form, club=club)
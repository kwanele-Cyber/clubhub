from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from core.database import db
from modules.forum.models import ForumTopic, ForumComment, Post, Poll, PollOption, PollVote
from modules.clubs.models import Club, Membership

forum_bp = Blueprint('forum', __name__, template_folder='templates')

@forum_bp.route('/feed')
@login_required
def feed():
    # ID 2: View Tailored Feed
    # Get all joined clubs
    from modules.announcements.models import Announcement
    
    joined_club_ids = [m.club_id for m in current_user.memberships if m.status == 'approved']
    
    if not joined_club_ids:
        return render_template('forum/feed.html', posts=[], joined=False)
        
    # Get posts from these clubs
    posts = Post.query.filter(Post.club_id.in_(joined_club_ids)).all()
    
    # Get announcements from these clubs
    announcements = Announcement.query.filter(Announcement.club_id.in_(joined_club_ids)).all()
    
    # Combine and sort by created_at descending
    feed_items = posts + announcements
    feed_items.sort(key=lambda x: x.created_at, reverse=True)
    
    return render_template('forum/feed.html', posts=feed_items, joined=True)

@forum_bp.route('/club/<int:club_id>/forum')
@login_required
def club_forum(club_id):
    club = Club.query.get_or_404(club_id)
    
    # Check membership
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=club_id,
        status='approved'
    ).first()
    
    if not membership:
        flash("You are not a member of this club's forum", "danger")
        return redirect(url_for('clubs.list_clubs'))
        
    # List approved topics
    topics = ForumTopic.query.filter_by(club_id=club_id, status='approved').order_by(ForumTopic.created_at.desc()).all()
    
    # Members with moderate_forum permission also see pending topics
    pending_topics = []
    if membership.has_perm('moderate_forum'):
        pending_topics = ForumTopic.query.filter_by(club_id=club_id, status='pending').all()
        
    return render_template('forum/club_forum.html', 
                         club=club, 
                         topics=topics, 
                         pending_topics=pending_topics,
                         membership=membership)

@forum_bp.route('/club/<int:club_id>/forum/create', methods=['POST'])
@login_required
def create_topic(club_id):
    club = Club.query.get_or_404(club_id)
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club_id, status='approved').first()
    
    if not membership:
        return jsonify({'error': 'Unauthorized'}), 403
        
    title = request.form.get('title')
    content = request.form.get('content')
    
    # Check if moderation is required
    status = 'approved'
    if club.forum_moderation_required and not membership.has_perm('moderate_forum'):
        status = 'pending'
        flash("Your topic has been submitted for moderation", "info")
    else:
        flash("Topic published successfully", "success")
        
    new_topic = ForumTopic(
        club_id=club_id,
        author_id=current_user.id,
        title=title,
        content=content,
        status=status
    )
    
    db.session.add(new_topic)
    db.session.commit()
    
    return redirect(url_for('forum.club_forum', club_id=club_id))

@forum_bp.route('/forum/topic/<int:topic_id>')
@login_required
def view_topic(topic_id):
    topic = ForumTopic.query.get_or_404(topic_id)
    
    # Check membership for visibility
    membership = Membership.query.filter_by(
        user_id=current_user.id,
        club_id=topic.club_id,
        status='approved'
    ).first()
    
    if not membership:
        flash("Unauthorized view", "danger")
        return redirect(url_for('dashboard.index'))
        
    if topic.status != 'approved' and not membership.has_perm('moderate_forum') and topic.author_id != current_user.id:
        flash("This topic is pending moderation", "warning")
        return redirect(url_for('forum.club_forum', club_id=topic.club_id))
        
    return render_template('forum/view_topic.html', topic=topic, membership=membership)

@forum_bp.route('/forum/topic/<int:topic_id>/comment', methods=['POST'])
@login_required
def post_comment(topic_id):
    topic = ForumTopic.query.get_or_404(topic_id)
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=topic.club_id, status='approved').first()
    
    if not membership:
        return jsonify({'error': 'Unauthorized'}), 403
        
    content = request.form.get('content')
    if not content:
        flash("Comment cannot be empty", "warning")
        return redirect(url_for('forum.view_topic', topic_id=topic_id))
        
    comment = ForumComment(
        topic_id=topic_id,
        author_id=current_user.id,
        content=content
    )
    
    db.session.add(comment)
    db.session.commit()
    
    return redirect(url_for('forum.view_topic', topic_id=topic_id))

@forum_bp.route('/club/<int:club_id>/posts/create', methods=['POST'])
@login_required
def create_post(club_id):
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club_id, status='approved').first()
    
    # Use 'post_announcements' permission for feed posts as well
    if not membership or not membership.has_perm('post_announcements'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    content = request.form.get('content')
    image_url = request.form.get('image_url')
    
    post = Post(
        club_id=club_id,
        author_id=current_user.id,
        content=content,
        image_url=image_url
    )
    
    db.session.add(post)
    db.session.commit()
    flash("Post published to feed", "success")
    return redirect(url_for('clubs.view_club', club_id=club_id))

@forum_bp.route('/forum/moderate/<int:topic_id>/<string:action>', methods=['POST'])
@login_required
def moderate_topic(topic_id, action):
    topic = ForumTopic.query.get_or_404(topic_id)
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=topic.club_id, status='approved').first()
    
    if not membership or not membership.has_perm('moderate_forum'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    if action == 'approve':
        topic.status = 'approved'
        flash("Topic approved", "success")
    elif action == 'reject':
        topic.status = 'rejected'
        flash("Topic rejected", "warning")
        
    db.session.commit()
    return redirect(url_for('forum.club_forum', club_id=topic.club_id))

@forum_bp.route('/club/<int:club_id>/polls/create', methods=['GET'])
@login_required
def create_poll_view(club_id):
    club = Club.query.get_or_404(club_id)
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club_id, status='approved').first()
    
    if not membership or not membership.has_perm('create_polls'):
        flash("Unauthorized", "danger")
        return redirect(url_for('clubs.view_club', club_id=club_id))
        
    return render_template('forum/create_poll.html', club=club)

@forum_bp.route('/club/<int:club_id>/polls/create', methods=['POST'])
@login_required
def create_poll(club_id):
    club = Club.query.get_or_404(club_id)
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=club_id, status='approved').first()
    
    if not membership or not membership.has_perm('create_polls'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    question = request.form.get('question')
    options = request.form.getlist('options')
    
    if not question or not options or len(options) < 2:
        flash("Question and at least two options are required", "danger")
        return redirect(url_for('forum.create_poll_view', club_id=club_id))
        
    poll = Poll(
        club_id=club_id,
        author_id=current_user.id,
        question=question
    )
    db.session.add(poll)
    db.session.flush() 
    
    for opt_text in options:
        if opt_text.strip():
            option = PollOption(poll_id=poll.id, text=opt_text.strip())
            db.session.add(option)
            
    db.session.commit()
    flash("Poll created successfully", "success")
    return redirect(url_for('clubs.view_club', club_id=club_id))

@forum_bp.route('/polls/<int:poll_id>/vote', methods=['POST'])
@login_required
def vote_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    option_id = request.form.get('option_id')
    
    membership = Membership.query.filter_by(user_id=current_user.id, club_id=poll.club_id, status='approved').first()
    if not membership:
        return jsonify({'error': 'Unauthorized'}), 403
        
    existing_vote = PollVote.query.filter_by(poll_id=poll_id, user_id=current_user.id).first()
    if existing_vote:
        flash("You have already voted in this poll", "info")
        return redirect(url_for('clubs.view_club', club_id=poll.club_id))
        
    vote = PollVote(
        poll_id=poll_id,
        option_id=option_id,
        user_id=current_user.id
    )
    db.session.add(vote)
    db.session.commit()
    
    flash("Your vote has been recorded", "success")
    return redirect(url_for('clubs.view_club', club_id=poll.club_id))

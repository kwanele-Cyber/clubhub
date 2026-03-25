#!/usr/bin/env python
from core.database import db
from core import create_app
from modules.auth.models import User
from modules.clubs.models import Club
from modules.events.models import Event

from modules.clubs.models import Club, Membership
from modules.events.models import Event, EventAttendance
from modules.announcements.models import Announcement
from modules.dashboard.models import Badge, Contribution
from core.utils.gamification import GamificationService
from datetime import datetime, timedelta


from modules.tasks.models import Task
from modules.forum.models import ForumTopic, ForumComment, Post, Poll, PollOption, PollVote



def init_database(drop_db = False):
    app = create_app()


    with app.app_context():
        # Create tables
        if drop_db:
            db.drop_all()  # Clear existing data (careful in production!)
        
        db.create_all()
        
        # Create default badges
        GamificationService.create_default_badges()
        
        # Create admin user
        admin = User(
            student_number='ADMIN001',
            first_name='Admin',
            last_name='User',
            email='admin@example.com',
            role = "admin",
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create test users
        users = []
        for i in range(1, 6):
            user = User(
                student_number=f'S{10000 + i}',
                first_name=f'Test{i}',
                last_name='User',
                email=f'test{i}@example.com',
                is_active=True
            )
            user.set_password('password123')
            db.session.add(user)
            users.append(user)
        
        db.session.commit()
        
        # Create clubs
        clubs = []
        club_data = [
            {'name': 'Programming Club', 'category': 'technology', 'description': 'Learn coding and build projects'},
            {'name': 'Chess Club', 'category': 'sports', 'description': 'Play chess and improve strategy'},
            {'name': 'Drama Society', 'category': 'arts', 'description': 'Theatre and performance arts'},
            {'name': 'Debate Team', 'category': 'academic', 'description': 'Public speaking and debate'}
        ]
        
        for data in club_data:
            club = Club(
                name=data['name'],
                description=data['description'],
                category=data['category'],
                created_by=admin.id,
                is_active=True
            )
            db.session.add(club)
            clubs.append(club)
        
        db.session.commit()
        
        # Add memberships
        # Admin as leader of all clubs
        for club in clubs:
            membership = Membership(
                user_id=admin.id,
                club_id=club.id,
                role='leader',
                status='approved',
                joined_at=datetime.utcnow()
            )
            db.session.add(membership)
        
        # Add test users as members
        for i, user in enumerate(users):
            for j, club in enumerate(clubs):
                if j <= i:  # Each user joins progressively more clubs
                    membership = Membership(
                        user_id=user.id,
                        club_id=club.id,
                        role='member',
                        status='approved',
                        joined_at=datetime.utcnow() - timedelta(days=i*10)
                    )
                    db.session.add(membership)
        
        db.session.commit()
        
        # Create events
        events = []
        for i, club in enumerate(clubs):
            for j in range(3):  # 3 events per club
                event = Event(
                    club_id=club.id,
                    title=f'{club.name} Event {j+1}',
                    description=f'Regular meeting and activities for {club.name}',
                    event_type='meeting',
                    location=f'Room {100 + i*10 + j}',
                    start_time=datetime.utcnow() + timedelta(days=7*j),
                    end_time=datetime.utcnow() + timedelta(days=7*j, hours=2),
                    created_by=admin.id,
                    max_attendees=30
                )
                db.session.add(event)
                events.append(event)
        
        db.session.commit()
        
        # Create announcements
        for club in clubs:
            announcement = Announcement(
                club_id=club.id,
                author_id=admin.id,
                title=f'Welcome to {club.name}',
                content=f'We are excited to have you join {club.name}. Stay tuned for updates!',
                priority='high'
            )
            db.session.add(announcement)
        
        db.session.commit()
        
        print("Database initialized successfully!")
        print("\nTest Credentials:")
        print("Admin - Email: admin@example.com, Password: admin123")
        for i, user in enumerate(users, 1):
            print(f"Test User {i} - Email: test{i}@example.com, Password: password123")

if __name__ == '__main__':
    #add get the argument to delete records on not
    _drop_db = False
    init_database(drop_db=_drop_db)
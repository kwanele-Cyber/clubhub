from datetime import datetime, timedelta
from sqlalchemy import func

from core.database import db
from modules.dashboard.models import Contribution, Badge, UserBadge, Leaderboard
from modules.auth.models import User
from modules.clubs.models import Club, Membership

class GamificationService:
    
    @staticmethod
    def award_points(user_id, club_id, points, contribution_type, description, event_id=None):
        """Award points to a user for a contribution"""
        contribution = Contribution(
            user_id=user_id,
            club_id=club_id,
            event_id=event_id,
            points=points,
            contribution_type=contribution_type,
            description=description
        )
        
        db.session.add(contribution)
        db.session.commit()
        
        # Check for new badges
        GamificationService.check_badges(user_id)
        
        # Update leaderboards
        GamificationService.update_leaderboards(club_id)
        
        return contribution
    
    @staticmethod
    def get_user_points(user_id, club_id=None):
        """Get total points for a user (globally or per club)"""
        query = db.session.query(func.sum(Contribution.points)).filter(Contribution.user_id == user_id)
        
        if club_id:
            query = query.filter(Contribution.club_id == club_id)
        
        return query.scalar() or 0
    
    @staticmethod
    def check_badges(user_id):
        """Check and award any newly earned badges"""
        user = User.query.get(user_id)
        
        # Get total points
        total_points = GamificationService.get_user_points(user_id)
        
        # Get event attendance count
        event_count = Contribution.query.filter_by(
            user_id=user_id,
            contribution_type='event_attendance'
        ).count()
        
        # Get all badges user doesn't have yet
        earned_badge_ids = [ub.badge_id for ub in user.badges]
        available_badges = Badge.query.filter(~Badge.id.in_(earned_badge_ids) if earned_badge_ids else True).all()
        
        new_badges = []
        for badge in available_badges:
            earned = False
            
            if badge.points_required and total_points >= badge.points_required:
                earned = True
            elif badge.events_required and event_count >= badge.events_required:
                earned = True
            
            if earned:
                user_badge = UserBadge(
                    user_id=user_id,
                    badge_id=badge.id
                )
                db.session.add(user_badge)
                new_badges.append(badge)
        
        if new_badges:
            db.session.commit()
        
        return new_badges
    
    @staticmethod
    def update_leaderboards(club_id=None):
        """Update leaderboard rankings"""
        period = 'all_time'  # Default
        
        # Query to get user points per club
        if club_id:
            # Club-specific leaderboard
            points_query = db.session.query(
                Contribution.user_id,
                func.sum(Contribution.points).label('total_points')
            ).filter(Contribution.club_id == club_id).group_by(Contribution.user_id)
        else:
            # Global leaderboard
            points_query = db.session.query(
                Contribution.user_id,
                func.sum(Contribution.points).label('total_points')
            ).group_by(Contribution.user_id)
        
        # Get top 100 users
        rankings = []
        for user_id, points in points_query.order_by(func.sum(Contribution.points).desc()).limit(100).all():
            user = User.query.get(user_id)
            rankings.append({
                'user_id': user_id,
                'name': user.full_name,
                'points': points,
                'avatar': None  # Could add avatar URL later
            })
        
        # Update or create leaderboard
        leaderboard = Leaderboard.query.filter_by(club_id=club_id, period=period).first()
        if leaderboard:
            leaderboard.rankings = rankings
        else:
            leaderboard = Leaderboard(
                club_id=club_id,
                period=period,
                rankings=rankings
            )
            db.session.add(leaderboard)
        
        db.session.commit()
    
    @staticmethod
    def create_default_badges():
        """Create default badges if they don't exist"""
        default_badges = [
            {
                'name': 'First Steps',
                'description': 'Attend your first event',
                'icon': 'fa-solid fa-shoe-prints',
                'category': 'attendance',
                'events_required': 1
            },
            {
                'name': 'Event Enthusiast',
                'description': 'Attend 10 events',
                'icon': 'fa-solid fa-calendar-check',
                'category': 'attendance',
                'events_required': 10
            },
            {
                'name': 'Event Master',
                'description': 'Attend 50 events',
                'icon': 'fa-solid fa-crown',
                'category': 'attendance',
                'events_required': 50
            },
            {
                'name': 'Contributor',
                'description': 'Earn 100 points',
                'icon': 'fa-solid fa-star',
                'category': 'contribution',
                'points_required': 100
            },
            {
                'name': 'Rising Star',
                'description': 'Earn 500 points',
                'icon': 'fa-solid fa-star',
                'category': 'contribution',
                'points_required': 500
            },
            {
                'name': 'Club Legend',
                'description': 'Earn 1000 points',
                'icon': 'fa-solid fa-star',
                'category': 'contribution',
                'points_required': 1000
            },
            {
                'name': 'Leader',
                'description': 'Create 5 events',
                'icon': 'fa-solid fa-user-tie',
                'category': 'leadership',
                'points_required': None,
                'events_required': None  # Custom logic
            },
            {
                'name': 'Community Builder',
                'description': 'Refer 5 new members',
                'icon': 'fa-solid fa-users',
                'category': 'achievement',
                'points_required': None
            }
        ]
        
        for badge_data in default_badges:
            existing = Badge.query.filter_by(name=badge_data['name']).first()
            if not existing:
                badge = Badge(**badge_data)
                db.session.add(badge)
        
        db.session.commit()
from flask_mail import Message
from flask import url_for
from app import mail
import os
from twilio.rest import Client  # For SMS (optional)
from flask import render_template, url_for

class NotificationService:
    
    @staticmethod
    def send_email(recipient, subject, template, **kwargs):
        """Send email notification"""
        try:
            msg = Message(
                subject=subject,
                recipients=[recipient],
                html=template,
                sender=os.getenv('MAIL_USERNAME')
            )
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False
    
    @staticmethod
    def send_sms(phone_number, message):
        """Send SMS notification (optional - requires Twilio)"""
        try:
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            
            if account_sid and auth_token:
                client = Client(account_sid, auth_token)
                client.messages.create(
                    body=message,
                    from_=os.getenv('TWILIO_PHONE_NUMBER'),
                    to=phone_number
                )
                return True
        except Exception as e:
            print(f"SMS sending failed: {e}")
        return False
    
    @staticmethod
    def notify_membership_request(club, user):
        """Notify club leaders about new membership request"""
        from app.models.club import Membership
        from flask import render_template
        
        leaders = Membership.query.filter_by(
            club_id=club.id,
            role='leader',
            status='approved'
        ).all()
        
        for leader in leaders:
            if leader.user.email:
                subject = f"New Membership Request - {club.name}"
                html = render_template(
                    'emails/membership_request.html',
                    club=club,
                    user=user,
                    leader=leader.user
                )
                NotificationService.send_email(leader.user.email, subject, html)
    
    @staticmethod
    def notify_membership_approved(user, club):
        """Notify user that their membership was approved"""
        subject = f"Membership Approved - {club.name}"
        html = render_template(
            'emails/membership_approved.html',
            club=club,
            user=user
        )
        NotificationService.send_email(user.email, subject, html)
        
        # Send SMS if phone number exists
        if user.phone:
            message = f"Your membership request for {club.name} has been approved!"
            NotificationService.send_sms(user.phone, message)
    
    @staticmethod
    def notify_event_reminder(event, user):
        """Send event reminder"""
        subject = f"Reminder: {event.title} Tomorrow"
        html = render_template(
            'emails/event_reminder.html',
            event=event,
            user=user
        )
        NotificationService.send_email(user.email, subject, html)
        
        if user.phone:
            message = f"Reminder: {event.title} tomorrow at {event.start_time.strftime('%I:%M %p')}"
            NotificationService.send_sms(user.phone, message)
    
    @staticmethod
    def notify_announcement(announcement):
        """Notify all club members about new announcement"""
        from app.models.club import Membership
        
        members = Membership.query.filter_by(
            club_id=announcement.club_id,
            status='approved'
        ).all()
        
        for member in members:
            if member.user.email and member.user.id != announcement.author_id:
                subject = f"New Announcement: {announcement.title}"
                html = render_template(
                    'emails/announcement.html',
                    announcement=announcement,
                    user=member.user
                )
                NotificationService.send_email(member.user.email, subject, html)